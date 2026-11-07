"""The user-approved S09 replacement passes MANIFEST checks only.
The episode must remain blocked by independent render rights and audio history.
"""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from production.visual_plan_contract import VisualPlanContractError, validate_visual_plan

ROOT = Path(__file__).resolve().parents[1]
NEW_ID = "pexels-8888977"
OLD_ID = "pexels-12213087"

class VisualIntakeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/"episodes/episode-005/visual/asset-acquisition-plan.json").read_text(encoding="utf-8"))
        self.manifest=json.loads((ROOT/"episodes/episode-005/visual/scene-asset-manifest.json").read_text(encoding="utf-8"))

    def _consistent_copy(self):
        return copy.deepcopy(self.plan),copy.deepcopy(self.manifest)

    def test_real_manifest_passes_without_authorizing_render(self):
        report=validate_visual_plan(self.plan,self.manifest)
        self.assertEqual(report["status"],"VISUAL_PLAN_CONTRACT_PASS")
        self.assertEqual(report["manifest_asset_count"],16)
        self.assertFalse(report["promotion_allowed"])
        self.assertFalse(report["render_allowed"])
        self.assertFalse(report["global_catalog_updated"])
        asset=next(a for a in self.manifest["assets"] if a["candidate_id"]==NEW_ID)
        self.assertFalse(asset["approved_for_render"])
        self.assertFalse(any(a["candidate_id"]==OLD_ID for a in self.manifest["assets"]))
        self.assertTrue(any(a["candidate_id"]==OLD_ID for a in self.plan["candidates"]))

    def test_synthetic_human_approval_revocation_blocks(self):
        plan,man=self._consistent_copy()
        c=next(a for a in plan["candidates"] if a["candidate_id"]==NEW_ID)
        c["rights_status"]="CANDIDATE_DOWNLOADED_AWAITING_HUMAN_QA"
        with self.assertRaisesRegex(VisualPlanContractError,"manifest contains a candidate not approved"):
            validate_visual_plan(plan,man)

    def test_tampered_sha_is_rejected(self):
        plan,man=self._consistent_copy()
        next(a for a in man["assets"] if a["candidate_id"]==NEW_ID)["sha256"]="0"*64
        with self.assertRaisesRegex(VisualPlanContractError,"intake SHA-256 mismatch"):
            validate_visual_plan(plan,man)

    def test_tampered_perceptual_identity_is_rejected(self):
        plan,man=self._consistent_copy()
        next(a for a in man["assets"] if a["candidate_id"]==NEW_ID)["perceptual_hash"]="PENDING_MANIFEST_ONLY"
        with self.assertRaisesRegex(VisualPlanContractError,"intake perceptual fingerprint mismatch"):
            validate_visual_plan(plan,man)

if __name__=="__main__":
    unittest.main()
