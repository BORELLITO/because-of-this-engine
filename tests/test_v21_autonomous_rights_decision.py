"""Episode 005 machine rights decisions require exact visual truth-disclosure evidence.

All validations are offline and read-only; they never publish, render or call TTS.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from production.rights_autonomy_v21 import (
    APPROVED_STATUS, audit, audit_repository, decide_one,
)
from production.ledgers_v21 import validate_rights_ledger
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency

ROOT = Path(__file__).resolve().parents[1]
APPROVED_NEW = {
    "pexels-11764431", "nasa-svs-geos5-clouds-no-labels-4819",
    "pixabay-radio-vintage-old-171435",
    "pixabay-radar-black-green-target-symbol-57670",
    "pexels-5523892", "pexels-12590338", "pexels-8888977",
}


class AutonomousRightsDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=json.loads((ROOT/"episodes/episode-005/production-record.json").read_text())
        cls.plan=json.loads((ROOT/"episodes/episode-005/visual/asset-acquisition-plan.json").read_text())
        cls.scene=json.loads((ROOT/"episodes/episode-005/visual/scene-asset-manifest.json").read_text())
        cls.evidence=json.loads((ROOT/"reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json").read_text())
        cls.disclosure=json.loads((ROOT/"episodes/episode-005/visual/scene-disclosures-v21.json").read_text())

    def check(self, *, record=None, evidence=None, disclosure=None):
        return audit(record or self.record,self.plan,self.scene,
                     evidence or self.evidence,
                     disclosure_contract=self.disclosure if disclosure is None else disclosure)

    def test_seven_source_approvals_are_exactly_bound_to_truth_labels(self):
        report=self.check()
        self.assertEqual(report["status"],"PASS",report)
        self.assertEqual(report["auto_approved_count"],7)
        self.assertEqual(report["blocked_count"],0)
        self.assertEqual({x["asset_id"] for x in report["decisions"] if x["allow_scoped_render"]},APPROVED_NEW)
        self.assertTrue(all(not x["independent_publication_authorization"] for x in report["decisions"]))
        self.assertEqual(audit_repository(self.record,repo_root=ROOT)["status"],"PASS")
        self.assertFalse(report["render_executed"])
        self.assertFalse(report["publication_executed"])

    def test_ledger_sixteen_exact_rights_can_pass_but_publishing_remains_off(self):
        entries=self.record["rights_ledger"]
        self.assertEqual(len(entries),16)
        self.assertEqual(sum(x["rights_status"]=="APPROVED" for x in entries),16)
        self.assertEqual(sum(x["approved_for_render"] is True for x in entries),16)
        for x in entries:
            if x["asset_id"] in APPROVED_NEW:
                self.assertEqual(x["render_approval_status"],APPROVED_STATUS)
                self.assertEqual(x["approval_scope"],"episode-005-render")
                self.assertFalse(x["published_or_distributed"])
                self.assertFalse(x["global_catalog_updated"])
        self.assertEqual(validate_rights_ledger(self.record)["status"],"PASS")
        self.assertEqual(validate_visual_rights_consistency(self.record,repo_root=ROOT)["status"],"PASS")
        self.assertFalse(self.record["production_enablement"])

    def test_actor_is_recognizable_and_fails_without_exact_disclosure(self):
        actor=next(x for x in self.record["rights_ledger"] if x["asset_id"]=="pexels-11764431")
        p=next(x for x in self.plan["candidates"] if x["candidate_id"]==actor["asset_id"])
        s=next(x for x in self.scene["assets"] if x["candidate_id"]==actor["asset_id"])
        e=next(x for x in self.evidence["reviewed_assets"] if x["asset_id"]==actor["asset_id"])
        self.assertEqual(e["visual_person_class"],"identifiable")
        self.assertEqual(e["source_role_warning"].split("S03")[0],"Historical source_role=")
        self.assertTrue(any("identifiable person" in msg for msg in decide_one(actor,p,s,e)["reasons"]))
        self.assertEqual(audit(self.record,self.plan,self.scene,self.evidence)["status"],"BLOCKED")

    def test_nasa_2020_model_requires_rendered_notice_and_delivery_copy(self):
        nasa=next(x for x in self.record["rights_ledger"] if x["asset_id"].startswith("nasa-"))
        p=next(x for x in self.plan["candidates"] if x["candidate_id"]==nasa["asset_id"])
        s=next(x for x in self.scene["assets"] if x["candidate_id"]==nasa["asset_id"])
        e=next(x for x in self.evidence["reviewed_assets"] if x["asset_id"]==nasa["asset_id"])
        self.assertFalse(e["delivery_credit_and_model_notice_verified"])
        self.assertFalse(decide_one(nasa,p,s,e)["allow_scoped_render"])
        approved=next(x for x in self.disclosure["disclosures"] if x["asset_id"]==nasa["asset_id"])
        self.assertTrue(decide_one(nasa,p,s,e,verified_disclosure=approved)["allow_scoped_render"])
        self.assertFalse(approved["final_assembled_video_metadata_verified"])

    def test_fake_notice_cannot_approve_actor(self):
        disclosure=copy.deepcopy(self.disclosure)
        actor=next(x for x in disclosure["disclosures"] if x["asset_id"]=="pexels-11764431")
        actor["overlay"]["line_1"]="ACTUAL 1983 FOOTAGE"
        report=self.check(disclosure=disclosure)
        self.assertEqual(report["status"],"BLOCKED",report)
        self.assertTrue(any("disclaimer contract failed" in x for x in report["failures"]))

    def test_forged_sample_sha_cannot_authorize_nasa(self):
        disclosure=copy.deepcopy(self.disclosure)
        nasa=next(x for x in disclosure["disclosures"] if x["asset_id"].startswith("nasa-"))
        nasa["overlay_qa_receipt"]["sample_video_sha256"]="0"*64
        self.assertEqual(self.check(disclosure=disclosure)["status"],"BLOCKED")

    def test_tampered_source_sha256_or_fingerprint_blocks(self):
        evidence=copy.deepcopy(self.evidence)
        right=next(x for x in evidence["reviewed_assets"] if x["asset_id"]=="pexels-8888977")
        right["verified_source_sha256"]="f"*64
        self.assertEqual(self.check(evidence=evidence)["status"],"BLOCKED")

    def test_unexpected_brand_and_false_license_url_block(self):
        evidence=copy.deepcopy(self.evidence)
        right=next(x for x in evidence["reviewed_assets"] if x["asset_id"]=="pexels-5523892")
        right["visual_brand_class"]="prominent_identifiable_brand"
        self.assertEqual(self.check(evidence=evidence)["status"],"BLOCKED")
        evidence=copy.deepcopy(self.evidence)
        right=next(x for x in evidence["reviewed_assets"] if x["asset_id"]=="pexels-8888977")
        right["reviewed_source_license_policy"]="https://wrong.example/pexels"
        self.assertEqual(self.check(evidence=evidence)["status"],"BLOCKED")

    def test_new_asset_claim_without_evidence_blocks(self):
        rec=copy.deepcopy(self.record)
        rec["rights_ledger"].append({"asset_id":"unknown","render_approval_status":APPROVED_STATUS})
        self.assertEqual(self.check(record=rec)["status"],"BLOCKED")

    def test_actor_scene_falsely_moved_to_s03_blocks_even_if_approval_stored(self):
        scene=copy.deepcopy(self.scene)
        next(x for x in scene["shot_assignments"] if x["shot_id"]=="S01")["shot_id"]="S03"
        report=audit(self.record,self.plan,scene,self.evidence,disclosure_contract=self.disclosure)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertTrue(any("disclaimer contract" in f for f in report["failures"]))


if __name__=="__main__":
    unittest.main()
