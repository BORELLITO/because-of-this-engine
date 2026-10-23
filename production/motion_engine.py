#!/usr/bin/env python3
"""Deterministic editorial motion and transition selection.

This module deliberately contains no randomness.  A scene receives movement
from its narrative metadata, subject focus and neighbouring scenes.  The
renderer consumes the normalized result, while the validator uses the same
rules to fail closed before an export can hide an editorial mistake.
"""

from __future__ import annotations

from typing import Any

MOTION_TYPES = (
    "slow_push_in",
    "slow_pull_out",
    "pan_left",
    "pan_right",
    "pan_up",
    "pan_down",
    "focus_reframe",
    "static_hold",
    "subtle_rotation_push_in",
)

TRANSITION_TYPES = (
    "crossfade",
    "soft_dissolve",
    "dip_to_black",
    "hard_cut",
    "motion_match",
)

EASINGS = ("linear", "smoothstep", "ease_in_out")


def _text(scene: dict[str, Any]) -> str:
    values = (
        scene.get("story_beat"),
        scene.get("visual_intent"),
        scene.get("emotion"),
        scene.get("image_type"),
        scene.get("notes"),
    )
    return " ".join(str(value or "") for value in values).lower()


def _contains(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def choose_motion(
    scene: dict[str, Any],
    previous_motion: str | None = None,
    next_scene: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return a motion type and a human-readable reason.

    The rule order is intentional: reveal/consequence beats get priority over
    generic image type labels, and repetition is resolved deterministically.
    """
    text = _text(scene)
    if _contains(text, "reveal", "consequence", "danger", "catastrophe", "payoff", "discovery"):
        candidate, reason = "slow_push_in", "narrative pressure or reveal"
    elif _contains(text, "establish", "context", "location", "wide", "travel", "journey"):
        candidate, reason = "slow_pull_out", "establishing context or scale"
    elif _contains(text, "evidence", "document", "investigation", "instrument", "detail"):
        candidate, reason = "focus_reframe", "direct attention to evidence"
    elif _contains(text, "isolation", "waiting", "silence", "aftermath"):
        candidate, reason = "static_hold", "let an emotional beat breathe"
    elif _contains(text, "movement", "orbit", "trajectory", "route", "direction"):
        candidate, reason = "pan_right", "follow a physical direction"
    else:
        candidate, reason = "slow_push_in", "safe editorial default"

    # A scene should not repeat its predecessor's exact movement.  The
    # fallback is still semantically conservative and never random.
    if candidate == previous_motion:
        alternatives = {
            "slow_push_in": "focus_reframe",
            "slow_pull_out": "pan_right",
            "focus_reframe": "static_hold",
            "static_hold": "slow_pull_out",
            "pan_right": "pan_left",
            "pan_left": "pan_right",
        }
        candidate = alternatives.get(candidate, "static_hold")
        reason += "; repetition guard"
    return candidate, reason


def choose_transition(
    scene: dict[str, Any],
    index: int,
    previous_scene: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Choose an understated transition from narrative context."""
    if index == 0:
        return "hard_cut", "opening frame"
    text = _text(scene)
    if _contains(text, "reveal", "consequence", "catastrophe", "payoff"):
        return "dip_to_black", "mark a reveal or consequence"
    if previous_scene and _contains(_text(previous_scene), "location", "establish", "context"):
        return "soft_dissolve", "move from context into detail"
    if _contains(text, "movement", "orbit", "trajectory", "route"):
        return "motion_match", "preserve directional energy"
    return "crossfade", "neutral continuity"


def normalize_motion(scene: dict[str, Any], index: int, previous_motion: str | None = None) -> dict[str, Any]:
    """Normalize an optional scene motion object without changing its meaning."""
    requested = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}
    motion_type = requested.get("type")
    if motion_type is None:
        motion_type, reason = choose_motion(scene, previous_motion)
    else:
        reason = "explicit scene direction"
    if motion_type not in MOTION_TYPES:
        raise ValueError(f"Unsupported motion type for scene {scene.get('scene_id', index + 1)}: {motion_type}")
    easing = requested.get("easing", "smoothstep")
    if easing not in EASINGS:
        raise ValueError(f"Unsupported easing for scene {scene.get('scene_id', index + 1)}: {easing}")
    intensity = requested.get("intensity", 1)
    if not isinstance(intensity, (int, float)) or not 0.0 < float(intensity) <= 2.0:
        raise ValueError(f"Motion intensity must be in (0, 2] for scene {scene.get('scene_id', index + 1)}")
    focus = requested.get("focus", scene.get("focus", {"x": 0.5, "y": 0.5}))
    if not isinstance(focus, dict):
        raise ValueError(f"Motion focus must be an object for scene {scene.get('scene_id', index + 1)}")
    x, y = float(focus.get("x", 0.5)), float(focus.get("y", 0.5))
    if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
        raise ValueError(f"Motion focus must stay inside 0..1 for scene {scene.get('scene_id', index + 1)}")
    return {
        "type": motion_type,
        "easing": easing,
        "intensity": float(intensity),
        "focus": {"x": x, "y": y},
        "selection_reason": reason,
    }


def normalize_transition(scene: dict[str, Any], default_duration: float, index: int) -> dict[str, Any]:
    requested = scene.get("transition") if isinstance(scene.get("transition"), dict) else {}
    transition_type = requested.get("type", "crossfade" if index else "hard_cut")
    if transition_type not in TRANSITION_TYPES:
        raise ValueError(f"Unsupported transition type for scene {scene.get('scene_id', index + 1)}: {transition_type}")
    duration = requested.get("duration", 0.0 if transition_type == "hard_cut" else default_duration)
    if not isinstance(duration, (int, float)) or duration < 0:
        raise ValueError(f"Transition duration must be non-negative for scene {scene.get('scene_id', index + 1)}")
    # FFmpeg's xfade needs a positive interval. A hard cut is represented by
    # one frame (25 fps), which is perceptually a cut and keeps the timeline
    # arithmetic honest.
    if transition_type == "hard_cut" and float(duration) == 0.0:
        duration = 1.0 / 25.0
    return {"type": transition_type, "duration": float(duration)}


def validate_motion_sequence(scenes: list[dict[str, Any]]) -> list[str]:
    """Return human-readable warnings for variety problems."""
    warnings: list[str] = []
    motions = [scene.get("motion", {}).get("type") for scene in scenes]
    for index in range(2, len(motions)):
        if motions[index] and motions[index] == motions[index - 1] == motions[index - 2]:
            warnings.append(f"three consecutive scenes repeat motion {motions[index]}")
    return warnings

