#!/usr/bin/env python3
"""Create review queues for approved-stock video discovery.

This module never auto-approves a clip and never falls back to a still image.
It records the semantic fallback ladder so a reviewer can tell why a near
match was accepted.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

PROVIDER_ORDER = ("mixkit", "pixabay", "pexels")
FALLBACK_LADDER = ("EXACT", "NEAR", "EXPLANATORY", "SYMBOLIC", "ATMOSPHERE")


class ResearchError(ValueError):
    pass


def query_for_scene(scene: dict[str, Any]) -> str:
    values = [scene.get("story_beat", ""), scene.get("visual_intent", ""), scene.get("visual_symbol", "")]
    words = re.findall(r"[a-z0-9]+", " ".join(str(value).lower() for value in values))
    stop = {"the", "and", "with", "that", "this", "from", "into", "show", "shows", "visual"}
    unique: list[str] = []
    for word in words:
        if word not in stop and word not in unique:
            unique.append(word)
    if not unique:
        raise ResearchError(f"Scene {scene.get('scene_id', '?')} lacks story language for search.")
    return " ".join(unique[:10])


def score_candidate(candidate: dict[str, Any], scene: dict[str, Any]) -> float:
    query = set(query_for_scene(scene).split())
    searchable = set(re.findall(r"[a-z0-9]+", " ".join(str(candidate.get(key, "")).lower() for key in ("title", "description", "tags"))))
    overlap = len(query & searchable) / max(len(query), 1)
    duration = float(candidate.get("duration_seconds", 0) or 0)
    target = float(scene.get("duration", 1) or 1)
    duration_fit = min(duration / target, target / duration) if duration > 0 else 0
    width, height = int(candidate.get("width", 0) or 0), int(candidate.get("height", 0) or 0)
    vertical = 1.0 if height >= width and height > 0 else 0.45
    provider = 0.9 if candidate.get("provider") == "mixkit" else 0.75 if candidate.get("provider") == "pixabay" else 0.7
    return round(min(1.0, 0.55 * overlap + 0.2 * duration_fit + 0.1 * vertical + 0.15 * provider), 4)


def build_queue(manifest: dict[str, Any], searchers: dict[str, Callable[[str, int], list[dict[str, Any]]]] | None = None, limit: int = 8) -> dict[str, Any]:
    searchers = searchers or {}
    results = []
    for scene in manifest.get("scenes", []):
        query = query_for_scene(scene)
        candidates = []
        errors = []
        for provider in PROVIDER_ORDER:
            searcher = searchers.get(provider)
            if not searcher:
                continue
            try:
                for candidate in searcher(query, limit):
                    candidate = {**candidate, "provider": provider, "approved_for_render": False, "rights_status": "REVIEW_REQUIRED"}
                    candidate["relevance_score"] = score_candidate(candidate, scene)
                    candidates.append(candidate)
            except Exception as exc:  # provider outages must not approve anything
                errors.append(f"{provider}: {exc}")
        candidates.sort(key=lambda item: item["relevance_score"], reverse=True)
        results.append({
            "scene_id": scene.get("scene_id"),
            "query": query,
            "approval_status": "REVIEW_REQUIRED",
            "fallback_ladder": list(FALLBACK_LADDER),
            "candidates": candidates[: max(1, limit) * len(PROVIDER_ORDER)],
            "provider_errors": errors,
            "image_fallback": "FORBIDDEN",
        })
    return {"schema_version": "2.0", "video_id": manifest.get("video_id"), "research_type": "approved_video_asset_queue", "providers": list(PROVIDER_ORDER), "scenes": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("video-asset-review-queue.json"))
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = build_queue(manifest)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "VIDEO_ASSET_QUEUE_CREATED", "video_id": result.get("video_id"), "scenes": len(result["scenes"]), "image_fallback": "FORBIDDEN"}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"VIDEO ASSET RESEARCH BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


