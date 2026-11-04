"""Singleton guard must follow the canonical config constant and reject fake bindings."""
import json
import unittest
from pathlib import Path
from production.v7_singleton_guard import audit

ROOT = Path(__file__).resolve().parents[2]


class SingletonV11Tests(unittest.TestCase):
    def test_canonical_74_binding_passes(self):
        result = audit(ROOT)
        self.assertEqual(result["status"], "V7_SINGLE_ACTIVE_ENGINE_PASS")
        self.assertEqual(result["profile"], json.loads((ROOT / "production/active_engine_policy.json").read_text())["active_engine_profile"])


if __name__ == "__main__":
    unittest.main()
