from __future__ import annotations

import pytest

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


def test_active_profile_is_validated_and_normalized() -> None:
    value = validate_cinematic_suspense(PROFILE, require_active_profile=True)
    assert value["profile"] == PROFILE_ID
    assert value["profile_version"] == PROFILE_VERSION
    assert value["shadow_crush"] == 0.045


def test_renderer_contains_all_calibrated_dread_layers() -> None:
    graph = scene_filter(1080, 1920, 0.5, 0.5, PROFILE, duration=8.0)
    assert "eq=" in graph and ":eval=frame" in graph
    assert "colorlevels=" in graph
    assert "colorbalance=" in graph
    assert "unsharp=" in graph
    assert "vignette=angle=PI/5.8" in graph
    assert "scale=1080:1920" in graph


def test_legacy_profile_cannot_enter_active_production() -> None:
    legacy = {
        "enabled": True,
        "cinematic_suspense": {
            "enabled": True,
            "profile": "investigative_noir_suspense",
        },
    }
    with pytest.raises(VisualEffectsError):
        validate_cinematic_suspense(legacy, require_active_profile=True)


def test_effect_ranges_fail_closed() -> None:
    invalid = {**PROFILE, "cinematic_suspense": {
        **PROFILE["cinematic_suspense"],
        "shadow_crush": 0.50,
    }}
    with pytest.raises(VisualEffectsError):
        validate_cinematic_suspense(invalid, require_active_profile=True)
