import json
import unittest
from pathlib import Path

from production.production_record_v7 import new_record, transition, validate_record


ROOT = Path(__file__).resolve().parents[1]


class V7StateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))

    def test_record_has_canonical_gate_order(self):
        record = new_record(self.manifest, engine_bundle_id="test-bundle")
        result = validate_record(record)
        self.assertEqual(result["schema_id"], "because-of-this://schemas/production-record/3.0.0")
        self.assertEqual(list(record["gates"]), [f"G{i}" for i in range(12)])

    def test_transitions_are_fail_closed(self):
        record = new_record(self.manifest, engine_bundle_id="test-bundle")
        transition(record, "preflight", evidence="G0 passed")
        transition(record, "in_production", evidence="G1-G3 passed")
        with self.assertRaises(Exception):
            transition(record, "manually_published", evidence="publication is manual")


if __name__ == "__main__":
    unittest.main()
