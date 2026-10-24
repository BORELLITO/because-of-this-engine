#!/usr/bin/env python3
"""Editorial pacing and clip-quantity policy for Because of This Engine v2.

The policy keeps the current validated pilot reproducible while making every
new episode dynamic, visually denser and fail-closed against under-edited
timelines.
"""

from __future__ import annotations

from typing import Any

DEFAULT_CLIP_QUANTITY_POLICY = {
    "mode": "adaptive",
    "min_clips": 10,
    "target_min": 12,
    "target_max": 16,
    "max_clips": 18,
    "min_scene_seconds": 2.0,
    "max_scene_seconds": 20.0,
    "enforce": True,
}

_ALLOWED_MODES = {"adaptive", "fixed"}
_REQUIRED_NUMERIC = ("min_clips", "target_min", "target_max", "max_clips", "min_scene_seconds", "max_scene_seconds")


class EditorialPolicyError(ValueError):
    """Raised when the editorial policy is invalid."""


def clip_quantity_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a validated policy, defaulting to the strict v2 standard.

    A manifest may explicitly set enforce=false only for an existing approved
    baseline or a deliberately marked pilot. That exception is visible in the
    manifest and does not weaken future episodes.
    """
    editing = manifest.get("editing") or {}
    if not isinstance(editing, dict):
        raise EditorialPolicyError("editing must be an object.")
    raw = editing.get("clip_quantity") or {}
    if not isinstance(raw, dict):
        raise EditorialPolicyError("editing.clip_quantity must be an object.")

    policy = {**DEFAULT_CLIP_QUANTITY_POLICY, **raw}
    if policy["mode"] not in _ALLOWED_MODES:
        raise EditorialPolicyError("editing.clip_quantity.mode is invalid.")
    if not isinstance(policy["enforce"], bool):
        raise EditorialPolicyError("editing.clip_quantity.enforce must be boolean.")

    for key in _REQUIRED_NUMERIC:
        value = policy[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EditorialPolicyError(f"editing.clip_quantity.{key} must be numeric.")
        if value <= 0:
            raise EditorialPolicyError(f"editing.clip_quantity.{key} must be positive.")

    integer_fields = ("min_clips", "target_min", "target_max", "max_clips")
    for key in integer_fields:
        value = policy[key]
        if int(value) != value:
            raise EditorialPolicyError(f"editing.clip_quantity.{key} must be an integer.")
        policy[key] = int(value)

    if not (
        1 <= policy["min_clips"] <= policy["target_min"]
        <= policy["target_max"] <= policy["max_clips"]
    ):
        raise EditorialPolicyError("Clip quantity bounds must be min <= target_min <= target_max <= max.")
    if policy["min_scene_seconds"] > policy["max_scene_seconds"]:
        raise EditorialPolicyError("Scene duration bounds are inverted.")

    return policy


def clip_quantity_report(scene_count: int, policy: dict[str, Any]) -> dict[str, Any]:
    """Describe the quantity gate without silently approving a weak timeline."""
    if scene_count < policy["min_clips"] or scene_count > policy["max_clips"]:
        status = "BLOCKED" if policy["enforce"] else "ADVISORY"
    elif policy["target_min"] <= scene_count <= policy["target_max"]:
        status = "TARGET_PASS"
    else:
        status = "MINIMUM_PASS"

    return {
        "status": status,
        "scene_count": scene_count,
        "min_clips": policy["min_clips"],
        "target_range": [policy["target_min"], policy["target_max"]],
        "max_clips": policy["max_clips"],
        "enforced": policy["enforce"],
        "mode": policy["mode"],
    }


def validate_clip_quantity(scene_count: int, policy: dict[str, Any]) -> dict[str, Any]:
    report = clip_quantity_report(scene_count, policy)
    if report["status"] == "BLOCKED":
        raise EditorialPolicyError(
            f"Episode requires {policy['min_clips']}-{policy['max_clips']} unique video clips; "
            f"got {scene_count}."
        )
    return report
