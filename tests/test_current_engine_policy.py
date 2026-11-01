from __future__ import annotations

import json
import unittest
from pathlib import Path

from production.v7_singleton_guard import audit


ROOT = Path(__file__).resolve().parents[1]


class CurrentEnginePolicyTests(unittest.TestCase):
    def test_active_policy_declares_only_current_suite(self):
        policy = json.loads(
            (ROOT / "production" / "active_engine_policy.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            policy["active_test_suite"],
            [
                "tests/test_current_engine_policy.py",
                "tests/test_editorial_story_gates.py",
                "tests/test_reuse_first.py",
            ],
        )
        self.assertEqual(policy["legacy_test_policy"], "non_executable_archived")
        self.assertEqual(policy["legacy_version_execution"], "forbidden")

    def test_singleton_guard_accepts_current_engine_only(self):
        result = audit(ROOT)
        self.assertEqual(result["status"], "V7_SINGLE_ACTIVE_ENGINE_PASS")
        self.assertEqual(result["workflow"], ".github/workflows/episode-003-draft-preview.yml")

    def test_current_voice_and_schema_are_gemini_charon(self):
        policy = json.loads(
            (ROOT / "production" / "active_engine_policy.json").read_text(encoding="utf-8")
        )
        self.assertEqual(policy["voice_provider"], "gemini_tts")
        self.assertEqual(policy["voice_policy"]["voice_name"], "Charon")
        schema = json.loads(
            (ROOT / "production" / "schemas" / "production-record-3.0.0.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["narration"]["properties"]["provider"]["const"], "gemini_tts")


if __name__ == "__main__":
    unittest.main()
