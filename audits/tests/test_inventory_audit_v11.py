"""Offline catalog completeness tests; never access real assets or network."""
import json
import tempfile
import unittest
from pathlib import Path

from audits.inventory_audit_v11 import inspect, InventoryAuditError


class InventoryV11Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "episodes" / "new").mkdir(parents=True)
        self.registry_path = self.root / "episodes/asset-memory-registry.json"
        self.write_registry([])
        self.manifest_path = self.root / "episodes/new/preview-manifest.json"

    def write_registry(self, items):
        self.registry_path.write_text(json.dumps({"schema_version": 1, "assets": items}), encoding="utf-8")

    def write_manifest(self, ids=("101",)):
        self.manifest_path.write_text(json.dumps({
            "video_id": "new-story",
            "scenes": [{"scene_id": f"S{i:02d}", "asset": {
                "provider": "mixkit",
                "provider_asset_id": value,
                "source_page_url": f"https://mixkit.co/free-stock-video/example-{value}",
                "license": "Mixkit Stock Video Free License",
                "sha256": "a"*64,
            }} for i, value in enumerate(ids, 1)]
        }), encoding="utf-8")

    def test_missing_record_is_reported_as_partial(self):
        self.write_manifest()
        result = inspect(self.root)
        self.assertEqual(result["status"], "LOCAL_METADATA_COVERAGE_PARTIAL")
        self.assertEqual(result["sources_without_registry_entries"], 1)
        self.assertFalse(result["independent_licensing_verified"])

    def test_covered_local_registry_never_claims_external_verification(self):
        self.write_manifest()
        self.write_registry([{"source_asset_key": "mixkit:101", "perceptual_hash": "some-real-fingerprint-marker"}])
        result = inspect(self.root)
        self.assertEqual(result["status"], "LOCAL_METADATA_COVERAGE_PASS")
        self.assertEqual(result["sources_without_registry_entries"], 0)
        self.assertFalse(result["drive_inventory_verified"])
        self.assertFalse(result["git_history_across_branches_verified"])

    def test_uncovered_draft_is_counted_even_without_final(self):
        self.write_manifest(("101", "102"))
        self.write_registry([{"source_asset_key": "mixkit:101", "perceptual_hash": "marker"}])
        result = inspect(self.root)
        self.assertEqual(result["manifest_count"], 1)
        self.assertEqual(result["sources_without_registry_entries"], 1)

    def test_missing_registry_blocks_readability(self):
        self.write_manifest()
        self.registry_path.unlink()
        with self.assertRaises(InventoryAuditError):
            inspect(self.root)


if __name__ == "__main__":
    unittest.main()
