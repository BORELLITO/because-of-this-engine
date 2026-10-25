import unittest

from production.story_intelligence import (
    StoryIntegrityError,
    attach_audio_timestamps,
    audit_manifest,
    validate_narration_coverage,
    validate_story_graph,
)
from production.visual_semantics import text_has_concept, visual_match_report


def base_manifest():
    scenes = [
        {"scene_id": "S01", "narration_excerpt": "The guard waits."},
        {"scene_id": "S02", "narration_excerpt": "The lights go out."},
    ]
    return {
        "video_id": "story-test",
        "script": {"path": "script.txt"},
        "scenes": scenes,
        "story_graph": {
            "version": "1.0",
            "entities": [
                {
                    "entity_id": "guard",
                    "canonical_name": "the guard",
                    "aliases": ["guard", "night guard"],
                    "continuity_mode": "same investigator",
                },
                {
                    "entity_id": "lights",
                    "canonical_name": "the lights",
                    "aliases": ["lights", "light"],
                    "continuity_mode": "single stateful system",
                },
            ],
            "beats": [
                {
                    "scene_id": "S01",
                    "event": "guard waits",
                    "state_before": "guard_absent",
                    "state_after": "guard_waiting",
                    "causal_role": "investigation",
                    "emotion": "anticipation",
                    "visual_motif": "isolated watcher",
                    "entities": ["guard"],
                    "narration_excerpt": "The guard waits.",
                },
                {
                    "scene_id": "S02",
                    "event": "lights go out",
                    "state_before": "guard_waiting",
                    "state_after": "lights_out",
                    "causal_role": "escalation",
                    "emotion": "dread",
                    "visual_motif": "darkness",
                    "entities": ["guard", "lights"],
                    "narration_excerpt": "The lights go out.",
                },
            ],
        },
    }


class StoryIntelligenceTests(unittest.TestCase):
    def test_graph_and_ordered_coverage_pass(self):
        report = audit_manifest(base_manifest(), "The guard waits. The lights go out.")
        self.assertEqual(report["status"], "STORY_INTELLIGENCE_PASS")
        self.assertEqual(report["narration_coverage"]["covered_word_count"], 7)
        self.assertEqual(report["narration_coverage"]["scenes"][1]["word_start_index"], 3)

    def test_coverage_rejects_hidden_gap(self):
        value = base_manifest()
        value["scenes"][1]["narration_excerpt"] = "The lights go out."
        with self.assertRaisesRegex(StoryIntegrityError, "Narration coverage gap before S02"):
            validate_narration_coverage(value, "The guard waits. Then suddenly the lights go out.")

    def test_graph_rejects_state_discontinuity(self):
        value = base_manifest()
        value["story_graph"]["beats"][1]["state_before"] = "different_state"
        with self.assertRaisesRegex(StoryIntegrityError, "state discontinuity"):
            validate_story_graph(value)

    def test_forced_alignment_attaches_scene_times(self):
        value = base_manifest()
        coverage = validate_narration_coverage(value, "The guard waits. The lights go out.")
        alignment = {
            "audio_duration_seconds": 2.4,
            "captions": [
                {
                    "words": [
                        {"canonical": "The", "start": 0.0, "end": 0.2},
                        {"canonical": "guard", "start": 0.2, "end": 0.7},
                        {"canonical": "waits", "start": 0.7, "end": 1.0},
                    ]
                },
                {
                    "words": [
                        {"canonical": "The", "start": 1.2, "end": 1.4},
                        {"canonical": "lights", "start": 1.4, "end": 1.9},
                        {"canonical": "go", "start": 1.9, "end": 2.1},
                        {"canonical": "out", "start": 2.1, "end": 2.4},
                    ]
                },
            ],
        }
        attach_audio_timestamps(coverage, alignment, "The guard waits. The lights go out.")
        self.assertEqual(coverage["timing_status"], "FORCED_ALIGNMENT_SCENE_TIMES_PASS")
        self.assertEqual(coverage["scenes"][0]["audio_start"], 0.0)
        self.assertEqual(coverage["scenes"][1]["audio_end"], 2.4)

    def test_generic_monitor_does_not_match_security_camera(self):
        self.assertFalse(text_has_concept("generic monitor in an office", "security_camera"))
        self.assertTrue(text_has_concept("security camera recording a hallway", "security_camera"))
        self.assertFalse(text_has_concept("the recording is visible", "screen"))

    def test_source_url_is_not_visual_proof(self):
        scene = {
            "scene_id": "S01",
            "visual_match": "EXACT",
            "visual_semantics": {
                "role": "literal",
                "required": {"objects": ["glass_door"]},
                "critical": {"objects": ["glass_door"]},
                "preferred": {},
                "forbidden": ["medical_vial"],
            },
        }
        candidate = {
            "source_page_url": "https://example.test/medical-vial",
            "visual_evidence": {
                "source_title": "Interior with glass door",
                "objects": ["glass_door"],
                "reviewed": True,
                "basis": "pixel review",
            },
        }
        report = visual_match_report(scene, candidate, require_review=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["forbidden_hits"], [])

    def test_missing_critical_anchor_blocks_even_when_other_fields_match(self):
        scene = {
            "scene_id": "S01",
            "visual_match": "EXACT",
            "visual_semantics": {
                "role": "literal",
                "required": {"environments": ["interior"]},
                "critical": {"objects": ["glass_door"]},
                "preferred": {},
                "forbidden": [],
            },
        }
        candidate = {
            "visual_evidence": {
                "source_title": "Dark interior",
                "environments": ["interior"],
                "reviewed": True,
                "basis": "pixel review",
            },
        }
        report = visual_match_report(scene, candidate, require_review=True)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("glass_door", report["critical_missing"]["objects"])


if __name__ == "__main__":
    unittest.main()
