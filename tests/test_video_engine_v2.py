import tempfile
import unittest
from pathlib import Path

from production.video_asset_contract import VideoContractError, validate_manifest
from production.render_video_episode import ass_color, narration_locked_scenes, scene_filter, xfade_filter, write_brand_ass
from production.video_asset_research import build_queue
from production.visual_semantics import text_has_concept, visual_match_report


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
            "narration_excerpt": "the investigation reaches beat",
            "visual_semantics": {
                "role": "literal",
                "required": {
                    "subjects": ["person"],
                    "actions": ["standing"],
                    "environments": ["interior"],
                    "objects": ["screen"],
                },
                "preferred": {"moods": ["eerie"]},
                "forbidden": ["medical_vial", "laboratory"],
            },
            "match_score": 0.9,
            "asset": {
                "asset_id": f"asset-{index}",
                "path": f"assets/clip-{index}.mp4",
                "provider": "mixkit",
                "source_page_url": f"https://mixkit.co/clip-{index}",
                "license": "Stock Video Free License",
                "rights_status": "APPROVED",
                "approved_for_render": True,
                "sha256": f"{index + 1:064x}",
                "episode_id": "v2-demo",
                "visual_evidence": {
                    "source_title": "Person standing at a screen in a dark interior",
                    "subjects": ["person"],
                    "actions": ["standing"],
                    "environments": ["interior"],
                    "objects": ["screen"],
                    "moods": ["eerie"],
                    "reviewed": True,
                    "basis": "test fixture",
                },
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
        "editing": {"clip_quantity": {"enforce": False}},
        "script": {"path": "script.txt"},
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
        self.assertIn("setsar=1", value)

    def test_transitions_are_narration_timeline_aware(self):
        value = xfade_filter([15, 15, 15], [{"type": "crossfade", "duration": 0.25}] * 2)
        self.assertIn("offset=14.750", value)
        self.assertIn("offset=29.500", value)
        self.assertIn("setsar=1", value)

    def test_brand_overlay_uses_ass_and_not_drawtext(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "brand.ass"
            result = write_brand_ass(target, {"watermark_enabled": True, "watermark_text": "|B", "accent_color": "#E3262E"}, 70.2)
            self.assertEqual(result, target)
            content = target.read_text(encoding="utf-8")
            self.assertIn("Style: Brand", content)
            self.assertIn("Dialogue: 0,0:00:00.00,0:01:10.20,Brand", content)
            self.assertNotIn("drawtext", content)
        self.assertEqual(ass_color("#E3262E"), "&H002E26E3")

    def test_narration_locked_timeline_matches_audio_after_transition_overlap(self):
        scenes = manifest()["scenes"]
        for index, scene in enumerate(scenes):
            scene["transition"] = {"type": "crossfade", "duration": 0.25} if index else {"type": "hard_cut", "duration": 0}
        locked = narration_locked_scenes(scenes, 70.2)
        overlap = 0.25 * 3
        self.assertAlmostEqual(sum(scene["duration"] for scene in locked) - overlap, 70.2, places=5)
        self.assertNotEqual([scene["duration"] for scene in locked], [scene["duration"] for scene in scenes])

    def test_enforced_clip_quantity_blocks_underedited_episode(self):
        value = manifest()
        value["editing"]["clip_quantity"]["enforce"] = True
        with self.assertRaisesRegex(VideoContractError, "requires 10-18 unique video clips"):
            validate_manifest(value, Path("/tmp"), check_files=False)

    def test_exact_match_requires_stronger_semantic_score(self):
        value = manifest()
        value["scenes"][0]["match_score"] = 0.79
        with self.assertRaisesRegex(VideoContractError, "EXACT semantic-match threshold"):
            validate_manifest(value, Path("/tmp"), check_files=False)

    def test_narration_lock_respects_source_duration_caps(self):
        scenes = manifest()["scenes"]
        for scene in scenes:
            scene["transition"] = {"type": "crossfade", "duration": 0.25}
            scene["asset"]["duration_seconds"] = 30
        scenes[0]["asset"]["duration_seconds"] = 12
        locked = narration_locked_scenes(scenes, 70.2)
        self.assertLessEqual(locked[0]["duration"], 11.951)
        self.assertAlmostEqual(sum(item["duration"] for item in locked) - 0.25 * 3, 70.2, places=5)

    def test_research_never_auto_approves_and_never_uses_images(self):
        value = manifest()
        result = build_queue(value, {"mixkit": lambda query, limit: [{"title": "Person standing at a screen in a dark interior", "duration_seconds": 15, "width": 1080, "height": 1920,
                         "visual_evidence": {"subjects": ["person"], "actions": ["standing"], "environments": ["interior"],
                                             "objects": ["screen"], "moods": ["eerie"]}}]})
        candidate = result["scenes"][0]["candidates"][0]
        self.assertFalse(candidate["approved_for_render"])
        self.assertEqual(result["scenes"][0]["image_fallback"], "FORBIDDEN")
        self.assertTrue(result["selection_rules"]["no_repeat_animation"])
        self.assertFalse(result["selection_rules"]["keyword_only_matching"])
        self.assertEqual(result["clip_quantity_gate"]["status"], "ADVISORY")

    def test_semantic_matcher_respects_word_boundaries(self):
        self.assertFalse(text_has_concept("hands and face against glass", "beach"))
        self.assertFalse(text_has_concept("a dark interior", "sand"))
        self.assertTrue(text_has_concept("sand falling in an hourglass", "sand"))

    def test_single_required_visual_dimension_is_allowed(self):
        value = manifest()
        scene = value["scenes"][0]
        scene["visual_match"] = "EXACT"
        scene["visual_semantics"] = {
            "role": "literal",
            "required": {"objects": ["clock"]},
            "preferred": {},
            "forbidden": [],
        }
        asset = {
            "visual_evidence": {
                "source_title": "Analog wall clock",
                "objects": ["clock"],
                "reviewed": True,
                "basis": "test fixture",
            }
        }
        report = visual_match_report(scene, asset, require_review=True)
        self.assertEqual(report["status"], "PASS")

    def test_semantic_gate_rejects_medical_vial_for_hotel_beat(self):
        value = manifest()
        scene = value["scenes"][0]
        scene["visual_semantics"]["forbidden"] = ["medical_vial", "laboratory"]
        scene["asset"]["visual_evidence"] = {
            "source_title": "Medical ampoule on a table",
            "subjects": ["object"],
            "actions": ["standing"],
            "environments": ["laboratory"],
            "objects": ["medical_vial"],
            "reviewed": True,
            "basis": "test fixture",
        }
        with self.assertRaisesRegex(VideoContractError, "forbidden concepts detected"):
            validate_manifest(value, Path("/tmp"), check_files=False)

    def test_research_quarantines_context_free_candidate(self):
        value = manifest()
        result = build_queue(value, {
            "mixkit": lambda query, limit: [{
                "title": "Beautiful abstract object",
                "duration_seconds": 15,
                "width": 1080,
                "height": 1920,
                "visual_evidence": {"moods": ["eerie"]},
            }]
        })
        self.assertEqual(result["scenes"][0]["candidates"], [])
        self.assertEqual(len(result["scenes"][0]["rejected_candidates"]), 1)
        self.assertEqual(
            result["scenes"][0]["rejected_candidates"][0]["selection_status"],
            "REJECTED_SEMANTIC_MISMATCH",
        )

    def test_contract_rejects_consecutive_dip_to_black_transitions(self):
        value = manifest()
        value["scenes"][1]["transition"] = {"type": "dip_to_black", "duration": 0.14}
        value["scenes"][2]["transition"] = {"type": "dip_to_black", "duration": 0.14}
        with self.assertRaisesRegex(VideoContractError, "consecutive dip_to_black"):
            validate_manifest(value, Path("/tmp"), check_files=False)


if __name__ == "__main__":
    unittest.main()


