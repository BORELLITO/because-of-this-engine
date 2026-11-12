"""Regression tests for the single active V2.1 engine boundary."""

import json
import unittest
from pathlib import Path

from production.v21_singleton_guard import audit


class SingletonGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.policy = json.loads(
            (cls.root / "production" / "active_engine_policy.json").read_text(
                encoding="utf-8"
            )
        )
        cls.readme = (cls.root / "README.md").read_text(encoding="utf-8")

    def test_active_policy_points_to_v21_gemini_charon(self):
        self.assertEqual(self.policy["active_engine_version"], "2.1")
        self.assertEqual(
            self.policy["canonical_entrypoint"],
            "production/canonical_entrypoint.py",
        )
        self.assertEqual(self.policy["voice_provider"], "gemini_tts")
        self.assertEqual(self.policy["voice_policy"]["model"], "gemini-3.8-flash-tts")
        self.assertEqual(self.policy["voice_policy"]["voice_name"], "Charon")
        self.assertFalse(self.policy["voice_policy"]["creative_claw_allowed"])
        self.assertFalse(self.policy["production_enablement"])

    def test_readme_does_not_advertise_retired_runtime(self):
        self.assertIn("Motor Canônico V2.1", self.readme)
        self.assertIn("production/canonical_entrypoint.py", self.readme)
        self.assertNotIn("V7.1 Piper Canonical Engine + Active V7.2", self.readme)
        self.assertNotIn("Narration provider: local Piper neural TTS only", self.readme)
        self.assertNotIn("Active V7.2 Reuse First", self.readme)

    def test_singleton_guard_passes_current_tree(self):
        report = audit(self.root)
        self.assertEqual(report["status"], "V21_SINGLETON_PASS", report)
        self.assertEqual(report["canonical_entrypoint"], "production/canonical_entrypoint.py")
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
