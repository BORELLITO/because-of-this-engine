#!/usr/bin/env python3
"""Canonical V7.3.2 cinematic-dread visual-effects contract.

The effect profile is intentionally deterministic and conservative: it increases
perceived dread through shadow shaping, restrained color separation, a controlled
luminance pulse and vignette without adding authored text, objects or narrative
content to source clips.
"""

from __future__ import annotations

from typing import Any

PROFILE_ID = "cinematic_dread_v73"
PROFILE_VERSION = "7.3.2"
REFERENCE_BASIS = "cinematic_dread_v73_before_after_comparison"


class VisualEffectsError(ValueError):
    """Raised when a visual-effects profile is incomplete or unsafe."""


def _number(profile: dict[str, Any], key: str, default: float) -> float:
    value = profile.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisualEffectsError(f"cinematic_suspense.{key} must be numeric")
    return float(value)


def validate_cinematic_suspense(
    color_grade: dict[str, Any] | None,
    *,
    require_active_profile: bool = False,
) -> dict[str, Any]:
    """Validate and normalize the active cinematic-dread profile.

    Legacy V7.3 manifests without the new profile remain readable for rollback
    and audit. Production manifests must declare the new profile explicitly.
    """

    grade = color_grade or {}
    suspense = grade.get("cinematic_suspense") or {}
    if not isinstance(suspense, dict):
        raise VisualEffectsError("color_grade.cinematic_suspense must be an object")
    if suspense.get("enabled") is not True:
        return {"enabled": False, "profile": "disabled"}

    profile = str(suspense.get("profile", "investigative_noir_suspense"))
    if profile == "investigative_noir_suspense":
        if require_active_profile:
            raise VisualEffectsError(
                f"active production requires profile {PROFILE_ID!r}, got {profile!r}"
            )
        return {
            "enabled": True,
            "profile": profile,
            "motion_strength": _number(suspense, "motion_strength", 0.035),
            "push_in": _number(suspense, "push_in", 0.045),
            "cool_shadows": _number(suspense, "cool_shadows", 0.025),
            "warm_highlights": _number(suspense, "warm_highlights", 0.010),
            "shadow_crush": 0.0,
            "highlight_rolloff": 0.0,
            "flicker_strength": 0.0,
            "flicker_period_seconds": 4.8,
            "detail_strength": 0.0,
            "vignette_angle": "PI/5",
            "edge_fade": suspense.get("edge_fade") is True,
        }

    if profile != PROFILE_ID:
        raise VisualEffectsError(f"unsupported cinematic_suspense profile: {profile!r}")
    if str(suspense.get("profile_version", "")) != PROFILE_VERSION:
        raise VisualEffectsError(
            f"cinematic_suspense.profile_version must be {PROFILE_VERSION!r}"
        )
    if str(suspense.get("reference_basis", "")) != REFERENCE_BASIS:
        raise VisualEffectsError(
            "cinematic_suspense.reference_basis must identify the approved before/after calibration"
        )

    motion_smoothing = suspense.get("motion_smoothing", False)
    if not isinstance(motion_smoothing, bool):
        raise VisualEffectsError("cinematic_suspense.motion_smoothing must be boolean")
    interpolation_fps = _number(suspense, "interpolation_fps", 60.0)
    if interpolation_fps != int(interpolation_fps):
        raise VisualEffectsError("cinematic_suspense.interpolation_fps must be an integer")

    normalized = {
        "enabled": True,
        "profile": profile,
        "profile_version": PROFILE_VERSION,
        "reference_basis": REFERENCE_BASIS,
        "motion_smoothing": motion_smoothing,
        "interpolation_fps": int(interpolation_fps),
        "motion_strength": _number(suspense, "motion_strength", 0.045),
        "push_in": _number(suspense, "push_in", 0.055),
        "cool_shadows": _number(suspense, "cool_shadows", 0.040),
        "warm_highlights": _number(suspense, "warm_highlights", 0.014),
        "shadow_crush": _number(suspense, "shadow_crush", 0.045),
        "highlight_rolloff": _number(suspense, "highlight_rolloff", 0.012),
        "flicker_strength": _number(suspense, "flicker_strength", 0.003),
        "flicker_period_seconds": _number(suspense, "flicker_period_seconds", 4.8),
        "detail_strength": _number(suspense, "detail_strength", 0.16),
        "motion_smoothing": motion_smoothing,
        "interpolation_fps": int(interpolation_fps),
        "vignette_angle": str(suspense.get("vignette_angle", "PI/5.8")),
        "edge_fade": suspense.get("edge_fade") is True,
    }

    ranges = {
        "motion_strength": (0.0, 0.08),
        "push_in": (0.0, 0.10),
        "cool_shadows": (0.0, 0.10),
        "warm_highlights": (0.0, 0.06),
        "shadow_crush": (0.0, 0.12),
        "highlight_rolloff": (0.0, 0.08),
        "flicker_strength": (0.0, 0.02),
        "flicker_period_seconds": (2.0, 12.0),
        "detail_strength": (0.0, 0.40),
        "interpolation_fps": (30.0, 120.0),
    }
    for key, (minimum, maximum) in ranges.items():
        value = normalized[key]
        if not minimum <= value <= maximum:
            raise VisualEffectsError(
                f"cinematic_suspense.{key}={value} is outside [{minimum}, {maximum}]"
            )
    if normalized["vignette_angle"] not in {"PI/5", "PI/5.8", "PI/6", "PI/6.2"}:
        raise VisualEffectsError("cinematic_suspense.vignette_angle is not an approved value")
    return normalized


def validate_visual_effects(
    manifest: dict[str, Any],
    *,
    require_active_profile: bool = False,
) -> dict[str, Any]:
    """Validate the complete color/effects section used by the renderer."""

    grade = manifest.get("color_grade")
    if not isinstance(grade, dict):
        raise VisualEffectsError("manifest requires a color_grade object")
    if grade.get("enabled") is not True:
        raise VisualEffectsError("active visual grade must remain enabled")
    brightness = grade.get("brightness")
    contrast = grade.get("contrast")
    saturation = grade.get("saturation")
    gamma = grade.get("gamma")
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           for value in (brightness, contrast, saturation, gamma)):
        raise VisualEffectsError("color_grade base values must be numeric")
    if not -0.20 <= float(brightness) <= 0.20:
        raise VisualEffectsError("color_grade.brightness is outside the safe range")
    if not 0.80 <= float(contrast) <= 1.30:
        raise VisualEffectsError("color_grade.contrast is outside the safe range")
    if not 0.65 <= float(saturation) <= 1.15:
        raise VisualEffectsError("color_grade.saturation is outside the safe range")
    if not 0.80 <= float(gamma) <= 1.15:
        raise VisualEffectsError("color_grade.gamma is outside the safe range")
    suspense = validate_cinematic_suspense(
        grade,
        require_active_profile=require_active_profile,
    )
    return {
        "status": "VISUAL_EFFECTS_V732_PASS",
        "profile": suspense.get("profile"),
        "profile_version": suspense.get("profile_version", "legacy"),
        "reference_basis": suspense.get("reference_basis"),
    }
