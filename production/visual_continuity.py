#!/usr/bin/env python3
"""Sequence-level visual continuity gates for the Because Of This engine.

The semantic matcher answers "does this clip depict the requested beat?".
This module answers the second question the editor needs: "does it belong to
the same visual world as the shots around it?"  It is deliberately metadata
first: an unknown tag is a review signal, never an invented fact.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


CONTINUITY_SCHEMA_VERSION = "1.0"
CONTINUITY_DIMENSIONS = (
    "era",
    "setting",
    "time_of_day",
    "lighting",
    "palette",
    "texture",
)
DIMENSION_WEIGHTS = {
    "era": 0.18,
    "setting": 0.24,
    "time_of_day": 0.18,
    "lighting": 0.16,
    "palette": 0.12,
    "texture": 0.12,
}
ENFORCEMENT_MODES = {"advisory", "block"}
SEQUENCE_MODES = {"manifest", "draft-preview", "preview", "final"}

# These are deliberately small, high-signal equivalence families.  They do
# not turn free text into evidence; they only make controlled tags comparable.
_TERM_FAMILIES = (
    frozenset({"night", "low_light", "indeterminate_low_light", "dark"}),
    frozenset({"daylight", "sunlight", "bright_day", "high_key"}),
    frozenset({"analog", "crt", "period_compatible", "cold_war", "1983"}),
    frozenset({"modern", "digital", "smartphone", "bright_modern_ui"}),
    frozenset({"low_key", "cool_shadows", "restrained_red", "restrained_amber"}),
    frozenset({"metal", "brushed_metal", "industrial", "control_room"}),
)


class VisualContinuityError(ValueError):
    """Raised when a continuity profile is malformed."""


def _term(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .split()
    )


def _terms(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values: Iterable[Any] = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        values = [value]
    result: list[str] = []
    for item in values:
        normalized = _term(item)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _family(term: str) -> frozenset[str] | None:
    normalized = _term(term).replace(" ", "_")
    for family in _TERM_FAMILIES:
        if normalized in family:
            return family
    return None


def _token_sequence_contains(needle: list[str], haystack: list[str]) -> bool:
    """Match whole underscore-delimited tags, never partial words.

    A tag such as "night" may match "night_sky"; it must not match the
    unrelated compound "neon_nightclub" merely because "night" is a
    substring of "nightclub".
    """
    if not needle or not haystack or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(
        haystack[index:index + width] == needle
        for index in range(len(haystack) - width + 1)
    )


def _term_matches(expected: str, actual: str) -> bool:
    left = _term(expected).replace(" ", "_")
    right = _term(actual).replace(" ", "_")
    if not left or not right:
        return False
    if left == right:
        return True
    left_tokens = left.split("_")
    right_tokens = right.split("_")
    if _token_sequence_contains(left_tokens, right_tokens):
        return True
    if _token_sequence_contains(right_tokens, left_tokens):
        return True
    family = _family(left)
    return family is not None and right in family


def _overlap(expected: list[str], actual: list[str]) -> list[str]:
    return [
        item for item in expected
        if any(_term_matches(item, candidate) for candidate in actual)
    ]


def _profile_source(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    candidate = record.get("visual_continuity_profile")
    if candidate is None:
        candidate = record.get("visual_continuity")
    return candidate if isinstance(candidate, dict) else None


def continuity_profile(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a normalized profile attached to a plan, manifest or story."""
    raw = _profile_source(record)
    if raw is None:
        return None
    return normalize_profile(raw)


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise VisualContinuityError("visual_continuity_profile must be an object.")
    version = str(profile.get("schema_version", CONTINUITY_SCHEMA_VERSION))
    if version != CONTINUITY_SCHEMA_VERSION:
        raise VisualContinuityError(
            f"Unsupported visual continuity schema: {version}"
        )

    world_raw = _mapping(profile.get("world"))
    world: dict[str, list[str]] = {}
    for dimension in CONTINUITY_DIMENSIONS:
        world[dimension] = _terms(world_raw.get(dimension))

    hard_raw = _mapping(profile.get("hard_constraints"))
    hard_constraints: dict[str, list[str]] = {}
    for dimension in CONTINUITY_DIMENSIONS:
        hard_constraints[dimension] = _terms(
            hard_raw.get(dimension, world.get(dimension))
        )

    forbidden = _terms(profile.get("hard_forbidden"))
    allowed_tiers = _terms(profile.get("allowed_source_tiers"))
    if not allowed_tiers:
        allowed_tiers = ["stock_auto", "archive_manual", "government_manual", "cc_manual", "original"]

    transition_raw = _mapping(profile.get("transition_policy"))
    transition_policy = {
        "allow_bridge_shots": bool(transition_raw.get("allow_bridge_shots", True)),
        "max_hard_conflicts": int(transition_raw.get("max_hard_conflicts", 0)),
        "required_adjacency_review": bool(
            transition_raw.get("required_adjacency_review", True)
        ),
    }
    if transition_policy["max_hard_conflicts"] < 0:
        raise VisualContinuityError("transition_policy.max_hard_conflicts cannot be negative.")

    enforcement_raw = _mapping(profile.get("enforcement"))
    enforcement: dict[str, str] = {}
    for mode in ("manifest", "draft-preview", "preview", "final"):
        value = str(enforcement_raw.get(mode, "advisory" if mode == "manifest" else "block")).lower()
        if value not in ENFORCEMENT_MODES:
            raise VisualContinuityError(
                f"enforcement.{mode} must be advisory or block."
            )
        enforcement[mode] = value

    search_terms = _terms(profile.get("search_terms"))
    return {
        "schema_version": CONTINUITY_SCHEMA_VERSION,
        "profile_id": str(profile.get("profile_id", "")).strip(),
        "world": world,
        "hard_constraints": hard_constraints,
        "hard_forbidden": forbidden,
        "allowed_source_tiers": allowed_tiers,
        "transition_policy": transition_policy,
        "enforcement": enforcement,
        "search_terms": search_terms,
    }


def _scene_tags(scene: dict[str, Any] | None, profile: dict[str, Any]) -> dict[str, list[str]]:
    scene = scene if isinstance(scene, dict) else {}
    raw = scene.get("continuity_tags") or scene.get("visual_continuity_tags") or {}
    raw = _mapping(raw)
    tags: dict[str, list[str]] = {}
    for dimension in CONTINUITY_DIMENSIONS:
        scene_values = _terms(raw.get(dimension))
        tags[dimension] = scene_values or list(profile["world"].get(dimension, []))
    return tags


def _candidate_tags(candidate: dict[str, Any] | None) -> dict[str, list[str]]:
    candidate = candidate if isinstance(candidate, dict) else {}
    raw = candidate.get("continuity_tags") or candidate.get("visual_continuity_tags") or {}
    raw = _mapping(raw)
    return {
        dimension: _terms(raw.get(dimension))
        for dimension in CONTINUITY_DIMENSIONS
    }


def continuity_search_terms(
    scene: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> list[str]:
    """Build auditable continuity-aware search terms for one scene."""
    normalized = normalize_profile(profile) if profile else None
    values: list[str] = []
    tags = _scene_tags(scene, normalized) if normalized else _mapping(
        scene.get("continuity_tags") or scene.get("visual_continuity_tags")
    )
    if isinstance(tags, dict):
        for dimension in CONTINUITY_DIMENSIONS:
            values.extend(_terms(tags.get(dimension)))
    if normalized:
        values.extend(normalized["search_terms"])
        for dimension in ("era", "setting", "time_of_day", "lighting"):
            values.extend(normalized["world"].get(dimension, []))
    for value in (
        scene.get("visual_intent"),
        scene.get("story_beat"),
        scene.get("role"),
    ):
        values.extend(_terms(value))
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result[:18]


def _hard_conflicts(
    expected: dict[str, list[str]],
    actual: dict[str, list[str]],
    profile: dict[str, Any],
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    conflict_pairs = {
        "time_of_day": (
            ({"night", "low_light", "indeterminate_low_light"}, {"daylight", "sunlight", "bright_day"}),
            ({"daylight", "sunlight", "bright_day"}, {"night", "low_light", "indeterminate_low_light"}),
        ),
        "lighting": (
            ({"low_key", "cool_shadows", "restrained_red", "restrained_amber"}, {"high_key", "bright_day", "sunlit"}),
            ({"high_key", "bright_day", "sunlit"}, {"low_key", "cool_shadows"}),
        ),
        "era": (
            ({"1983", "cold_war", "analog", "crt", "period_compatible"}, {"modern", "digital", "smartphone", "bright_modern_ui"}),
            ({"modern", "digital", "smartphone", "bright_modern_ui"}, {"1983", "cold_war", "analog", "crt"}),
        ),
    }
    for dimension, pairs in conflict_pairs.items():
        exp = set(expected.get(dimension, []))
        got = set(actual.get(dimension, []))
        for left, right in pairs:
            if exp & left and got & right:
                conflicts.append({
                    "dimension": dimension,
                    "expected": ", ".join(sorted(exp & left)),
                    "actual": ", ".join(sorted(got & right)),
                    "reason": "hard temporal/visual-world conflict",
                })
    forbidden = profile.get("hard_forbidden", [])
    for dimension, values in actual.items():
        for actual_value in values:
            for forbidden_value in forbidden:
                if _term_matches(forbidden_value, actual_value):
                    conflicts.append({
                        "dimension": dimension,
                        "expected": "not-forbidden",
                        "actual": actual_value,
                        "reason": f"hard_forbidden:{forbidden_value}",
                    })
    return conflicts


def continuity_match_report(
    scene: dict[str, Any],
    candidate: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score a candidate against the scene's visual world."""
    if profile is None:
        return {
            "status": "PASS",
            "score": 1.0,
            "matched": {},
            "missing": {},
            "conflicts": [],
            "risk_flags": [],
            "profile_id": None,
            "source_tier": candidate.get("source_tier"),
        }
    normalized = normalize_profile(profile)
    expected = _scene_tags(scene, normalized)
    actual = _candidate_tags(candidate)
    matched: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    for dimension in CONTINUITY_DIMENSIONS:
        if not expected[dimension]:
            continue
        matched_values = _overlap(expected[dimension], actual[dimension])
        if matched_values:
            matched[dimension] = matched_values
        if not actual[dimension]:
            missing[dimension] = expected[dimension]
        elif not matched_values:
            missing[dimension] = expected[dimension]
    conflicts = _hard_conflicts(expected, actual, normalized)
    available_weight = sum(
        DIMENSION_WEIGHTS[dimension]
        for dimension in CONTINUITY_DIMENSIONS
        if expected[dimension]
    )
    matched_weight = sum(
        DIMENSION_WEIGHTS[dimension]
        for dimension in matched
    )
    score = round(matched_weight / available_weight, 4) if available_weight else 0.0
    source_tier = _term(candidate.get("source_tier"))
    tier_risk = (
        []
        if not source_tier or source_tier in normalized["allowed_source_tiers"]
        else [f"source_tier_not_allowed:{source_tier}"]
    )
    risk_flags = list(tier_risk)
    if missing:
        risk_flags.append("continuity_metadata_incomplete")
    if conflicts:
        risk_flags.append("hard_continuity_conflict")
    if conflicts:
        status = "BLOCKED"
    elif score >= 0.72 and not missing:
        status = "PASS"
    else:
        status = "REVIEW_REQUIRED"
    return {
        "status": status,
        "score": score,
        "matched": matched,
        "missing": missing,
        "conflicts": conflicts,
        "risk_flags": risk_flags,
        "profile_id": normalized["profile_id"],
        "source_tier": source_tier or None,
    }


def adjacency_report(
    previous: dict[str, Any],
    current: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the cut between two adjacent shots."""
    normalized = normalize_profile(profile)
    prev_asset = previous.get("asset") if isinstance(previous, dict) else None
    curr_asset = current.get("asset") if isinstance(current, dict) else None
    prev_asset = prev_asset if isinstance(prev_asset, dict) else previous
    curr_asset = curr_asset if isinstance(curr_asset, dict) else current
    prev_tags = _candidate_tags(prev_asset)
    curr_tags = _candidate_tags(curr_asset)
    prev_scene = previous.get("scene") if isinstance(previous, dict) else previous
    curr_scene = current.get("scene") if isinstance(current, dict) else current
    bridge = any(
        _term(value) in {"bridge", "bridge_shot", "transition"}
        for value in (
            _mapping(previous).get("continuity_mode"),
            _mapping(current).get("continuity_mode"),
            _mapping(prev_scene).get("continuity_mode"),
            _mapping(curr_scene).get("continuity_mode"),
        )
    )
    conflicts: list[dict[str, str]] = []
    for dimension in ("time_of_day", "lighting", "palette", "texture"):
        left = prev_tags.get(dimension, [])
        right = curr_tags.get(dimension, [])
        if not left or not right:
            continue
        if dimension == "time_of_day":
            if (
                any(_term_matches(value, "night") for value in left)
                and any(_term_matches(value, "daylight") for value in right)
            ) or (
                any(_term_matches(value, "daylight") for value in left)
                and any(_term_matches(value, "night") for value in right)
            ):
                conflicts.append({
                    "dimension": dimension,
                    "reason": "adjacent day/night flip without a declared bridge",
                })
        elif dimension in {"lighting", "palette"}:
            if (
                any(_term_matches(value, "low_key") for value in left)
                and any(_term_matches(value, "high_key") for value in right)
            ) or (
                any(_term_matches(value, "high_key") for value in left)
                and any(_term_matches(value, "low_key") for value in right)
            ):
                conflicts.append({
                    "dimension": dimension,
                    "reason": "adjacent lighting/palette jump",
                })
    if conflicts and bridge and normalized["transition_policy"]["allow_bridge_shots"]:
        status = "REVIEW_REQUIRED"
        reason = "declared bridge shot softens an otherwise abrupt transition"
    elif conflicts:
        status = "BLOCKED"
        reason = "adjacent shots break the declared visual world"
    else:
        status = "PASS"
        reason = "adjacent shots remain compatible"
    return {
        "status": status,
        "conflicts": conflicts,
        "bridge_declared": bridge,
        "reason": reason,
    }


def validate_sequence(
    sequence: list[dict[str, Any]],
    profile: dict[str, Any] | None,
    *,
    mode: str = "manifest",
) -> dict[str, Any]:
    """Return a report and enforce strictness at the caller's chosen stage."""
    if mode not in SEQUENCE_MODES:
        raise VisualContinuityError(f"Unsupported continuity sequence mode: {mode}")
    if not profile:
        return {
            "status": "NOT_CONFIGURED",
            "mode": mode,
            "profile_id": None,
            "scene_reports": [],
            "adjacency_reports": [],
            "blocking_reasons": [],
            "review_reasons": ["visual continuity profile is not configured"],
            "strict_preview_block": False,
        }
    normalized = normalize_profile(profile)
    scene_reports: list[dict[str, Any]] = []
    for item in sequence:
        item = item if isinstance(item, dict) else {}
        scene = item.get("scene") if isinstance(item.get("scene"), dict) else item
        asset = item.get("asset") if isinstance(item.get("asset"), dict) else item
        report = continuity_match_report(scene, asset, normalized)
        report["shot_id"] = str(item.get("shot_id") or scene.get("shot_id") or "")
        scene_reports.append(report)
    adjacency_reports: list[dict[str, Any]] = []
    for previous, current in zip(sequence, sequence[1:]):
        report = adjacency_report(previous, current, normalized)
        report["from_shot_id"] = str(previous.get("shot_id", ""))
        report["to_shot_id"] = str(current.get("shot_id", ""))
        adjacency_reports.append(report)

    hard_conflicts = sum(len(report.get("conflicts", [])) for report in scene_reports)
    hard_conflicts += sum(
        len(report.get("conflicts", []))
        for report in adjacency_reports
        if report.get("status") == "BLOCKED"
    )
    review_reasons: list[str] = []
    blocking_reasons: list[str] = []
    for report in scene_reports:
        if report["status"] == "REVIEW_REQUIRED":
            review_reasons.append(
                f"{report['shot_id'] or 'scene'} continuity metadata/fit requires review"
            )
        elif report["status"] == "BLOCKED":
            blocking_reasons.append(
                f"{report['shot_id'] or 'scene'} has a hard continuity conflict"
            )
    for report in adjacency_reports:
        if report["status"] == "REVIEW_REQUIRED":
            review_reasons.append(
                f"{report['from_shot_id']}->{report['to_shot_id']} uses a declared bridge"
            )
        elif report["status"] == "BLOCKED":
            blocking_reasons.append(
                f"{report['from_shot_id']}->{report['to_shot_id']} breaks adjacency continuity"
            )

    enforcement = normalized["enforcement"].get(mode, "block")
    if hard_conflicts and enforcement == "block":
        status = "BLOCKED"
    elif blocking_reasons and mode in {"preview", "final"}:
        status = "BLOCKED"
    elif review_reasons or hard_conflicts:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"
    return {
        "status": status,
        "mode": mode,
        "profile_id": normalized["profile_id"],
        "scene_reports": scene_reports,
        "adjacency_reports": adjacency_reports,
        "blocking_reasons": blocking_reasons,
        "review_reasons": review_reasons,
        "hard_conflict_count": hard_conflicts,
        "coverage_score": round(
            sum(float(report.get("score", 0.0)) for report in scene_reports)
            / len(scene_reports),
            4,
        ) if scene_reports else 0.0,
        "strict_preview_block": normalized["enforcement"].get("preview") == "block",
        "source_tiers": normalized["allowed_source_tiers"],
    }
