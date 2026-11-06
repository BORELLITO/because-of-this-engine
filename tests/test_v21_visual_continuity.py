import unittest

from production.video_asset_research import query_variants_for_scene
from production.visual_continuity import (
    continuity_match_report,
    validate_sequence,
)
from production.visual_provider_policy import (
    host_allowed,
    license_allowed,
    policy_for,
)


PROFILE = {
    "schema_version": "1.0",
    "profile_id": "test-cold-war",
    "world": {
        "era": ["1983", "cold_war", "analog"],
        "setting": ["technical_control_room"],
        "time_of_day": ["night", "indeterminate_low_light"],
        "lighting": ["low_key", "cool_shadows"],
        "palette": ["charcoal", "steel", "warning_red"],
        "texture": ["crt_phosphor", "brushed_metal", "low_light_grain"],
    },
    "hard_constraints": {
        "era": ["1983", "cold_war", "analog"],
        "setting": ["technical_control_room"],
        "time_of_day": ["night", "indeterminate_low_light"],
        "lighting": ["low_key", "cool_shadows"],
        "palette": ["charcoal", "steel", "warning_red"],
        "texture": ["crt_phosphor", "brushed_metal", "low_light_grain"],
    },
    "hard_forbidden": ["smartphone", "bright_modern_ui"],
    "allowed_source_tiers": ["stock_auto", "archive_manual", "government_manual", "cc_manual"],
    "transition_policy": {
        "allow_bridge_shots": True,
        "max_hard_conflicts": 0,
        "required_adjacency_review": True,
    },
    "enforcement": {
        "manifest": "advisory",
        "preview": "block",
        "final": "block",
    },
    "search_terms": ["1983 Cold War bunker", "night CRT control panel"],
}


def tags(**overrides):
    result = {
        "era": ["1983", "cold_war", "analog"],
        "setting": ["technical_control_room"],
        "time_of_day": ["night", "indeterminate_low_light"],
        "lighting": ["low_key", "cool_shadows"],
        "palette": ["charcoal", "steel"],
        "texture": ["crt_phosphor", "brushed_metal"],
    }
    result.update(overrides)
    return result


class VisualContinuityTests(unittest.TestCase):
    def test_search_query_includes_world_terms(self):
        scene = {
            "scene_id": "S01",
            "story_beat": "an alert begins",
            "visual_intent": "warning panel",
            "continuity_tags": tags(),
        }
        variants = query_variants_for_scene(scene, PROFILE)
        self.assertTrue(any("1983" in query for query in variants))
        self.assertTrue(any("night" in query for query in variants))
        self.assertTrue(any("crt" in query for query in variants))

    def test_period_compatible_candidate_passes(self):
        scene = {"scene_id": "S01", "continuity_tags": tags()}
        report = continuity_match_report(
            scene,
            {"source_tier": "stock_auto", "continuity_tags": tags()},
            PROFILE,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(report["score"], 0.72)
        self.assertEqual(report["conflicts"], [])

    def test_modern_daylight_candidate_is_blocked(self):
        scene = {"scene_id": "S01", "continuity_tags": tags()}
        report = continuity_match_report(
            scene,
            {
                "source_tier": "stock_auto",
                "continuity_tags": tags(
                    era=["modern", "digital"],
                    time_of_day=["daylight", "sunlight"],
                    lighting=["high_key", "sunlit"],
                ),
            },
            PROFILE,
        )
        self.assertEqual(report["status"], "BLOCKED")
        self.assertGreaterEqual(len(report["conflicts"]), 2)

    def test_preview_gate_blocks_bad_sequence_but_manifest_can_review(self):
        sequence = [
            {
                "shot_id": "S01",
                "scene": {"shot_id": "S01", "continuity_tags": tags()},
                "asset": {"continuity_tags": tags(), "source_tier": "stock_auto"},
            },
            {
                "shot_id": "S02",
                "scene": {"shot_id": "S02", "continuity_tags": tags()},
                "asset": {
                    "continuity_tags": tags(
                        time_of_day=["daylight"],
                        lighting=["high_key"],
                    ),
                    "source_tier": "stock_auto",
                },
            },
        ]
        manifest_report = validate_sequence(sequence, PROFILE, mode="manifest")
        preview_report = validate_sequence(sequence, PROFILE, mode="preview")
        self.assertEqual(manifest_report["status"], "REVIEW_REQUIRED")
        self.assertEqual(preview_report["status"], "BLOCKED")
        self.assertTrue(preview_report["strict_preview_block"])

    def test_manual_provider_license_and_hosts_are_explicit(self):
        policy = policy_for("wikimedia")
        self.assertIsNotNone(policy)
        self.assertTrue(license_allowed(policy, "CC BY 4.0"))
        self.assertTrue(host_allowed("upload.wikimedia.org", policy["media_hosts"]))
        self.assertFalse(license_allowed(policy, "Personal Use Only"))
        self.assertTrue(policy["manual_only"])
        self.assertEqual(policy["source_tier"], "cc_manual")


if __name__ == "__main__":
    unittest.main()
