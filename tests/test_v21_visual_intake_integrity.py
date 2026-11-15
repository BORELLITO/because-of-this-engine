"""The complete Episode 005 manifest passes intake identity checks only."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from production.visual_plan_contract import VisualPlanContractError,validate_visual_plan
ROOT=Path(__file__).resolve().parents[1]
NEW_ID="pexels-8888977"
S07_ID="archive-prelinger-onguard1956-s07"
S10_ID="archive-gov-antps25-29604-s10"
class VisualIntakeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/"episodes/episode-005/visual/asset-acquisition-plan.json").read_text())
        self.manifest=json.loads((ROOT/"episodes/episode-005/visual/scene-asset-manifest.json").read_text())
    def test_real_manifest_passes_without_authorizing_render(self):
        report=validate_visual_plan(self.plan,self.manifest)
        self.assertEqual(report["status"],"VISUAL_PLAN_CONTRACT_PASS")
        self.assertEqual(report["manifest_asset_count"],16)
        self.assertFalse(report["promotion_allowed"])
        self.assertFalse(report["render_allowed"])
        self.assertFalse(report["global_catalog_updated"])
        self.assertFalse(next(a for a in self.manifest["assets"] if a["candidate_id"]==NEW_ID)["approved_for_render"])
        self.assertEqual(self.manifest["unresolved_shots"],[])
        self.assertEqual(next(a for a in self.manifest["assets"] if a["candidate_id"]==S07_ID)["source_segment"]["start_seconds"],282)
        self.assertEqual(next(a for a in self.manifest["assets"] if a["candidate_id"]==S10_ID)["source_segment"]["start_seconds"],550)
    def test_synthetic_human_approval_revocation_blocks(self):
        plan=copy.deepcopy(self.plan)
        man=copy.deepcopy(self.manifest)
        c=next(a for a in plan["candidates"] if a["candidate_id"]==NEW_ID)
        c["rights_status"]="CANDIDATE_DOWNLOADED_AWAITING_HUMAN_QA"
        with self.assertRaisesRegex(VisualPlanContractError,"manifest contains a candidate not approved"):
            validate_visual_plan(plan,man)
    def test_tampered_sha_is_rejected(self):
        plan=copy.deepcopy(self.plan)
        man=copy.deepcopy(self.manifest)
        next(a for a in man["assets"] if a["candidate_id"]==NEW_ID)["sha256"]="0"*64
        with self.assertRaisesRegex(VisualPlanContractError,"intake SHA-256 mismatch"):
            validate_visual_plan(plan,man)
    def test_tampered_perceptual_identity_is_rejected(self):
        plan=copy.deepcopy(self.plan)
        man=copy.deepcopy(self.manifest)
        next(a for a in man["assets"] if a["candidate_id"]==NEW_ID)["perceptual_hash"]="PENDING_MANIFEST_ONLY"
        with self.assertRaisesRegex(VisualPlanContractError,"intake perceptual fingerprint mismatch"):
            validate_visual_plan(plan,man)
if __name__=="__main__":
    unittest.main()
