"""Absolute zero-incremental-cost tests; NEVER call an external provider."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.zero_cost_v21 import (
    POLICY_PATH, ZeroCostViolation, assert_zero_cost, audit_repository,
    evaluate_cost,
)
from production.gemini_tts import GeminiTTSError, _request_json

ROOT = Path(__file__).resolve().parents[1]


class ZeroIncrementalCostTests(unittest.TestCase):
    def test_offline_approved_charon_reuse_is_allowed(self):
        for item in ("existing_charon_audio_reuse", "ffmpeg_local_mix",
                     "source_fingerprint_local", "offline_media_qa"):
            report = evaluate_cost(item)
            self.assertEqual(report["status"], "PASS", report)
            self.assertFalse(report["new_charge_authorized"])

    def test_any_unverified_network_cost_is_blocked(self):
        for operation in ("gemini_tts_generate_content", "gemini_batch_generate",
                          "paid_stock_purchase", "paid_render_api",
                          "unknown_paid_service", "unverified_external_api"):
            report = evaluate_cost(operation)
            self.assertEqual(report["status"], "BLOCKED", report)
            self.assertFalse(report["external_request_authorized"])
            with self.assertRaises(ZeroCostViolation):
                assert_zero_cost(operation)

    def test_nonzero_spending_policy_cannot_authorize_requests(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        policy["zero_additional_cost_policy"]["allow_paid_apis"] = True
        policy["zero_additional_cost_policy"]["max_incremental_spend_usd"] = 100
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "policy.json"
            path.write_text(json.dumps(policy))
            self.assertEqual(evaluate_cost(
                "existing_charon_audio_reuse", policy_path=path)["status"], "BLOCKED")
            self.assertEqual(evaluate_cost(
                "gemini_tts_generate_content", policy_path=path)["status"], "BLOCKED")

    def test_absent_policy_fails_even_for_local_actions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "missing.json"
            self.assertEqual(evaluate_cost(
                "offline_media_qa", policy_path=p)["status"], "BLOCKED")

    def test_user_env_or_forged_free_tier_hint_cannot_override_network_lock(self):
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "fake-test-key-never-sent",
            "GEMINI_TTS_FREE_TIER": "true",
            "GEMINI_BILLING_HARD_CAP": "0",
            "PAYMENT_METHOD_DISABLED": "true",
        }):
            with patch("urllib.request.urlopen") as network:
                with self.assertRaisesRegex(GeminiTTSError, "ZERO_COST_POLICY_BLOCKED"):
                    _request_json("https://generativelanguage.googleapis.com/test",
                                  {"contents": [{"parts": [{"text": "test"}]}]})
                network.assert_not_called()

    def test_real_repo_cost_guard_is_integrated(self):
        report = audit_repository(ROOT)
        self.assertEqual(report["status"], "PASS", report)
        self.assertFalse(report["external_tts_calls_enabled"])


if __name__ == "__main__":
    unittest.main()
