import json
import tempfile
import unittest
from pathlib import Path

from production.asset_reuse_brain import audit, canonicalize_source_url, source_asset_key


def write_manifest(
    root: Path,
    episode: str,
    sha: str,
    *,
    source: str | None = None,
    segment: tuple[float, float] = (0.0, 10.0),
    legacy: bool = False,
) -> Path:
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
                "source_page_url": source or f"https://example.com/{sha}",
                "provider": "pexels",
                "source_segment_in": segment[0],
                "source_segment_out": segment[1],
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
            self.assertTrue(report["release_blocked"])
            self.assertTrue(report["cross_episode_duplicates"])

    def test_legacy_collision_is_recorded_not_reported_as_pass(self) -> None:
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
            self.assertEqual(report["status"], "HISTORICAL_COLLISION_RECORDED")
            self.assertTrue(report["release_blocked"])
            self.assertTrue(report["legacy_baseline"])

    def test_same_source_different_segment_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = "https://www.pexels.com/video/night-corridor-12345/?utm_source=test"
            write_manifest(root, "because-of-this-episode-001", "c" * 64, source=source, segment=(0, 5))
            target = write_manifest(
                root,
                "because-of-this-episode-003",
                "d" * 64,
                source="https://www.pexels.com/video/night-corridor-12345/",
                segment=(15, 20),
            )
            report = audit(target, root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(any(item["key_type"] == "source_asset" for item in report["cross_episode_duplicates"]))

    def test_canonical_url_removes_tracking_parameters(self) -> None:
        self.assertEqual(
            canonicalize_source_url("HTTPS://Pexels.com/video/a-123/?utm_source=x&b=2#frame"),
            "https://pexels.com/video/a-123?b=2",
        )

    def test_provider_source_key_is_segment_independent(self) -> None:
        asset = {
            "provider": "pexels",
            "source_page_url": "https://www.pexels.com/video/night-corridor-12345/",
        }
        self.assertEqual(source_asset_key(asset), "pexels:12345")

    def test_registry_unavailable_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = write_manifest(root, "because-of-this-episode-003", "e" * 64)
            with self.assertRaisesRegex(ValueError, "ASSET_MEMORY_UNAVAILABLE"):
                audit(target, root, registry_path=root / "episodes" / "asset-memory-registry.json")

    def test_unique_episode_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root, "because-of-this-episode-001", "f" * 64)
            target = write_manifest(root, "because-of-this-episode-003", "0" * 64)
            report = audit(target, root)
            self.assertEqual(report["status"], "ASSET_REUSE_PASS")
            self.assertFalse(report["cross_episode_duplicates"])


if __name__ == "__main__":
    unittest.main()
