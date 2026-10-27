import unittest
from pathlib import Path

from production.video_asset_contract import VideoContractError, validate_manifest
from production.render_video_episode import RenderError, narration_locked_scenes, scene_filter, xfade_filter
from production.video_asset_research import build_queue, query_variants_for_scene
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
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

    def test_video_contract_rejects_repeated_animation_checksum(self):
        value = manifest()
        value["scenes"][1]["asset"]["sha256"] = value["scenes"][0]["asset"]["sha256"]
        with self.assertRaisesRegex(VideoContractError, "sha256 is repeated"):
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

    def test_video_contract_rejects_duplicate_runtime_asset_path(self):
        value = manifest()
        value["scenes"][1]["asset"]["path"] = value["scenes"][0]["asset"]["path"]
        with self.assertRaisesRegex(VideoContractError, "Runtime asset path is repeated"):
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

    def test_contract_requires_sixty_to_seventy_five_seconds(self):
        value = manifest()
        value["scenes"][0]["duration"] = 2
        with self.assertRaisesRegex(VideoContractError, "between 60s and 75s"):
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

    def test_renderer_uses_vertical_video_crop_and_fixed_fps(self):
        value = scene_filter(1080, 1920, 0.5, 0.5)
        self.assertIn("force_original_aspect_ratio=increase", value)
        self.assertIn("fps=25", value)
        self.assertNotIn("zoompan", value)
        self.assertIn("setsar=1", value)

    def test_cinematic_suspense_grade_is_explicit_and_safe(self):
        value = scene_filter(1080, 1920, 0.5, 0.5, {
            "enabled": True,
            "preset": "investigative_noir_suspense",
            "brightness": -0.03,
            "contrast": 1.08,
            "saturation": 0.90,
            "gamma": 0.96,
            "vignette": True,
            "cinematic_suspense": {
                "enabled": True,
                "cool_shadows": 0.025,
                "warm_highlights": 0.010,
            },
        })
        self.assertIn("colorbalance=", value)
        self.assertIn("vignette=PI/5", value)
        self.assertIn("eq=brightness=-0.0300:contrast=1.0800", value)

    def test_transitions_are_narration_timeline_aware(self):
        value = xfade_filter([15, 15, 15], [{"type": "crossfade", "duration": 0.25}] * 2)
        self.assertIn("trim=duration=14.750", value)
        self.assertIn("trim=duration=15.000", value)
        self.assertIn("concat=n=3:v=1:a=0", value)
        self.assertIn("setsar=1", value)

    def test_production_timing_requires_forced_alignment(self):
        with self.assertRaisesRegex(RenderError, "Forced-alignment narration spans are mandatory"):
            narration_locked_scenes(manifest()["scenes"], 70.2)

    def test_enforced_clip_quantity_blocks_underedited_episode(self):
        value = manifest()
        value["editing"]["clip_quantity"]["enforce"] = True
        with self.assertRaisesRegex(VideoContractError, "requires 10-18 unique video clips"):
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

    def test_exact_match_requires_stronger_semantic_score(self):
        value = manifest()
        value["scenes"][0]["match_score"] = 0.79
        with self.assertRaisesRegex(VideoContractError, "EXACT semantic-match threshold"):
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

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
        self.assertFalse(text_has_concept("sand falling in an hourglass", "beach"))

    def test_editorial_notes_cannot_create_semantic_matches(self):
        value = manifest()
        scene = value["scenes"][0]
        scene["visual_match"] = "EXACT"
        scene["visual_semantics"] = {
            "role": "literal",
            "required": {
                "subjects": ["security_guard"],
                "actions": ["standing"],
                "environments": ["interior"],
            },
            "preferred": {},
            "forbidden": [],
        }
        asset = {
            "visual_evidence": {
                "source_title": "Woman in a dim room",
                "subjects": ["person"],
                "actions": ["standing"],
                "environments": ["interior"],
                "notes": "This is not a security guard; recollect the clip.",
                "reviewed": True,
                "basis": "test fixture",
            }
        }
        report = visual_match_report(scene, asset, require_review=True)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("security_guard", report["missing"]["subjects"])

    def test_negative_story_beat_rejects_present_figure(self):
        value = manifest()
        scene = value["scenes"][0]
        scene["visual_match"] = "NEAR"
        scene["visual_semantics"] = {
            "role": "literal",
            "required": {"environments": ["hallway"]},
            "preferred": {"objects": ["footprints"]},
            "forbidden": ["person", "silhouette"],
        }
        asset = {
            "visual_evidence": {
                "source_title": "Ghost in the hall",
                "subjects": ["silhouette"],
                "environments": ["hallway"],
                "reviewed": True,
                "basis": "test fixture",
            }
        }
        report = visual_match_report(scene, asset, require_review=True)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("silhouette", report["forbidden_hits"])

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
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)

    def test_research_translates_negative_narrative_context(self):
        value = manifest()
        scene = value["scenes"][0]
        scene["narration_excerpt"] = "They found no footprints and no person inside the hallway."
        scene["visual_semantics"] = {
            "role": "literal",
            "required": {"environments": ["hallway"]},
            "preferred": {"objects": ["footprints"]},
            "forbidden": ["person", "silhouette"],
        }
        queries = query_variants_for_scene(scene)
        self.assertIn("empty", queries[0])
        self.assertIn("unoccupied", queries[0])
        self.assertNotIn("person", queries[0].split())
        self.assertNotIn("footprints", queries[0].split())

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
            validate_manifest(value, Path("/tmp"), check_files=False, enforce_canonical=False)


if __name__ == "__main__":
    unittest.main()


