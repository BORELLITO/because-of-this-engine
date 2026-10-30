from __future__ import annotations

import unittest

from production.render_video_episode import scene_filter
from production.visual_effects_v73 import (
    PROFILE_ID,
    PROFILE_VERSION,
    VisualEffectsError,
    validate_cinematic_suspense,
)


PROFILE = {
    "enabled": True,
    "preset": PROFILE_ID,
    "brightness": -0.05,
    "contrast": 1.14,
    "saturation": 0.84,
    "gamma": 0.92,
    "vignette": True,
    "cinematic_suspense": {
        "enabled": True,
        "profile": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "reference_basis": "cinematic_dread_v73_before_after_comparison",
        "cool_shadows": 0.04,
        "warm_highlights": 0.014,
        "motion_strength": 0.045,
        "push_in": 0.055,
        "edge_fade": True,
        "shadow_crush": 0.045,
        "highlight_rolloff": 0.012,
        "flicker_strength": 0.003,
        "flicker_period_seconds": 4.8,
        "detail_strength": 0.16,
        "vignette_angle": "PI/5.8",
    },
}


class VisualEffectsV731Tests(unittest.TestCase):
    def test_active_profile_is_validated_and_normalized(self) -> None:
        value = validate_cinematic_suspense(PROFILE, require_active_profile=True)
        self.assertEqual(value["profile"], PROFILE_ID)
        self.assertEqual(value["profile_version"], PROFILE_VERSION)
        self.assertEqual(value["shadow_crush"], 0.045)

    def test_renderer_contains_all_calibrated_dread_layers(self) -> None:
        graph = scene_filter(1080, 1920, 0.5, 0.5, PROFILE, duration=8.0)
        self.assertIn("eq=", graph)
        self.assertIn(":eval=frame", graph)
        self.assertIn("colorlevels=", graph)
        self.assertIn("colorbalance=", graph)
        self.assertIn("unsharp=", graph)
        self.assertNotIn("preserve=lum", graph)
        self.assertIn("vignette=angle=PI/5.8", graph)
        self.assertIn("scale=1080:1920", graph)

    def test_legacy_profile_cannot_enter_active_production(self) -> None:
        legacy = {
            "enabled": True,
            "cinematic_suspense": {
                "enabled": True,
                "profile": "investigative_noir_suspense",
            },
        }
        with self.assertRaises(VisualEffectsError):
            validate_cinematic_suspense(legacy, require_active_profile=True)

    def test_effect_ranges_fail_closed(self) -> None:
        invalid = {**PROFILE, "cinematic_suspense": {
            **PROFILE["cinematic_suspense"],
            "shadow_crush": 0.50,
        }}
        with self.assertRaises(VisualEffectsError):
            validate_cinematic_suspense(invalid, require_active_profile=True)


if __name__ == "__main__":
    unittest.main()
