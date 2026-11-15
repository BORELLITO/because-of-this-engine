"""V3 visual lock: direct photorealistic event representation only.

This gate is intentionally stricter than the historical V2.1 intake checks.
It does not replace clips or regenerate previews; it blocks render promotion
when a manifest still relies on diagrams, graphics or abstract filler.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

FORBIDDEN_TRUTH_CLASSES = {"MAP_OR_DIAGRAM", "ABSTRACT_ATMOSPHERE"}
FORBIDDEN_TERMS = (
    "diagram",
    "infographic",
    "hud",
    "graphic overlay",
    "graphic",
    "map",
    "timepiece",
    "clock mechanism",
    "alarm clock",
)
ALLOWED_ABSTRACT_ROLES = {"BRAND_OUTRO"}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    return ""


def audit_visual_manifest(manifest: dict[str, Any], record: dict[str, Any] | None = None) -> dict[str, Any]:
    failures: list[str] = []
    assets = manifest.get("assets") if isinstance(manifest.get("assets"), list) else []
    for asset in assets:
        asset_id = str(asset.get("candidate_id") or "<unknown>")
        truth_class = str(asset.get("truth_class") or "").upper()
        role = str(asset.get("source_role") or "").upper()
        if truth_class in FORBIDDEN_TRUTH_CLASSES and role not in ALLOWED_ABSTRACT_ROLES:
            failures.append(f"asset {asset_id} uses forbidden truth_class={truth_class}")
        hits = [term for term in FORBIDDEN_TERMS if term in _text(asset)]
        if hits:
            failures.append(f"asset {asset_id} contains forbidden visual terms: {', '.join(sorted(set(hits)))}")

    assignments = manifest.get("shot_assignments") if isinstance(manifest.get("shot_assignments"), list) else []
    for shot in assignments:
        shot_id = str(shot.get("shot_id") or "<unknown>")
        requested_class = str(shot.get("requested_truth_class") or "").upper()
        requested_visual = _text(shot.get("requested_visual"))
        if requested_class in FORBIDDEN_TRUTH_CLASSES:
            failures.append(f"shot {shot_id} requests forbidden truth_class={requested_class}")
        hits = [term for term in FORBIDDEN_TERMS if term in requested_visual]
        if hits:
            failures.append(f"shot {shot_id} requests forbidden concepts: {', '.join(sorted(set(hits)))}")

    if record:
        for field in ("visual_truth_classes", "visual_representation_by_stage"):
            hits = [term for term in FORBIDDEN_TERMS if term in _text(record.get(field))]
            if hits:
                failures.append(f"production record {field} contains forbidden concepts: {', '.join(sorted(set(hits)))}")
        classes = {str(item).upper() for item in record.get("visual_truth_classes", []) if isinstance(item, str)}
        if classes & FORBIDDEN_TRUTH_CLASSES:
            failures.append(
                "production record visual_truth_classes contains: "
                + ", ".join(sorted(classes & FORBIDDEN_TRUTH_CLASSES))
            )

    return {
        "status": "V3_VISUAL_POLICY_PASS" if not failures else "V3_VISUAL_POLICY_BLOCKED",
        "failures": failures,
        "asset_count": len(assets),
        "shot_count": len(assignments),
        "rule": "DIRECT_PHOTOREALISTIC_EVENT_REPRESENTATION_ONLY",
    }


def audit_episode(repo_root: Path, record: dict[str, Any]) -> dict[str, Any]:
    reference = str(record.get("visual_manifest_reference") or "episodes/episode-005/visual/scene-asset-manifest.json")
    path = repo_root / reference
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "status": "V3_VISUAL_POLICY_BLOCKED",
            "failures": [f"cannot load visual manifest {reference}: {exc}"],
            "asset_count": 0,
            "shot_count": 0,
            "rule": "DIRECT_PHOTOREALISTIC_EVENT_REPRESENTATION_ONLY",
        }
    if not isinstance(manifest, dict):
        return {
            "status": "V3_VISUAL_POLICY_BLOCKED",
            "failures": ["visual manifest must be a JSON object"],
            "asset_count": 0,
            "shot_count": 0,
            "rule": "DIRECT_PHOTOREALISTIC_EVENT_REPRESENTATION_ONLY",
        }
    return audit_visual_manifest(manifest, record)


__all__ = ["audit_episode", "audit_visual_manifest", "FORBIDDEN_TERMS", "FORBIDDEN_TRUTH_CLASSES"]
