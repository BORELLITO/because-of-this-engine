from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from production.reuse_first import compute_fingerprints, verify_receipt, write_receipt


class ReuseFirstTests(unittest.TestCase):
    def manifest(self, root: Path) -> Path:
        (root / "script.txt").write_text("A verified narration.", encoding="utf-8")
        value = {
            "video_id": "test-video",
            "scenes": [
                {
                    "scene_id": "S01",
                    "beat_id": "B01",
                    "duration": 3,
                    "source_in": 0,
                    "focus": {"x": 0.5, "y": 0.5},
                    "asset": {
                        "asset_id": "asset-01",
                        "sha256": "a" * 64,
                        "drive_file_id": "drive-01",
                    },
                }
            ],
            "color_grade": {"preset": "test"},
            "music": {"source": "engine_generated", "generation": {"duration_seconds": 70}},
            "brand": {"logo_width": 540},
            "loop": {"outro_seconds": 1.2},
        }
        path = root / "preview-manifest.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_runtime_only_changes_do_not_invalidate_fingerprint(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = self.manifest(root)
            before = compute_fingerprints(path)
            value = json.loads(path.read_text(encoding="utf-8"))
            value["runtime_artifacts"] = {"preview": "rendered/preview.mp4"}
            value["runtime_artifact_hashes"] = {"preview": "b" * 64}
            path.write_text(json.dumps(value), encoding="utf-8")
            after = compute_fingerprints(path)
            self.assertEqual(before["final_key"], after["final_key"])

    def test_asset_change_invalidates_scene_and_final_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = self.manifest(root)
            before = compute_fingerprints(path)
            value = json.loads(path.read_text(encoding="utf-8"))
            value["scenes"][0]["asset"]["sha256"] = "b" * 64
            path.write_text(json.dumps(value), encoding="utf-8")
            after = compute_fingerprints(path)
            self.assertNotEqual(before["asset_key"], after["asset_key"])
            self.assertNotEqual(before["scene_key"], after["scene_key"])
            self.assertNotEqual(before["final_key"], after["final_key"])
            self.assertEqual(before["narration_key"], after["narration_key"])
            self.assertEqual(before["alignment_key"], after["alignment_key"])

    def test_receipt_requires_verified_delivery(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = self.manifest(root)
            fingerprints = compute_fingerprints(manifest)
            fp_path = root / "fingerprints.json"
            fp_path.write_text(json.dumps(fingerprints), encoding="utf-8")
            delivery = root / "delivery.json"
            delivery.write_text(json.dumps({
                "status": "DRIVE_VERIFIED",
                "delivery_name": "stable-delivery",
                "job_id": "stable-job",
                "delivery_folder_id": "folder-test",
                "delivery_folder_url": "https://drive.google.com/drive/folders/folder-test",
                "file_count": 1,
                "files": [
                    {"id": "file-test", "name": "preview.mp4", "size": 4, "md5": "098f6bcd4621d373cade4e832627b4f6"}
                ],
            }), encoding="utf-8")
            receipt = root / "receipt.json"
            write_receipt(fingerprints, receipt, manifest, delivery)
            valid, reason = verify_receipt(receipt, fingerprints)
            self.assertTrue(valid)
            self.assertEqual(reason, "reuse_valid")


if __name__ == "__main__":
    unittest.main()
