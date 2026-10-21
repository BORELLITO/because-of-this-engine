import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from production.require_preview_approval import ApprovalError, require_approval
from production.validate_authorial_episode import (
    ReleaseValidationError,
    caption_events,
    parse_ass_time,
    validate,
)


class AuthorialReleaseTests(unittest.TestCase):
    def test_ass_parser_rejects_overlapping_events(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "captions.ass"
            path.write_text(
                "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,,one\n"
                "Dialogue: 0,0:00:01.50,0:00:03.00,Default,,0,0,,two\n",
                encoding="utf-8",
            )
            with self.assertRaises(ReleaseValidationError):
                caption_events(path)

    def test_ass_timestamp(self):
        self.assertAlmostEqual(parse_ass_time("0:01:02.50"), 62.5)

    def test_release_manifest_requires_schema_1_1(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
            with self.assertRaises(ReleaseValidationError):
                validate(manifest, "preview")

    def test_preview_approval_binds_to_manifest_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            approval = root / "approval.json"
            image = root / "S01.png"
            image.write_bytes(b"image")
            preview = root / "preview.mp4"
            preview.write_bytes(b"preview")
            manifest.write_text(
                json.dumps({
                    "video_id": "demo",
                    "scenes": [{"scene_id": "S01", "image": "S01.png"}],
                    "output": {"path": "{mode}.mp4"},
                    "approval": {"path": "approval.json"},
                }),
                encoding="utf-8",
            )
            asset_digest = hashlib.sha256()
            asset_digest.update(b"S01")
            asset_digest.update(hashlib.sha256(image.read_bytes()).digest())
            approval.write_text(
                json.dumps({
                    "approved": True,
                    "video_id": "demo",
                    "preview_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "preview_assets_sha256": asset_digest.hexdigest(),
                    "preview_output_sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
                    "reviewer": "Borelli",
                    "approved_at": "2026-10-21T12:00:00-03:00",
                }),
                encoding="utf-8",
            )
            result = require_approval(manifest)
            self.assertEqual(result["reviewer"], "Borelli")

            manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(ApprovalError):
                require_approval(manifest)


if __name__ == "__main__":
    unittest.main()
