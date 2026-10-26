#!/usr/bin/env python3
"""Create review queues for semantically approved stock-video discovery.

The queue is video-only and fail-closed.  Search phrases are generated from
the scene's narrative excerpt and visual contract, while candidate ranking uses
subject/action/environment/object evidence rather than isolated keyword overlap.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

from production.asset_reuse_brain import REGISTRY_SCHEMA_VERSION, source_asset_key
from production.editorial_policy import clip_quantity_policy, clip_quantity_report
from production.visual_semantics import (
    DIMENSIONS,
    evidence_text,
    visual_match_report,
)

PROVIDER_ORDER = ("mixkit", "pixabay", "pexels")
FALLBACK_LADDER = ("EXACT", "NEAR", "EXPLANATORY", "SYMBOLIC", "ATMOSPHERE")
_STOP_WORDS = {
    "a", "an", "and", "at", "behind", "by", "for", "from", "in", "into", "is",
    "of", "on", "or", "show", "shows", "that", "the", "this", "to", "with",
    "visual", "scene", "video", "no", "not",
}


class ResearchError(ValueError):
    pass


def _load_asset_memory(registry_path: Path | None) -> dict[str, Any]:
    if registry_path is None:
        return {
            "status": "NOT_CONFIGURED",
            "registry_path": None,
            "retired_source_keys": set(),
        }
    path = registry_path.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchError(f"Asset memory registry is unavailable: {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ResearchError("Asset memory registry has an unsupported schema.")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ResearchError("Asset memory registry assets must be a list.")
    retired_source_keys: set[str] = set()
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise ResearchError(f"Asset memory registry record {index} is invalid.")
        key = str(asset.get("source_asset_key") or "").strip().lower()
        if not key:
            raise ResearchError(f"Asset memory registry record {index} has no source_asset_key.")
        retired_source_keys.add(key)
    return {
        "status": "READY",
        "registry_path": str(path),
        "retired_source_keys": retired_source_keys,
    }


def _tokens(value: Any) -> list[str]:
    return [
        word for word in re.findall(r"[a-z0-9:]+", str(value).lower())
        if word not in _STOP_WORDS
    ]


def _semantic_terms(scene: dict[str, Any]) -> list[str]:
    spec = scene.get("visual_semantics") or {}
    terms: list[str] = []
    if isinstance(spec, dict):
        for group in ("required", "preferred"):
            values = spec.get(group) or {}
            if isinstance(values, dict):
                for dimension in DIMENSIONS:
                    for value in values.get(dimension, []) or []:
                        terms.extend(_tokens(value))
    return terms


def _narrative_search_terms(excerpt: Any) -> tuple[list[str], set[str]]:
    """Translate explicit negation into positive stock-search intent.

    Search engines often treat "no person" as a request for a person. We
    therefore remove negated subjects from the positive token stream and add
    auditable visual qualifiers such as "empty" and "unoccupied". The
    semantic gate remains authoritative after retrieval.
    """
    text = str(excerpt or "").lower()
    negative_terms: list[str] = []
    excluded: set[str] = set()

    if re.search(r"\bno\s+(person|people|one|figure)\b", text):
        negative_terms.extend(["empty", "unoccupied", "without people"])
        excluded.update({"person", "people", "one", "figure"})
    if re.search(r"\bno\s+(footprints?|tracks?)\b", text):
        negative_terms.extend(["clean floor", "empty hallway"])
        excluded.update({"footprint", "footprints", "tracks"})
    if re.search(r"\bno\s+broken\s+lock\b", text):
        negative_terms.extend(["intact lock", "closed door"])
        excluded.update({"broken", "lock"})
    if re.search(r"\bno\s+longer\b", text):
        negative_terms.extend(["empty", "unoccupied"])

    return negative_terms, excluded


def query_variants_for_scene(scene: dict[str, Any]) -> list[str]:
    """Build focused queries while preserving the complete narrative beat."""
    excerpt = scene.get("narration_excerpt", "")
    spec = scene.get("visual_semantics") or {}
    required: list[str] = []
    if isinstance(spec, dict):
        groups = spec.get("required") or {}
        if isinstance(groups, dict):
            for dimension in ("subjects", "actions", "environments", "objects"):
                required.extend(str(item) for item in groups.get(dimension, []) or [])
    if not required:
        required.extend(_tokens(scene.get("story_beat", "")))
        required.extend(_tokens(scene.get("visual_intent", "")))

    negative_terms, excluded = _narrative_search_terms(excerpt)
    unique: list[str] = []

    def add_terms(items: list[str]) -> None:
        for value in items:
            for word in _tokens(value):
                if word not in excluded and word not in unique:
                    unique.append(word)

    add_terms(negative_terms)
    add_terms(required)
    add_terms(_semantic_terms(scene))
    add_terms(_tokens(excerpt))

    if not unique:
        raise ResearchError(f"Scene {scene.get('scene_id', '?')} lacks narrative visual language.")

    primary = " ".join(unique[:12])
    variants = [primary]
    if len(unique) >= 5:
        variants.append(" ".join(unique[:6]))
    if excerpt:
        excerpt_tokens = [word for word in _tokens(excerpt) if word not in excluded]
        excerpt_query = " ".join(excerpt_tokens[:10])
        if excerpt_query and excerpt_query not in variants:
            variants.append(excerpt_query)
    return variants[:3]


def query_for_scene(scene: dict[str, Any]) -> str:
    return query_variants_for_scene(scene)[0]


def _candidate_text(candidate: dict[str, Any]) -> str:
    return evidence_text(candidate)


def _fallback_tier(candidate: dict[str, Any], scene: dict[str, Any]) -> str:
    declared = str(candidate.get("visual_match", "")).upper()
    if declared in FALLBACK_LADDER:
        return declared
    guard = visual_match_report(scene, candidate)
    score = float(guard.get("score", 0.0))
    if score >= 0.80:
        return "EXACT"
    if score >= 0.66:
        return "NEAR"
    if score >= 0.50:
        return "EXPLANATORY"
    if score >= 0.34:
        return "SYMBOLIC"
    return "ATMOSPHERE"


def score_candidate(candidate: dict[str, Any], scene: dict[str, Any]) -> float:
    guard = visual_match_report(scene, candidate, require_review=False)
    if guard.get("status") == "BLOCKED":
        return 0.0

    semantic = float(guard.get("score", 0.0))
    duration = float(candidate.get("duration_seconds", 0) or 0)
    target = float(scene.get("duration", 1) or 1)
    duration_fit = min(duration / target, target / duration) if duration > 0 else 0.0

    width = int(candidate.get("width", 0) or 0)
    height = int(candidate.get("height", 0) or 0)
    orientation = 1.0 if height >= width and height > 0 else 0.45
    provider = 0.90 if candidate.get("provider") == "mixkit" else 0.75 if candidate.get("provider") == "pixabay" else 0.70
    rights = 1.0 if candidate.get("license") or candidate.get("rights_status") == "APPROVED" else 0.0

    # Semantic fit dominates.  Duration, vertical suitability and rights are
    # tie-breakers, never substitutes for narrative relevance.
    return round(min(1.0, 0.68 * semantic + 0.12 * duration_fit + 0.08 * orientation + 0.06 * provider + 0.06 * rights), 4)


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
    guard = visual_match_report(scene, prepared, require_review=False)
    prepared["visual_guard"] = guard
    prepared["relevance_score"] = score_candidate(prepared, scene)
    prepared["selection_status"] = "REVIEW_REQUIRED" if guard.get("status") == "PASS" else "REJECTED_SEMANTIC_MISMATCH"
    return prepared


def build_queue(
    manifest: dict[str, Any],
    searchers: dict[str, Callable[[str, int], list[dict[str, Any]]]] | None = None,
    limit: int = 8,
    *,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    searchers = searchers or {}
    try:
        policy = clip_quantity_policy(manifest)
        asset_memory = _load_asset_memory(registry_path)
    except ValueError as exc:
        raise ResearchError(str(exc)) from exc

    results = []
    for scene in manifest.get("scenes", []):
        variants = query_variants_for_scene(scene)
        candidates = []
        rejected = []
        errors = []
        unique_keys: set[str] = set()
        for provider in PROVIDER_ORDER:
            searcher = searchers.get(provider)
            if not searcher:
                continue
            try:
                for query in variants:
                    for raw in searcher(query, limit):
                        candidate = _prepare_candidate(raw, provider, scene)
                        key = _candidate_key(candidate)
                        if key in unique_keys:
                            continue
                        unique_keys.add(key)
                        source_key = source_asset_key(candidate)
                        if not source_key:
                            candidate["selection_status"] = "REJECTED_MISSING_SOURCE_IDENTITY"
                            candidate["global_memory_check"] = "BLOCKED"
                            candidate["rejection_reason"] = "provider source identity is required before visual approval"
                            rejected.append(candidate)
                        elif source_key in asset_memory["retired_source_keys"]:
                            candidate["selection_status"] = "REJECTED_GLOBAL_REUSE"
                            candidate["global_memory_check"] = "BLOCKED"
                            candidate["source_asset_key"] = source_key
                            candidate["rejection_reason"] = "source asset is already retired in the global memory registry"
                            rejected.append(candidate)
                        elif candidate["selection_status"] == "REJECTED_SEMANTIC_MISMATCH":
                            candidate["global_memory_check"] = "PASS"
                            candidates.append(candidate)
                        else:
                            candidate["global_memory_check"] = "PASS"
                            candidate["source_asset_key"] = source_key
                            candidates.append(candidate)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        candidates.sort(key=lambda item: item["relevance_score"], reverse=True)
        rejected.sort(key=lambda item: item["visual_guard"].get("score", 0.0), reverse=True)
        results.append({
            "scene_id": scene.get("scene_id"),
            "narration_excerpt": scene.get("narration_excerpt"),
            "query": variants[0],
            "query_variants": variants,
            "approval_status": "REVIEW_REQUIRED",
            "fallback_ladder": list(FALLBACK_LADDER),
            "candidates": candidates[: max(1, limit) * len(PROVIDER_ORDER)],
            "rejected_candidates": rejected[: max(1, limit)],
            "provider_errors": errors,
            "asset_memory": {
                "status": asset_memory["status"],
                "registry_path": asset_memory["registry_path"],
                "retired_source_count": len(asset_memory["retired_source_keys"]),
            },
            "image_fallback": "FORBIDDEN",
            "selection_rule": (
                "match the complete narrative beat using subject, action, environment "
                "and object evidence; reject forbidden or context-free filler"
            ),
        })

    quantity = clip_quantity_report(len(results), policy)
    return {
        "schema_version": "2.1",
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
            "keyword_only_matching": False,
            "semantic_dimensions": ["subjects", "actions", "environments", "objects", "moods", "composition"],
            "forbidden_concepts_block": True,
            "global_no_repeat_source_asset": True,
            "asset_memory_required_for_release": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("video-asset-review-queue.json"))
    parser.add_argument("--asset-registry", type=Path, default=None)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = build_queue(manifest, registry_path=args.asset_registry)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "VIDEO_ASSET_QUEUE_CREATED",
            "video_id": result.get("video_id"),
            "scenes": len(result["scenes"]),
            "clip_quantity_gate": result["clip_quantity_gate"],
            "image_fallback": "FORBIDDEN",
            "keyword_only_matching": False,
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"VIDEO ASSET RESEARCH BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
