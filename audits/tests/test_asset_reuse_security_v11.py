"""V1.1 anti-reuse regression tests: all work with invented manifests in temp dirs.

No media bytes, API access or production files are modified.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.asset_reuse_brain import AssetReuseBrainError, audit
from production.quality_gates import _visual


class AssetReuseSecurityV11(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "episodes").mkdir()
        self.new_folder = self.root / "episodes" / "new"
        self.new_folder.mkdir()

    def manifest(self, folder, video_id, source_id, *, filename="manifest.json", alias=None):
        folder.mkdir(parents=True, exist_ok=True)
        data = {
            "video_id": video_id,
            "scenes": [{
                "scene_id": "S01",
                "asset": {
                    "asset_id": f"{video_id}-S01",
                    "provider": "mixkit",
                    "provider_asset_id": source_id,
                    "source_page_url": f"https://mixkit.co/free-stock-video/asset-{source_id}",
                    "sha256": "a" * 64 if source_id == "101" else "b" * 64,
                },
            }],
        }
        if alias:
            data["asset_reuse_brain"] = {"same_story_id": alias}
        target = folder / filename
        target.write_text(json.dumps(data), encoding="utf-8")
        return target

    def test_only_draft_snapshot_is_still_source_history(self):
        old_folder = self.root / "episodes" / "old"
        self.manifest(old_folder, "episode-old", "101", filename="preview-manifest.json")
        new = self.manifest(self.new_folder, "episode-new", "101")
        out = audit(new, self.root)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertTrue(out["cross_episode_duplicates"])
        self.assertEqual(out["scanned_manifest_count"], 2)

    def test_manifest_alias_cannot_hide_foreign_episode(self):
        old_folder = self.root / "episodes" / "old"
        self.manifest(old_folder, "episode-old", "101")
        new = self.manifest(self.new_folder, "episode-new", "101", alias="episode-old")
        out = audit(new, self.root)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIn("same_story_id", out["reason"])

    def test_unrelated_foreign_alias_still_blocks(self):
        new = self.manifest(self.new_folder, "episode-new", "102", alias="a-different-story")
        out = audit(new, self.root)
        self.assertEqual(out["status"], "BLOCKED")

    def test_same_id_preview_snapshot_is_allowed(self):
        new = self.manifest(self.new_folder, "episode-new", "102", alias="episode-new")
        self.manifest(self.new_folder, "episode-new", "102", filename="preview-manifest.json", alias="episode-new")
        out = audit(new, self.root)
        self.assertEqual(out["status"], "ASSET_REUSE_PASS")
        self.assertEqual(out["scanned_manifest_count"], 2)

    def test_missing_registry_is_fail_closed(self):
        new = self.manifest(self.new_folder, "episode-new", "102")
        with self.assertRaises(AssetReuseBrainError):
            audit(new, self.root, registry_path=self.root / "episodes" / "no-registry.json")

    def test_saved_pass_cannot_override_new_live_failure(self):
        new = self.manifest(self.new_folder, "episode-new", "102")
        render = self.new_folder / "rendered"
        render.mkdir()
        (render / "asset-reuse-brain-final.json").write_text(
            json.dumps({"status": "ASSET_REUSE_PASS"}), encoding="utf-8"
        )
        with patch("production.quality_gates.validate_manifest", return_value={"scenes": [1]}):
            with patch("production.quality_gates.audit_asset_reuse", return_value={
                "status": "BLOCKED", "reason": "source already used",
            }) as live:
                status, reason = _visual(new, self.new_folder, "final")
                self.assertEqual(status, "BLOCKED")
                self.assertIn("fresh", reason)
                self.assertTrue(live.called)

    def test_saved_block_cannot_override_fresh_real_pass(self):
        new = self.manifest(self.new_folder, "episode-new", "102")
        render = self.new_folder / "rendered"
        render.mkdir()
        (render / "asset-reuse-brain-final.json").write_text(
            json.dumps({"status": "BLOCKED"}), encoding="utf-8"
        )
        with patch("production.quality_gates.validate_manifest", return_value={"scenes": [1]}):
            with patch("production.quality_gates.audit_asset_reuse", return_value={
                "status": "ASSET_REUSE_PASS",
                "scanned_manifest_count": 1,
                "registry_asset_count": 1,
            }):
                status, _reason = _visual(new, self.new_folder, "final")
                self.assertEqual(status, "PASS")


if __name__ == "__main__":
    unittest.main()
