#!/usr/bin/env python3
"""Research illustrative stock-video candidates for Because of This.

This module is deliberately a research layer, not an auto-publisher. It searches
approved public providers, ranks candidates against a scene beat, and writes a
provenance/rights record. Every candidate remains REVIEW_REQUIRED until a human
approves the exact source page and license.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = "1.0"
PEXELS_SEARCH = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH = "https://pixabay.com/api/videos/"
PROVIDER_ORDER = ("pixabay", "pexels")

_STOPWORDS = {
    "a", "an", "and", "as", "at", "before", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "two", "with", "um", "uma", "e", "de",
    "da", "do", "das", "dos", "em", "para", "por", "que", "se", "no", "na",
    "nos", "nas", "ao", "aos", "com", "um", "uma", "this", "that",
}


class ResearchError(ValueError):
    """Raised when the research contract cannot be satisfied."""


@dataclass(frozen=True)
class SceneQuery:
    scene_id: str
    query: str
    duration: float
    visual_function: str
    visual_intent: str


def _tokens(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    words = re.findall(r"[a-z0-9]+", value.lower())
    return {word for word in words if len(word) > 2 and word not in _STOPWORDS}


def _scene_query(scene: dict[str, Any], override: str | None = None) -> SceneQuery:
    scene_id = str(scene.get("scene_id") or "").strip()
    if not scene_id:
        raise ResearchError("Each scene requires a non-empty scene_id.")
    duration = scene.get("duration")
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ResearchError(f"Scene {scene_id} requires a positive duration.")
    if override and override.strip():
        query = override.strip()
    else:
        raw_keywords = scene.get("search_keywords", [])
        keyword_text = " ".join(str(value) for value in raw_keywords) if isinstance(raw_keywords, list) else str(raw_keywords)
        pieces = [
            keyword_text,
            scene.get("story_beat", ""),
            scene.get("visual_intent", ""),
            scene.get("image_type", ""),
            scene.get("visual_function", ""),
        ]
        ordered: list[str] = []
        seen: set[str] = set()
        for piece in pieces:
            for token in re.findall(r"[A-Za-z0-9]+", str(piece).lower()):
                if len(token) > 2 and token not in _STOPWORDS and token not in seen:
                    seen.add(token)
                    ordered.append(token)
        query = " ".join(ordered[:10])
    if not query:
        raise ResearchError(f"Scene {scene_id} has no searchable visual language.")
    return SceneQuery(
        scene_id=scene_id,
        query=query,
        duration=float(duration),
        visual_function=str(scene.get("visual_function") or "contextual"),
        visual_intent=str(scene.get("visual_intent") or ""),
    )


def _get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "because-of-this-engine/stock-video-research", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:
        raise ResearchError(f"Provider request failed: {url}") from exc
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ResearchError(f"Provider returned invalid JSON: {url}") from exc
    if not isinstance(value, dict):
        raise ResearchError(f"Provider response must be a JSON object: {url}")
    return value


def _base_candidate(
    *,
    provider: str,
    candidate_id: str,
    title: str,
    description: str,
    tags: str,
    source_page_url: str,
    download_url: str | None,
    license_url: str,
    license_name: str,
    duration: float | None,
    width: int | None,
    height: int | None,
    attribution: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "candidate_id": candidate_id,
        "title": title.strip(),
        "description": description.strip(),
        "tags": tags.strip(),
        "source_page_url": source_page_url,
        "download_url": download_url,
        "license_url": license_url,
        "license": license_name,
        "attribution": attribution,
        "rights_status": "REVIEW_REQUIRED",
        "approved_for_render": False,
        "duration_seconds": duration,
        "width": width,
        "height": height,
    }


def _search_pexels(query: SceneQuery, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise ResearchError("PEXELS_API_KEY is not configured; use browser review or add the free Pexels API key.")
    params = urllib.parse.urlencode({"query": query.query, "per_page": min(max(limit, 1), 80)})
    payload = _get_json(f"{PEXELS_SEARCH}?{params}", {"Authorization": key})
    results: list[dict[str, Any]] = []
    for item in payload.get("videos", []) if isinstance(payload.get("videos"), list) else []:
        if not isinstance(item, dict):
            continue
        files = item.get("video_files", [])
        best = None
        if isinstance(files, list):
            usable = [f for f in files if isinstance(f, dict) and f.get("link")]
            if usable:
                best = max(usable, key=lambda f: (int(f.get("width") or 0), int(f.get("height") or 0)))
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        results.append(_base_candidate(
            provider="pexels",
            candidate_id=str(item.get("id") or ""),
            title=f"Pexels video {item.get('id')}",
            description="",
            tags=query.query,
            source_page_url=str(item.get("url") or ""),
            download_url=str(best.get("link")) if best else None,
            license_url="https://www.pexels.com/license/",
            license_name="Pexels License",
            duration=float(item.get("duration")) if isinstance(item.get("duration"), (int, float)) else None,
            width=int(best.get("width")) if best and best.get("width") else None,
            height=int(best.get("height")) if best and best.get("height") else None,
            attribution=str(user.get("name") or ""),
        ))
    return results


def _search_pixabay(query: SceneQuery, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise ResearchError("PIXABAY_API_KEY is not configured; use browser review or add the free Pixabay API key.")
    params = urllib.parse.urlencode({
        "key": key,
        "q": query.query,
        "per_page": min(max(limit, 3), 200),
        "safesearch": "true",
    })
    payload = _get_json(f"{PIXABAY_SEARCH}?{params}")
    results: list[dict[str, Any]] = []
    for item in payload.get("hits", []) if isinstance(payload.get("hits"), list) else []:
        if not isinstance(item, dict):
            continue
        videos = item.get("videos") if isinstance(item.get("videos"), dict) else {}
        choices = [value for value in videos.values() if isinstance(value, dict) and value.get("url")]
        best = max(choices, key=lambda f: (int(f.get("width") or 0), int(f.get("height") or 0))) if choices else None
        results.append(_base_candidate(
            provider="pixabay",
            candidate_id=str(item.get("id") or ""),
            title=str(item.get("tags") or f"Pixabay video {item.get('id')}"),
            description="",
            tags=str(item.get("tags") or ""),
            source_page_url=str(item.get("pageURL") or ""),
            download_url=str(best.get("url")) if best else None,
            license_url="https://pixabay.com/service/license-summary/",
            license_name="Pixabay Content License",
            duration=float(item.get("duration")) if isinstance(item.get("duration"), (int, float)) else None,
            width=int(best.get("width")) if best and best.get("width") else None,
            height=int(best.get("height")) if best and best.get("height") else None,
            attribution=str(item.get("user") or ""),
        ))
    return results


def score_candidate(candidate: dict[str, Any], scene: SceneQuery) -> float:
    scene_terms = _tokens(f"{scene.query} {scene.visual_intent} {scene.visual_function}")
    candidate_terms = _tokens(" ".join([
        str(candidate.get("title") or ""),
        str(candidate.get("description") or ""),
        str(candidate.get("tags") or ""),
    ]))
    overlap = len(scene_terms & candidate_terms) / max(len(scene_terms), 1)
    duration = candidate.get("duration_seconds")
    if isinstance(duration, (int, float)) and duration > 0:
        duration_fit = min(float(duration) / max(scene.duration, 1.0), 1.0)
        if float(duration) < min(scene.duration, 3.0):
            duration_fit = 0.0
    else:
        duration_fit = 0.45
    width, height = candidate.get("width"), candidate.get("height")
    if isinstance(width, int) and isinstance(height, int) and height > 0:
        format_fit = 1.0 if height >= width else 0.55
    else:
        format_fit = 0.5
    provider_confidence = {"pexels": 0.72, "pixabay": 0.68}.get(
        str(candidate.get("provider")), 0.4
    )
    score = 0.55 * overlap + 0.18 * duration_fit + 0.12 * format_fit + 0.15 * provider_confidence
    return round(min(max(score, 0.0), 1.0), 4)


def research(
    manifest: dict[str, Any],
    *,
    scene_id: str | None = None,
    provider: str = "all",
    limit: int = 8,
    query_override: str | None = None,
    searchers: dict[str, Callable[[SceneQuery, int], list[dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ResearchError("Manifest requires a non-empty scenes list.")
    selected = [s for s in scenes if isinstance(s, dict) and (not scene_id or s.get("scene_id") == scene_id)]
    if scene_id and not selected:
        raise ResearchError(f"Scene not found: {scene_id}")
    names = [provider] if provider != "all" else list(PROVIDER_ORDER)
    unknown = [name for name in names if name not in PROVIDER_ORDER]
    if unknown:
        raise ResearchError(f"Unsupported provider(s): {', '.join(unknown)}")
    searchers = searchers or {
        "pexels": _search_pexels,
        "pixabay": _search_pixabay,
    }
    scene_results: list[dict[str, Any]] = []
    for raw_scene in selected:
        query = _scene_query(raw_scene, query_override if scene_id else None)
        candidates: list[dict[str, Any]] = []
        errors: list[str] = []
        for name in names:
            try:
                found = searchers[name](query, limit)
            except ResearchError as exc:
                errors.append(str(exc))
                found = []
            for candidate in found:
                candidate["scene_id"] = query.scene_id
                candidate["query"] = query.query
                candidate["relevance_score"] = score_candidate(candidate, query)
                candidates.append(candidate)
        candidates.sort(key=lambda c: float(c.get("relevance_score", 0.0)), reverse=True)
        scene_results.append({
            "scene_id": query.scene_id,
            "query": query.query,
            "duration_seconds": query.duration,
            "approval_status": "REVIEW_REQUIRED",
            "candidates": candidates[: max(limit, 1) * max(len(names), 1)],
            "provider_errors": errors,
            "fallback": "keep_authorial_image_until_exact_clip_is_approved",
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "video_id": str(manifest.get("video_id") or ""),
        "research_type": "stock_video_candidates",
        "rights_policy": "no_auto_approval",
        "browser_review_required": True,
        "generated_by": "production/stock_video_research.py",
        "scenes": scene_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--scene")
    parser.add_argument("--provider", default="all", choices=["all", *PROVIDER_ORDER])
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument("--query")
    parser.add_argument("--output", default="stock-video-candidates.json")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        result = research(
            manifest,
            scene_id=args.scene,
            provider=args.provider,
            limit=args.max_results,
            query_override=args.query,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "RESEARCH_COMPLETE",
            "video_id": result["video_id"],
            "scenes": len(result["scenes"]),
            "candidate_count": sum(len(scene["candidates"]) for scene in result["scenes"]),
            "approval_status": "REVIEW_REQUIRED",
            "output": str(output),
        }, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, ResearchError) as exc:
        print(f"RESEARCH_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
