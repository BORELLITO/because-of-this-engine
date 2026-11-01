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
                "tests/test_reuse_first.py",
                "tests/test_current_engine_policy.py",
            ],
        )
        self.assertEqual(policy["legacy_test_policy"], "non_executable_archived")
        self.assertEqual(policy["legacy_version_execution"], "forbidden")

    def test_singleton_guard_accepts_current_engine_only(self):
        result = audit(ROOT)
        self.assertEqual(result["status"], "V7_SINGLE_ACTIVE_ENGINE_PASS")
        self.assertEqual(result["workflow"], ".github/workflows/episode-002-draft-preview.yml")


if __name__ == "__main__":
    unittest.main()
