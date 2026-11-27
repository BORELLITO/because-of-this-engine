import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "production" / "brazil_files_clip_source_registry_v1.json"


class ClipSourceRegistryTests(unittest.TestCase):
    def test_registry_is_free_first_and_fail_closed(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "RESEARCH_SOURCE_REGISTRY_READY_ASSET_VERIFICATION_REQUIRED")
        self.assertEqual(data["global_policy"]["default_rights_status"], "NOT_VERIFIED_PER_ASSET")
        self.assertEqual(len(data["sources"]), 7)
        self.assertTrue(all(source["selection_allowed"] for source in data["sources"]))
        self.assertTrue(all(source["default_rights_status"] == "NOT_VERIFIED_PER_ASSET" for source in data["sources"]))

    def test_registry_captures_restricted_and_attribution_risks(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        by_id = {source["source_id"]: source for source in data["sources"]}
        self.assertIn("restricted-license", " ".join(by_id["MIXKIT"]["block_conditions"]))
        self.assertEqual(by_id["VIDEEZY"]["attribution"], "REQUIRED_UNLESS_SEPARATE_COMMERCIAL_LICENSE")
        self.assertEqual(by_id["DAREFUL"]["license_class"], "CC_BY_4_0")
        self.assertEqual(by_id["WIKIMEDIA_COMMONS"]["attribution"], "FILE_SPECIFIC")


if __name__ == "__main__":
    unittest.main()
