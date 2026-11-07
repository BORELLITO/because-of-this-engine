"""Ensure S09 user-approved visual substitution never silently authorizes render.
The candidate source and perceptual identity come from actual GitHub media QA.
"""
from __future__ import annotations
import json
import unittest
from pathlib import Path

from production.visual_plan_contract import validate_visual_plan
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency

ROOT=Path(__file__).resolve().parents[1]
ASSET="pexels-8888977"
OLD="pexels-12213087"

class UserApprovedS09ManifestOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((ROOT/"episodes/episode-005/visual/asset-acquisition-plan.json").read_text())
        cls.scene=json.loads((ROOT/"episodes/episode-005/visual/scene-asset-manifest.json").read_text())
        cls.record=json.loads((ROOT/"episodes/episode-005/production-record.json").read_text())
        cls.evidence=json.loads((ROOT/"reports/EP005_S09_APPROVED_MANIFEST_ONLY_20261107.json").read_text())

    def test_original_asset_preserved_in_historical_plan_but_not_active_scene(self):
        plan_ids={x["candidate_id"] for x in self.plan["candidates"]}
        scene_ids={x["candidate_id"] for x in self.scene["assets"]}
        self.assertIn(OLD,plan_ids)
        self.assertNotIn(OLD,scene_ids)
        self.assertIn(ASSET,plan_ids & scene_ids)
        shot=next(x for x in self.scene["shot_assignments"] if x["shot_id"]=="S09")
        self.assertEqual(shot["assignment"]["candidate_id"],ASSET)
        self.assertEqual(shot["assignment"]["approved_for_render"],False)

    def test_source_and_perceptual_matches_verified_real_media(self):
        p=next(x for x in self.plan["candidates"] if x["candidate_id"]==ASSET)
        m=next(x for x in self.scene["assets"] if x["candidate_id"]==ASSET)
        self.assertEqual(p["intake_artifact"]["sha256"],self.evidence["original_media"]["sha256"])
        self.assertEqual(p["intake_artifact"]["perceptual_hash"],self.evidence["original_media"]["perceptual_hash"])
        self.assertEqual(m["sha256"],p["intake_artifact"]["sha256"])
        self.assertEqual(m["perceptual_hash"],p["intake_artifact"]["perceptual_hash"])
        self.assertEqual(p["fingerprint_audit"]["workflow_run_id"],42390022588)
        self.assertEqual(self.evidence["evidence"]["detected_collisions"],0)
        self.assertEqual(self.evidence["source"]["media_url"],p["media_url"])

    def test_manifests_pass_but_rights_remain_blocked(self):
        r=validate_visual_plan(self.plan,self.scene)
        self.assertEqual(r["status"],"VISUAL_PLAN_CONTRACT_PASS",r)
        self.assertFalse(r["render_allowed"])
        self.assertFalse(r["global_catalog_updated"])
        rights=validate_visual_rights_consistency(self.record,repo_root=ROOT)
        self.assertEqual(rights["status"],"BLOCKED")
        self.assertTrue(any("visual assets missing render rights" in error for error in rights["failures"]))
        self.assertFalse(any("plan does not record human manifest approval" in e and ASSET in e for e in rights["failures"]))
        self.assertFalse(any(x["asset_id"]==ASSET for x in self.record["rights_ledger"]))

    def test_safety_flags_user_approved_only_for_editorial_choice(self):
        e=self.evidence["release_state"]
        self.assertTrue(e["approved_for_manifest_only"])
        self.assertTrue(e["user_editorial_approval_recorded"])
        for field in ("legal_render_authorization","rights_ledger_updated","global_asset_registry_updated","render_executed","publication_executed","production_enablement"):
            self.assertIs(e[field],False,field)

if __name__=="__main__":
    unittest.main()
