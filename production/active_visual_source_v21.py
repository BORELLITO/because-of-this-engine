"""Canonical V2.1 visual-source gate.

The active engine consumes one episode visual manifest. Historical acquisition
plans and retired engine files remain evidence/rollback material only; they
cannot silently become a runtime clip source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CANONICAL_ENGINE_VERSION = "2.1"
EPISODE005 = "episode-005"
EPISODE005_MANIFEST = "episodes/episode-005/visual/scene-asset-manifest.json"
EPISODE005_SHOT_COUNT = 16
EPISODE005_FORBIDDEN_PROVIDERS = ("nasa",)
EPISODE005_NO_CLOCK_TERMS = (
    "clock",
    "alarm clock",
    "timepiece",
    "clock mechanism",
)

_LEGACY_RUNTIME_MARKERS = (
    "production/v7_orchestrator.py",
    "production/v7_contract.py",
    "production/render_video_episode.py",
    "production/pipeline_state.py",
)


def _normalized(value: Any) -> str:
    return re.sub(r"[_-]+", " ", str(value or "").lower())


def forbidden_concept_hits(record: dict[str, Any], terms: list[str] | tuple[str, ...]) -> list[str]:
    """Return explicit editorial exclusions found in a candidate record."""
    fields = (
        "candidate_id",
        "asset_id",
        "title",
        "description",
        "role",
        "visual_match",
        "visual_intent",
        "visual_request",
        "source_page_url",
        "media_url",
    )
    text = _normalized(" ".join(str(record.get(field, "")) for field in fields))
    hits: list[str] = []
    for term in terms:
        normalized = _normalized(term).strip()
        if not normalized:
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
        if re.search(pattern, text):
            hits.append(str(term))
    return sorted(set(hits))


def _manifest_path_value(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def validate_scene_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path,
    *,
    expected_episode_id: str = EPISODE005,
) -> dict[str, Any]:
    """Validate the active runtime source without downloading or rendering."""
    failures: list[str] = []
    episode_id = str(manifest.get("episode_id") or "").strip()
    expected_path = (
        EPISODE005_MANIFEST if expected_episode_id == EPISODE005
        else f"episodes/{expected_episode_id}/visual/scene-asset-manifest.json"
    )
    actual_path = _manifest_path_value(manifest_path)
    if episode_id != expected_episode_id:
        failures.append(f"manifest episode_id must be {expected_episode_id}")
    if actual_path != expected_path:
        failures.append(
            f"runtime visual source must be {expected_path}, got {actual_path or '<missing>'}"
        )
    if manifest.get("runtime_source_of_truth") != expected_path:
        failures.append("manifest runtime_source_of_truth is not the canonical scene manifest")
    if manifest.get("canonical_engine_version") != CANONICAL_ENGINE_VERSION:
        failures.append("manifest is not locked to canonical V2.1")

    profile = manifest.get("visual_continuity_profile")
    profile = profile if isinstance(profile, dict) else {}
    forbidden = profile.get("hard_forbidden")
    forbidden = [str(item) for item in forbidden] if isinstance(forbidden, list) else []
    normalized_forbidden = {_normalized(item).strip() for item in forbidden}
    if expected_episode_id == EPISODE005:
        missing = [
            term for term in EPISODE005_NO_CLOCK_TERMS
            if _normalized(term) not in normalized_forbidden
        ]
        if missing:
            failures.append("Episode 005 no-clock editorial lock is incomplete: " + ", ".join(missing))

    assets = manifest.get("assets")
    assets = assets if isinstance(assets, list) else []
    asset_hits: dict[str, list[str]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            failures.append("active manifest contains a non-object asset")
            continue
        candidate_id = str(asset.get("candidate_id") or "<missing>")
        provider = str(asset.get("provider") or "").strip().lower()
        source_urls = " ".join(
            str(asset.get(field) or "").lower()
            for field in ("source_page_url", "media_url")
        )
        if expected_episode_id == EPISODE005 and (
            provider in EPISODE005_FORBIDDEN_PROVIDERS
            or "nasa.gov" in source_urls
            or "svs.gsfc.nasa.gov" in source_urls
        ):
            failures.append(
                f"Episode 005 active visual source uses a forbidden provider: {candidate_id}"
            )
        hits = forbidden_concept_hits(asset, forbidden)
        if hits:
            asset_hits[candidate_id] = hits
    if asset_hits:
        failures.append("active manifest contains forbidden concepts: " + json.dumps(asset_hits, sort_keys=True))

    assignments = manifest.get("shot_assignments")
    assignments = assignments if isinstance(assignments, list) else []
    assigned_shots: dict[str, str] = {}
    for item in assignments:
        if not isinstance(item, dict):
            failures.append("active manifest contains a non-object shot assignment")
            continue
        shot_id = str(item.get("shot_id") or "").strip()
        assignment = item.get("assignment")
        if isinstance(assignment, dict) and str(assignment.get("candidate_id") or "").strip():
            assigned_shots[shot_id] = str(assignment["candidate_id"]).strip()

    unresolved = {
        str(item).strip()
        for item in (manifest.get("unresolved_shots") or [])
        if str(item).strip()
    }
    if unresolved:
        failures.append("active visual manifest has unresolved shots: " + ", ".join(sorted(unresolved)))
    if expected_episode_id == EPISODE005:
        if len(assets) != EPISODE005_SHOT_COUNT:
            failures.append(
                f"Episode 005 active manifest requires {EPISODE005_SHOT_COUNT} assets, got {len(assets)}"
            )
        if len(assigned_shots) != EPISODE005_SHOT_COUNT:
            failures.append(
                f"Episode 005 active runtime requires {EPISODE005_SHOT_COUNT} assigned shots, got {len(assigned_shots)}"
            )
        if len(set(assigned_shots.values())) != len(assigned_shots):
            failures.append("active runtime cannot reuse a visual source within Episode 005")

    for marker in _LEGACY_RUNTIME_MARKERS:
        if marker in str(manifest.get("runtime_source_of_truth", "")):
            failures.append(f"legacy runtime marker in visual source: {marker}")

    return {
        "gate": "ACTIVE_V21_VISUAL_SOURCE",
        "status": "PASS" if not failures else "BLOCKED",
        "failures": failures,
        "engine_version": CANONICAL_ENGINE_VERSION,
        "source_of_truth": expected_path,
        "asset_count": len(assets),
        "assigned_shot_count": len(assigned_shots),
        "unresolved_shots": sorted(unresolved),
        "forbidden_concept_hits": asset_hits,
        "render": "NOT_RUN",
        "publication": "NOT_RUN",
    }


def validate_record_visual_source(record: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Load and validate the record's one canonical visual manifest."""
    episode_id = str(record.get("episode_id") or "").strip()
    manifest_reference = str(record.get("visual_manifest_reference") or "").strip()
    expected = (
        EPISODE005_MANIFEST if episode_id == EPISODE005
        else f"episodes/{episode_id}/visual/scene-asset-manifest.json"
    )
    if manifest_reference != expected:
        return {
            "gate": "ACTIVE_V21_VISUAL_SOURCE",
            "status": "BLOCKED",
            "failures": [f"record visual_manifest_reference must be {expected}"],
            "engine_version": CANONICAL_ENGINE_VERSION,
            "source_of_truth": expected,
            "render": "NOT_RUN",
            "publication": "NOT_RUN",
        }
    path = (repo_root / manifest_reference).resolve()
    try:
        path.relative_to(repo_root.resolve())
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "gate": "ACTIVE_V21_VISUAL_SOURCE",
            "status": "BLOCKED",
            "failures": [f"canonical visual manifest unavailable: {exc}"],
            "engine_version": CANONICAL_ENGINE_VERSION,
            "source_of_truth": expected,
            "render": "NOT_RUN",
            "publication": "NOT_RUN",
        }
    if not isinstance(manifest, dict):
        return {
            "gate": "ACTIVE_V21_VISUAL_SOURCE",
            "status": "BLOCKED",
            "failures": ["canonical visual manifest must be an object"],
            "engine_version": CANONICAL_ENGINE_VERSION,
            "source_of_truth": expected,
            "render": "NOT_RUN",
            "publication": "NOT_RUN",
        }
    return validate_scene_manifest(manifest, manifest_reference, expected_episode_id=episode_id)


__all__ = [
    "EPISODE005_MANIFEST",
    "EPISODE005_FORBIDDEN_PROVIDERS",
    "EPISODE005_NO_CLOCK_TERMS",
    "forbidden_concept_hits",
    "validate_record_visual_source",
    "validate_scene_manifest",
]
