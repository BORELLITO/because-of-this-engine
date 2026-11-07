"""Test the real Episode 005 manifest as blocked; use in-memory synthetic
approval only to exercise positive validation. Never mutate production records.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from production.visual_plan_contract import VisualPlanContractError, validate_visual_plan


ROOT = Path(__file__).resolve().parents[1]


class VisualIntakeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(
            (ROOT / "episodes/episode-005/visual/asset-acquisition-plan.json").read_text(encoding="utf-8")
        )
        self.manifest = json.loads(
            (ROOT / "episodes/episode-005/visual/scene-asset-manifest.json").read_text(encoding="utf-8")
        )

    def _synthetically_consistent(self):
        plan = copy.deepcopy(self.plan)
        manifest = copy.deepcopy(self.manifest)
        # TEST FIXTURE ONLY. Never write approvals or pretend this is human QA.
        candidate = next(c for c in plan["candidates"] if c["candidate_id"] == "pexels-12213087")
        asset = next(a for a in manifest["assets"] if a["candidate_id"] == "pexels-12213087")
        candidate["rights_status"] = "APPROVED_FOR_MANIFEST_ONLY"
        candidate["qa"]["human_approval"] = "APPROVED_FOR_MANIFEST"
        asset["perceptual_hash"] = candidate["intake_artifact"]["perceptual_hash"]
        return plan, manifest

    def test_real_manifest_is_blocked_until_approval_and_hash_reconcile(self):
        with self.assertRaises(VisualPlanContractError) as raised:
            validate_visual_plan(self.plan, self.manifest)
        reason = str(raised.exception)
        self.assertIn("manifest contains a candidate not approved", reason)
        self.assertIn("pexels-12213087: intake perceptual fingerprint mismatch", reason)

    def test_consistent_synthetic_fixture_passes_without_promoting_media(self):
        plan, manifest = self._synthetically_consistent()
        report = validate_visual_plan(plan, manifest)
        self.assertEqual(report["status"], "VISUAL_PLAN_CONTRACT_PASS")
        self.assertFalse(report["render_allowed"])
        self.assertFalse(report["promotion_allowed"])
        self.assertFalse(report["global_catalog_updated"])

    def test_tampered_sha_is_rejected(self):
        plan, manifest = self._synthetically_consistent()
        manifest["assets"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(VisualPlanContractError, "intake SHA-256 mismatch"):
            validate_visual_plan(plan, manifest)

    def test_tampered_perceptual_identity_is_rejected(self):
        plan, manifest = self._synthetically_consistent()
        manifest["assets"][0]["perceptual_hash"] = "PENDING_MANIFEST_ONLY"
        with self.assertRaisesRegex(VisualPlanContractError, "perceptual fingerprint mismatch"):
            validate_visual_plan(plan, manifest)


if __name__ == "__main__":
    unittest.main()
