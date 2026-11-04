"""Historical queue audit: review-only, not automatic consumption or permanent ban."""
import json
import tempfile
import unittest
from pathlib import Path

from production.asset_reuse_brain import audit, AssetReuseBrainError

ROOT = Path(__file__).resolve().parents[2]


class ReviewQueueV11Tests(unittest.TestCase):
    def setup_root(self, source="mixkit:100576", malformed=False):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        ep = root / "episodes" / "new"
        ep.mkdir(parents=True)
        queue = root / "audits" / "git_history_review_queue_v11.json"
        queue.parent.mkdir()
        data = {"schema_version": "1.1",
                "purpose": "REVIEW_QUEUE_ONLY_NEVER_AUTORETIRE",
                "automatic_retirement": False,
                "source_count": 1,
                "entries": [{"source_key": "mixkit:100576",
                             "status": "PENDING_REVIEW_NOT_RETIRED"}]}
        if malformed:
            data["automatic_retirement"] = True
        queue.write_text(json.dumps(data), encoding="utf-8")
        provider, source_id = source.split(":")
        manifest = {
            "video_id": "new",
            "scenes": [{"scene_id": "S01", "asset": {
                "asset_id": "new-scene1", "provider": provider,
                "provider_asset_id": source_id,
                "source_page_url": f"https://mixkit.co/free-stock-video/test-{source_id}/",
                "sha256": "a"*64,
            }}],
        }
        target = ep / "manifest.json"
        target.write_text(json.dumps(manifest), encoding="utf-8")
        return root, target

    def test_historical_draft_source_blocks_pending_review_not_retires(self):
        root, target = self.setup_root()
        report = audit(target, root)
        self.assertEqual(report["status"], "HISTORY_REVIEW_REQUIRED")
        self.assertTrue(report["release_blocked"])
        self.assertEqual(report["history_review_required_source_keys"], ["mixkit:100576"])
        self.assertFalse(report["historical_sources_auto_retired"])

    def test_unrelated_new_source_is_not_forced_to_review(self):
        root, target = self.setup_root(source="mixkit:100579")
        report = audit(target, root)
        self.assertEqual(report["status"], "ASSET_REUSE_PASS")
        self.assertEqual(report["history_review_required_source_keys"], [])
        self.assertFalse(report["historical_sources_auto_retired"])

    def test_malformed_queue_fails_closed(self):
        root, target = self.setup_root(malformed=True)
        with self.assertRaises(AssetReuseBrainError):
            audit(target, root)

    def test_real_queue_is_diagnostic_only_and_keeps_original_case(self):
        data=json.loads((ROOT/"audits/git_history_review_queue_v11.json").read_text())
        self.assertEqual(data["source_count"],len(data["entries"]))
        self.assertFalse(data["automatic_retirement"])
        self.assertFalse(data["approval_for_production"])
        self.assertTrue(all(x["status"]=="PENDING_REVIEW_NOT_RETIRED" for x in data["entries"]))
        self.assertIn("drive_file:1NG17JdVkslUfg9gXsw0VHkgTgzEbov6W",
                      [x["source_key"] for x in data["entries"]])


if __name__=="__main__":
    unittest.main()
