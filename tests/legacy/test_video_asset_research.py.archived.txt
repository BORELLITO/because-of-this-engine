import json
import tempfile
import unittest
from pathlib import Path

from production.video_asset_research import ResearchError, build_queue


def manifest():
    return {
        "video_id": "new-episode",
        "editing": {
            "clip_quantity": {
                "mode": "fixed",
                "min_clips": 1,
                "target_min": 1,
                "target_max": 1,
                "max_clips": 1,
                "min_scene_seconds": 2,
                "max_scene_seconds": 20,
                "enforce": True,
            }
        },
        "scenes": [{
            "scene_id": "S01",
            "duration": 5,
            "narration_excerpt": "A hotel hallway stays empty.",
            "visual_match": "EXACT",
            "visual_semantics": {
                "role": "literal",
                "required": {"environments": ["hotel"]},
                "narrative_anchors": {
                    "direct_required": ["hotel"],
                    "minimum_direct": 1,
                },
            },
        }],
    }


def candidate():
    return {
        "provider_asset_id": "42",
        "source_page_url": "https://mixkit.co/free-stock-video/hotel-hallway-42/?utm_source=test",
        "visual_evidence": {
            "environments": ["hotel"],
            "observed_environments": ["hotel"],
        },
    }


class AssetMemoryResearchTests(unittest.TestCase):
    def test_research_rejects_retired_source_before_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "asset-memory-registry.json"
            registry.write_text(json.dumps({
                "schema_version": 1,
                "policy": "GLOBAL_NO_REPEAT_SOURCE_ASSET",
                "assets": [{
                    "source_asset_key": "mixkit:42",
                    "first_used_video_id": "old-episode",
                    "status": "RETIRED",
                }],
            }), encoding="utf-8")

            result = build_queue(
                manifest(),
                {"mixkit": lambda query, limit: [candidate()]},
                limit=1,
                registry_path=registry,
            )
            scene = result["scenes"][0]
            self.assertEqual(scene["asset_memory"]["status"], "READY")
            self.assertEqual(scene["rejected_candidates"][0]["selection_status"], "REJECTED_GLOBAL_REUSE")
            self.assertEqual(scene["rejected_candidates"][0]["global_memory_check"], "BLOCKED")
            self.assertEqual(scene["candidates"], [])

    def test_research_fails_closed_when_registry_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises(ResearchError):
                build_queue(
                    manifest(),
                    {"mixkit": lambda query, limit: [candidate()]},
                    limit=1,
                    registry_path=missing,
                )


if __name__ == "__main__":
    unittest.main()
