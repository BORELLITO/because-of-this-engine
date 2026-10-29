import json
import unittest
from pathlib import Path

from production.production_record_v7 import new_record
from production.v7_post_publication import PostPublicationError, close_g11


ROOT = Path(__file__).resolve().parents[1]


class V7PostPublicationTests(unittest.TestCase):
    def test_manual_receipt_closes_g11(self):
        manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))
        record = new_record(manifest, engine_bundle_id="test-bundle")
        receipt = {"video_id": "episode-001", "platform": "youtube", "public_url": "https://youtube.example/video", "published_at": "2026-10-29T00:00:00Z", "video_sha256": "a" * 64, "manual_confirmation": True, "automatic_publication": False}
        updated = close_g11(record, receipt)
        self.assertEqual(updated["gates"]["G11"]["state"], "passed")
        self.assertEqual(updated["production"]["state"], "manually_published")

    def test_automatic_receipt_is_rejected(self):
        manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))
        record = new_record(manifest, engine_bundle_id="test-bundle")
        receipt = {"video_id": "episode-001", "platform": "youtube", "public_url": "https://youtube.example/video", "published_at": "2026-10-29T00:00:00Z", "video_sha256": "a" * 64, "manual_confirmation": False, "automatic_publication": True}
        with self.assertRaises(PostPublicationError):
            close_g11(record, receipt)


if __name__ == "__main__":
    unittest.main()
