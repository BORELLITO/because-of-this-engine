"""Regression tests for the manual-only LoreMotion intake lane."""
from __future__ import annotations

import copy
import unittest

from production.loremotion_intake_policy_v21 import validate_loremotion_candidate
from production.visual_provider_policy import license_allowed, policy_for


class LoreMotionIntakePolicyV21Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = {
            "provider": "loremotion",
            "model": "LTX 2.5",
            "source_page_url": "https://loremotion.com/generate/",
            "asset_path": "candidate.mp4",
            "capture_mode": "browser_manual",
            "promotion": "MANUAL_REVIEW_ONLY",
            "approved_for_render": False,
            "aspect_ratio": "9:16",
            "width": 720,
            "height": 1280,
            "duration_seconds": 5,
            "browser_receipt": {
                "status": "DONE",
                "model": "LTX 2.5",
                "aspect_ratio": "9:16",
                "watermark_status": "NONE",
            },
            "rights_receipt": {
                "status": "VERIFIED",
                "commercial_use_claim": True,
                "input_rights_confirmed": True,
                "model_terms_checked": True,
                "terms_url": "https://loremotion.com/terms",
                "acceptable_use_url": "https://loremotion.com/acceptable-use",
            },
        }

    def test_valid_candidate_passes_without_render_authorization(self):
        report = validate_loremotion_candidate(self.candidate)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["promotion"], "BLOCKED_BY_DEFAULT")
        self.assertFalse(report["approved_for_render"])
        self.assertEqual(report["render"], "NOT_RUN")
        self.assertEqual(report["publication"], "NOT_RUN")

    def test_provider_is_registered_as_manual_only(self):
        policy = policy_for("loremotion")
        self.assertIsNotNone(policy)
        self.assertTrue(policy["manual_only"])
        self.assertEqual(policy["source_tier"], "ai_generated_manual")
        self.assertTrue(license_allowed(policy, "LoreMotion Terms of Service (per generated clip)"))

    def test_automated_capture_is_blocked(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["capture_mode"] = "automated_browser"
        report = validate_loremotion_candidate(candidate)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("browser_manual" in failure for failure in report["failures"]))

    def test_missing_rights_receipt_is_blocked(self):
        candidate = copy.deepcopy(self.candidate)
        candidate.pop("rights_receipt")
        report = validate_loremotion_candidate(candidate)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("rights_receipt" in failure for failure in report["failures"]))

    def test_self_approved_render_is_blocked(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["approved_for_render"] = True
        report = validate_loremotion_candidate(candidate)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("self-authorize" in failure for failure in report["failures"]))

    def test_non_vertical_clip_is_blocked(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["aspect_ratio"] = "16:9"
        report = validate_loremotion_candidate(candidate)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("9:16" in failure for failure in report["failures"]))


if __name__ == "__main__":
    unittest.main()
