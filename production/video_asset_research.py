#!/usr/bin/env python3
"""Create review queues for approved-stock video discovery.

The queue is intentionally video-only and fail-closed. It asks for one
distinct clip per narrative beat, ranks exact matches above semantic fallbacks,
and records the reason a near match may be considered.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

from production.editorial_policy import clip_quantity_policy, clip_quantity_report

PROVIDER_ORDER = ("mixkit", "pixabay", "pexels")
FALLBACK_LADDER = ("EXACT", "NEAR", "EXPLANATORY", "SYMBOLIC", "ATMOSPHERE")
_STOP_WORDS = {
    "a", "an", "and", "at", "behind", "by", "for", "from", "in", "into", "is",
    "of", "on", "or", "show", "shows", "that", "the", "this", "to", "with",
    "visual", "scene", "video",
}


class ResearchError(ValueError):
    pass


def _tokens(value: Any) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", str(value).lower()) if word not in _STOP_WORDS]


def query_for_scene(scene: dict[str, Any]) -> str:
    """Build a search query from action, emotion and narrative function."""
    values = [
        scene.get("story_beat", ""),
        scene.get("visual_intent", ""),
        scene.get("visual_function", ""),
        scene.get("shot_role", ""),
        scene.get("emotion", ""),
        scene.get("visual_symbol", ""),
    ]
    unique: list[str] = []
    for word in _tokens(" ".join(str(value) for value in values)):
        if word not in unique:
            unique.append(word)
    if not unique:
        raise ResearchError(f"Scene {scene.get('scene_id', '?')} lacks story language for search.")
    return " ".join(unique[:14])


def _candidate_text(candidate: dict[str, Any]) -> str:
    keys = (
        "title", "description", "tags", "category", "mood", "motion",
        "composition", "visual_function", "emotion",
    )
    return " ".join(str(candidate.get(key, "")) for key in keys)


def _fallback_tier(candidate: dict[str, Any], scene: dict[str, Any]) -> str:
    declared = str(candidate.get("visual_match", "")).upper()
    if declared in FALLBACK_LADDER:
        return declared
    overlap = set(_tokens(query_for_scene(scene))) & set(_tokens(_candidate_text(candidate)))
    if len(overlap) >= 4:
        return "EXACT"
    if len(overlap) >= 2:
        return "NEAR"
    if candidate.get("visual_function") == scene.get("visual_function"):
        return "EXPLANATORY"
    if candidate.get("mood") or candidate.get("emotion"):
        return "SYMBOLIC"
    return "ATMOSPHERE"


def score_candidate(candidate: dict[str, Any], scene: dict[str, Any]) -> float:
    query = set(_tokens(query_for_scene(scene)))
    searchable = set(_tokens(_candidate_text(candidate)))
    overlap = len(query & searchable) / max(len(query), 1)

    duration = float(candidate.get("duration_seconds", 0) or 0)
    target = float(scene.get("duration", 1) or 1)
    duration_fit = min(duration / target, target / duration) if duration > 0 else 0.0

    width = int(candidate.get("width", 0) or 0)
    height = int(candidate.get("height", 0) or 0)
    orientation = 1.0 if height >= width and height > 0 else 0.45

    scene_function = str(scene.get("visual_function", "")).lower()
    function_fit = 1.0 if scene_function and scene_function in _candidate_text(candidate).lower() else 0.0
    provider = 0.90 if candidate.get("provider") == "mixkit" else 0.75 if candidate.get("provider") == "pixabay" else 0.70
    rights = 1.0 if candidate.get("license") or candidate.get("rights_status") == "APPROVED" else 0.0

    return round(min(1.0, 0.45 * overlap + 0.15 * duration_fit + 0.10 * orientation + 0.10 * function_fit + 0.10 * provider + 0.10 * rights), 4)


def _candidate_key(candidate: dict[str, Any]) -> str:
    for key in ("asset_id", "download_url", "source_page_url", "id", "title"):
        value = str(candidate.get(key, "")).strip().lower()
        if value:
            return value
    return json.dumps(candidate, sort_keys=True, ensure_ascii=False)


def _prepare_candidate(candidate: dict[str, Any], provider: str, scene: dict[str, Any]) -> dict[str, Any]:
    prepared = {
        **candidate,
        "provider": provider,
        "approved_for_render": False,
        "rights_status": "REVIEW_REQUIRED",
        "fallback_tier": _fallback_tier(candidate, scene),
    }
    prepared["relevance_score"] = score_candidate(prepared, scene)
    return prepared


def build_queue(
    manifest: dict[str, Any],
    searchers: dict[str, Callable[[str, int], list[dict[str, Any]]]] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    searchers = searchers or {}
    try:
        policy = clip_quantity_policy(manifest)
    except ValueError as exc:
        raise ResearchError(str(exc)) from exc

    results = []
    for scene in manifest.get("scenes", []):
        query = query_for_scene(scene)
        candidates = []
        errors = []
        unique_keys: set[str] = set()
        for provider in PROVIDER_ORDER:
            searcher = searchers.get(provider)
            if not searcher:
                continue
            try:
                for raw in searcher(query, limit):
                    candidate = _prepare_candidate(raw, provider, scene)
                    key = _candidate_key(candidate)
                    if key in unique_keys:
                        continue
                    unique_keys.add(key)
                    candidates.append(candidate)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        candidates.sort(key=lambda item: (item["relevance_score"], item["fallback_tier"] == "EXACT"), reverse=True)
        results.append({
            "scene_id": scene.get("scene_id"),
            "query": query,
            "approval_status": "REVIEW_REQUIRED",
            "fallback_ladder": list(FALLBACK_LADDER),
            "candidates": candidates[: max(1, limit) * len(PROVIDER_ORDER)],
            "provider_errors": errors,
            "image_fallback": "FORBIDDEN",
            "selection_rule": "one fresh source clip per narrative beat; never repeat source, hash or animation fingerprint",
        })

    quantity = clip_quantity_report(len(results), policy)
    return {
        "schema_version": "2.0",
        "video_id": manifest.get("video_id"),
        "research_type": "approved_video_asset_queue",
        "providers": list(PROVIDER_ORDER),
        "scenes": results,
        "clip_quantity_policy": policy,
        "clip_quantity_gate": quantity,
        "selection_rules": {
            "target_unique_clips": [policy["target_min"], policy["target_max"]],
            "minimum_unique_clips": policy["min_clips"],
            "maximum_unique_clips": policy["max_clips"],
            "no_repeat_animation": True,
            "image_fallback": "FORBIDDEN",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("video-asset-review-queue.json"))
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = build_queue(manifest)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "VIDEO_ASSET_QUEUE_CREATED",
            "video_id": result.get("video_id"),
            "scenes": len(result["scenes"]),
            "clip_quantity_gate": result["clip_quantity_gate"],
            "image_fallback": "FORBIDDEN",
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"VIDEO ASSET RESEARCH BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
