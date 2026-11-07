"""Real Episode 005 regression: autonomous engine determines rights without
repeated user approvals; it cannot forge licenses or bypass release gates.
"""
import copy
import json
import unittest
from pathlib import Path

from production.rights_autonomy_v21 import (
    APPROVED_STATUS, PENDING_STATUS, audit, audit_repository, decide_one
)
from production.ledgers_v21 import validate_rights_ledger
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT/"episodes/episode-005/production-record.json"
PLAN = ROOT/"episodes/episode-005/visual/asset-acquisition-plan.json"
SCENE = ROOT/"episodes/episode-005/visual/scene-asset-manifest.json"
EVIDENCE = ROOT/"reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json"
APPROVED = {
    "pixabay-radio-vintage-old-171435",
    "pixabay-radar-black-green-target-symbol-57670",
    "pexels-5523892",
    "pexels-12590338",
    "pexels-8888977",
}
BLOCKED = {"pexels-11764431","nasa-svs-geos5-clouds-no-labels-4819"}

class AutonomousRightsDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=json.loads(REC.read_text())
        cls.plan=json.loads(PLAN.read_text())
        cls.scene=json.loads(SCENE.read_text())
        cls.evidence=json.loads(EVIDENCE.read_text())

    def test_engine_makes_five_approvals_and_two_blocks_itself(self):
        result=audit(self.record,self.plan,self.scene,self.evidence)
        self.assertEqual(result["status"],"PASS",result)
        self.assertEqual(result["auto_approved_count"],5)
        self.assertEqual(result["blocked_count"],2)
        self.assertEqual(
            {x["asset_id"] for x in result["decisions"] if x["allow_scoped_render"]},
            APPROVED
        )
        self.assertEqual(
            {x["asset_id"] for x in result["decisions"] if not x["allow_scoped_render"]},
            BLOCKED
        )
        self.assertFalse(result["render_executed"])
        self.assertFalse(result["publication_executed"])
        self.assertEqual(audit_repository(self.record,repo_root=ROOT)["status"],"PASS")

    def test_actual_rights_ledger_has_exactly_fourteen_approved_two_blocked(self):
        entries=self.record["rights_ledger"]
        self.assertEqual(len(entries),16)
        self.assertEqual(sum(x["rights_status"]=="APPROVED" for x in entries),14)
        self.assertEqual(sum(x["rights_status"]==PENDING_STATUS for x in entries),2)
        for entry in entries:
            if entry["asset_id"] in APPROVED:
                self.assertEqual(entry["render_approval_status"],APPROVED_STATUS)
                self.assertTrue(entry["approved_for_render"])
                self.assertEqual(entry["approval_scope"],"episode-005-render")
                self.assertFalse(entry["published_or_distributed"])
                self.assertEqual(entry["used_by_semantics"],"AUTHORIZED_INTENDED_EPISODE_NOT_PROOF_OF_RELEASE_OR_PUBLICATION")
            if entry["asset_id"] in BLOCKED:
                self.assertFalse(entry["approved_for_render"])
                self.assertFalse(entry["commercial_use"])
                self.assertEqual(entry["used_by"],[])
        self.assertEqual(validate_rights_ledger(self.record)["status"],"BLOCKED")
        self.assertEqual(validate_visual_rights_consistency(self.record,repo_root=ROOT)["status"],"BLOCKED")

    def test_identifiable_person_blocks_even_with_normal_pexels_license(self):
        record=next(x for x in self.record["rights_ledger"] if x["asset_id"]=="pexels-11764431")
        plan=next(x for x in self.plan["candidates"] if x["candidate_id"]==record["asset_id"])
        scene=next(x for x in self.scene["assets"] if x["candidate_id"]==record["asset_id"])
        evid=next(x for x in self.evidence["reviewed_assets"] if x["asset_id"]==record["asset_id"])
        decision=decide_one(record,plan,scene,evid)
        self.assertFalse(decision["allow_scoped_render"])
        self.assertTrue(any("identifiable person" in x for x in decision["reasons"]))

    def test_nasa_no_2020_credit_and_factual_disclosure_blocks(self):
        r=next(x for x in self.record["rights_ledger"] if x["asset_id"].startswith("nasa-"))
        p=next(x for x in self.plan["candidates"] if x["candidate_id"]==r["asset_id"])
        s=next(x for x in self.scene["assets"] if x["candidate_id"]==r["asset_id"])
        e=next(x for x in self.evidence["reviewed_assets"] if x["asset_id"]==r["asset_id"])
        result=decide_one(r,p,s,e)
        self.assertFalse(result["allow_scoped_render"])
        self.assertTrue(any("NASA source credits" in x for x in result["reasons"]))

    def test_forged_approval_without_evidence_is_rejected(self):
        rec=copy.deepcopy(self.record)
        entry=next(x for x in rec["rights_ledger"] if x["asset_id"]=="pexels-11764431")
        entry["rights_status"]="APPROVED"
        entry["approved_for_render"]=True
        entry["commercial_use"]=True
        self.assertEqual(audit(rec,self.plan,self.scene,self.evidence)["status"],"BLOCKED")

    def test_tampered_source_sha_or_phash_blocks_approval(self):
        review=copy.deepcopy(self.evidence)
        entry=next(x for x in review["reviewed_assets"] if x["asset_id"]=="pexels-8888977")
        entry["verified_source_sha256"]="f"*64
        result=audit(self.record,self.plan,self.scene,review)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("source SHA-256 evidence mismatched" in x
            for d in result["decisions"] if d["asset_id"]=="pexels-8888977" for x in d["reasons"]))

    def test_logo_or_recognizable_person_forces_block(self):
        review=copy.deepcopy(self.evidence)
        item=next(x for x in review["reviewed_assets"] if x["asset_id"]=="pexels-5523892")
        item["visual_brand_class"]="recognizable_brand"
        self.assertEqual(audit(self.record,self.plan,self.scene,review)["status"],"BLOCKED")
        self.assertEqual(next(x for x in audit(self.record,self.plan,self.scene,review)["decisions"]
            if x["asset_id"]=="pexels-5523892")["decision"],"BLOCKED_PENDING_SAFEGUARDS")

    def test_fake_pexels_url_cannot_obtain_scoped_approval(self):
        review=copy.deepcopy(self.evidence)
        item=next(x for x in review["reviewed_assets"] if x["asset_id"]=="pexels-8888977")
        item["reviewed_source_license_policy"]="https://evil.example/pexels-license"
        self.assertEqual(audit(self.record,self.plan,self.scene,review)["status"],"BLOCKED")

    def test_new_unreviewed_auto_approval_is_rejected(self):
        rec=copy.deepcopy(self.record)
        rec["rights_ledger"].append({
            "asset_id":"unreviewed-media",
            "render_approval_status":APPROVED_STATUS,
            "approved_for_render":True,
        })
        self.assertEqual(audit(rec,self.plan,self.scene,self.evidence)["status"],"BLOCKED")

if __name__=="__main__":unittest.main()
