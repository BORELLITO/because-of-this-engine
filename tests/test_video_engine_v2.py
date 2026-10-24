import unittest
from pathlib import Path

from production.video_asset_contract import VideoContractError, validate_manifest
from production.render_video_episode import narration_locked_scenes, scene_filter, xfade_filter
from production.video_asset_research import build_queue


def manifest():
    scenes = []
    for index in range(4):
        scenes.append({
            "scene_id": f"S{index + 1:02d}",
            "duration": 15,
            "story_beat": f"the investigation reaches beat {index}",
            "visual_intent": "show the central evidence clearly",
            "visual_function": "evidence",
            "visual_match": "EXACT",
            "visual_truth": "VERIFIED_FACT",
            "match_score": 0.9,
            "asset": {
                "asset_id": f"asset-{index}",
                "path": f"assets/clip-{index}.mp4",
                "provider": "mixkit",
                "source_page_url": "https://mixkit.co/",
                "license": "Stock Video Free License",
                "rights_status": "APPROVED",
                "approved_for_render": True,
                "sha256": f"{index + 1:064x}",
                "episode_id": "v2-demo",
            },
        })
    return {
        "schema_version": "2.0",
        "video_id": "v2-demo",
        "story_profile": {
            "truth_mode": "VERIFIED_FACT",
            "primary_emotion": "curiosity",
            "central_question": "What was missed?",
            "visual_symbol": "a red signal",
        },
        "audio": {"path": "audio/narration.wav"},
        "captions": {"path": "captions/narration.ass"},
        "brand": {"watermark_text": "|B"},
        "scenes": scenes,
    }


class VideoEngineV2Tests(unittest.TestCase):
    def test_video_contract_rejects_narrative_images(self):
        value = manifest()
        value["scenes"][0]["image"] = "forbidden.png"
        with self.assertRaisesRegex(VideoContractError, "forbidden narrative image"):
            validate_manifest(value, Path("/tmp"), check_files=False)

    def test_video_contract_rejects_repeated_animation_checksum(self):
        value = manifest()
        value["scenes"][1]["asset"]["sha256"] = value["scenes"][0]["asset"]["sha256"]
        with self.assertRaisesRegex(VideoContractError, "sha256 is repeated"):
            validate_manifest(value, Path("/tmp"), check_files=False)

    def test_contract_requires_sixty_to_seventy_five_seconds(self):
        value = manifest()
        value["scenes"][0]["duration"] = 2
        with self.assertRaisesRegex(VideoContractError, "between 60s and 75s"):
            validate_manifest(value, Path("/tmp"), check_files=False)

    def test_renderer_uses_vertical_video_crop_and_fixed_fps(self):
        value = scene_filter(1080, 1920, 0.5, 0.5)
        self.assertIn("force_original_aspect_ratio=increase", value)
        self.assertIn("fps=25", value)
        self.assertNotIn("zoompan", value)

    def test_transitions_are_narration_timeline_aware(self):
        value = xfade_filter([15, 15, 15], [{"type": "crossfade", "duration": 0.25}] * 2)
        self.assertIn("offset=14.750", value)
        self.assertIn("offset=29.500", value)

    def test_narration_locked_timeline_matches_audio_after_transition_overlap(self):
        scenes = manifest()["scenes"]
        for index, scene in enumerate(scenes):
            scene["transition"] = {"type": "crossfade", "duration": 0.25} if index else {"type": "hard_cut", "duration": 0}
        locked = narration_locked_scenes(scenes, 70.2)
        overlap = 0.25 * 3 + 0.25
        self.assertAlmostEqual(sum(scene["duration"] for scene in locked) - overlap, 70.2, places=5)
        self.assertNotEqual([scene["duration"] for scene in locked], [scene["duration"] for scene in scenes])

    def test_research_never_auto_approves_and_never_uses_images(self):
        value = manifest()
        result = build_queue(value, {"mixkit": lambda query, limit: [{"title": "signal", "duration_seconds": 15, "width": 1080, "height": 1920}]})
        candidate = result["scenes"][0]["candidates"][0]
        self.assertFalse(candidate["approved_for_render"])
        self.assertEqual(result["scenes"][0]["image_fallback"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()


