import json
import unittest
from pathlib import Path

from production.master_prompt_contract import (
    GATE_ORDER,
    MASTER_PROMPT_SHA256,
    MASTER_PROMPT_VERSION,
    SCHEMA_ID,
    validate_manifest_contract,
    validate_master_prompt,
)


class MasterPromptV6ContractTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_master_prompt_and_schema_are_immutable_contracts(self):
        report = validate_master_prompt(self.ROOT)
        self.assertEqual(report["version"], MASTER_PROMPT_VERSION)
        self.assertEqual(report["sha256"], MASTER_PROMPT_SHA256)
        self.assertEqual(report["schema_id"], SCHEMA_ID)
        self.assertEqual(report["gates"], list(GATE_ORDER))

    def test_all_execution_manifests_are_bound_to_v6(self):
        paths = [
            self.ROOT / "examples/video-only-episode-manifest-v2.template.json",
            *sorted((self.ROOT / "episodes").glob("*/manifest*.json")),
        ]
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            report = validate_manifest_contract(value, source_label=str(path))
            self.assertEqual(report["master_prompt_version"], "6.0")
            self.assertTrue(report["human_approval_required"])


if __name__ == "__main__":
    unittest.main()
