import json
import tempfile
import unittest
from pathlib import Path

from production.asset_reuse_brain import audit


def write_manifest(root: Path, episode: str, sha: str, *, legacy: bool = False) -> Path:
    episode_dir = root / "episodes" / episode
    episode_dir.mkdir(parents=True, exist_ok=True)
    value = {
        "video_id": episode,
        "scenes": [{
            "scene_id": "S01",
            "asset": {
                "asset_id": f"{episode}-s01",
                "sha256": sha,
                "drive_file_id": f"drive-{sha[:8]}",
                "source_page_url": f"https://example.com/{sha}",
            },
        }],
    }
    if legacy:
        value["asset_reuse_brain"] = {
            "policy": "global_no_repeat",
            "legacy_baseline": True,
        }
    path = episode_dir / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class AssetReuseBrainTests(unittest.TestCase):
    def test_new_episode_blocks_exact_historical_clip_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "because-of-this-episode-001", "a" * 64)
            target = write_manifest(root, "because-of-this-episode-003", "a" * 64)
            report = audit(target, root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(report["cross_episode_duplicates"])

    def test_legacy_pilot_is_explicitly_recorded_but_does_not_break_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "because-of-this-episode-001", "b" * 64)
            target = write_manifest(
                root,
                "because-of-this-episode-002",
                "b" * 64,
                legacy=True,
            )
            report = audit(target, root)
            self.assertEqual(report["status"], "LEGACY_BASELINE_PASS")
            self.assertTrue(report["legacy_baseline"])

    def test_unique_episode_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "because-of-this-episode-001", "c" * 64)
            target = write_manifest(root, "because-of-this-episode-003", "d" * 64)
            report = audit(target, root)
            self.assertEqual(report["status"], "ASSET_REUSE_PASS")
            self.assertFalse(report["cross_episode_duplicates"])


if __name__ == "__main__":
    unittest.main()
