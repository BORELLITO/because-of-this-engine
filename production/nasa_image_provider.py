#!/usr/bin/env python3
"""NASA Image and Video Library provider for factual, free-first visuals.

This provider deliberately uses NASA's public image search instead of a
generative model.  It is a better default for factual science shorts: the
source image is semantically tied to the requested subject, the asset is
cropped to the episode's vertical format, and provenance is retained in a
sidecar file.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from image_provider import ImageGenerationError, ImageRequest, _atomic_write, _validate_image, _write_json_atomic

NASA_SEARCH_URL = "https://images-api.nasa.gov/search"
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920


def _json_request(url: str, *, timeout: int = 60) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "because-of-this-engine/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ImageGenerationError("NASA image search failed. Check network access and try again.") from exc
    if not isinstance(payload, dict):
        raise ImageGenerationError("NASA returned an invalid search response.")
    return payload


def _download(url: str, *, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "because-of-this-engine/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ImageGenerationError("NASA image download failed. Check the source URL and network access.") from exc
    if not data:
        raise ImageGenerationError("NASA returned an empty image file.")
    return data


def _asset_url(item: dict[str, Any]) -> str | None:
    links = item.get("links") or []
    candidates = [
        link.get("href")
        for link in links
        if isinstance(link, dict)
        and isinstance(link.get("href"), str)
        and link["href"].lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]
    if candidates:
        candidates.sort(key=lambda value: ("~orig" in value, len(value)), reverse=True)
        return candidates[0]

    data = item.get("data") or [{}]
    nasa_id = data[0].get("nasa_id") if isinstance(data[0], dict) else None
    if not isinstance(nasa_id, str) or not nasa_id:
        return None
    manifest = _json_request(f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nasa_id, safe='')}")
    assets = manifest.get("collection", {}).get("items", [])
    candidates = [
        entry.get("href")
        for entry in assets
        if isinstance(entry, dict)
        and isinstance(entry.get("href"), str)
        and entry["href"].lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]
    if not candidates:
        return None
    # NASA filenames commonly include `~orig`; prefer the largest source.
    candidates.sort(key=lambda value: ("~orig" in value, len(value)), reverse=True)
    return candidates[0]


def _score_item(item: dict[str, Any], query: str) -> int:
    data = item.get("data") or [{}]
    record = data[0] if isinstance(data[0], dict) else {}
    title = str(record.get("title", "")).lower()
    description = str(record.get("description", "")).lower()
    terms = [term for term in query.lower().split() if len(term) > 2]
    score = sum(4 for term in terms if term in title)
    score += sum(1 for term in terms if term in description)
    score += 2 if any("mars climate orbiter" in value for value in (title, description)) else 0
    return score


def _select_item(payload: dict[str, Any], query: str) -> dict[str, Any]:
    items = payload.get("collection", {}).get("items", [])
    if not isinstance(items, list) or not items:
        raise ImageGenerationError(f"NASA returned no images for query: {query}")
    valid = [item for item in items if isinstance(item, dict) and _asset_url(item)]
    if not valid:
        raise ImageGenerationError(f"NASA returned no downloadable images for query: {query}")
    return max(valid, key=lambda item: _score_item(item, query))


def _vertical_crop(data: bytes, *, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> bytes:
    try:
        from io import BytesIO
        from PIL import Image, ImageEnhance

        with Image.open(BytesIO(data)) as source:
            source = source.convert("RGB")
            target_ratio = width / height
            source_ratio = source.width / source.height
            if source_ratio > target_ratio:
                crop_width = int(source.height * target_ratio)
                left = max(0, (source.width - crop_width) // 2)
                source = source.crop((left, 0, left + crop_width, source.height))
            elif source_ratio < target_ratio:
                crop_height = int(source.width / target_ratio)
                top = max(0, (source.height - crop_height) // 2)
                source = source.crop((0, top, source.width, top + crop_height))
            source = source.resize((width, height), Image.Resampling.LANCZOS)
            source = ImageEnhance.Contrast(source).enhance(1.04)
            source = ImageEnhance.Color(source).enhance(0.96)
            output = BytesIO()
            source.save(output, format="PNG", optimize=True)
            return output.getvalue()
    except Exception as exc:
        raise ImageGenerationError("NASA image could not be converted to the vertical PNG format.") from exc


class NASAImageProvider:
    """Download and format semantically matched NASA imagery."""

    def __init__(self, *, quota_ledger: Path | None = None, max_requests_per_day: int = 12) -> None:
        if max_requests_per_day < 1:
            raise ImageGenerationError("max_requests_per_day must be at least 1.")
        self.quota_ledger = quota_ledger or Path("production/image-generation-usage.json")
        self.max_requests_per_day = max_requests_per_day

    def _reserve_request(self) -> tuple[str, int]:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.quota_ledger.exists():
            try:
                ledger = json.loads(self.quota_ledger.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ImageGenerationError(f"Image quota ledger is unreadable: {self.quota_ledger}") from exc
        else:
            ledger = {"schema_version": 1, "days": {}}
        if not isinstance(ledger, dict) or not isinstance(ledger.get("days", {}), dict):
            raise ImageGenerationError(f"Image quota ledger has an invalid schema: {self.quota_ledger}")
        day = ledger.setdefault("days", {}).setdefault(today, {"requests": 0, "models": {}})
        used = int(day.get("requests", 0))
        if used >= self.max_requests_per_day:
            raise ImageGenerationError(f"Local image quota guard stopped the run: {used}/{self.max_requests_per_day} requests used today.")
        day["requests"] = used + 1
        day.setdefault("models", {})["nasa-images"] = int(day["models"].get("nasa-images", 0)) + 1
        _write_json_atomic(self.quota_ledger, ledger)
        return today, used + 1

    def generate(self, request: ImageRequest, *, query: str) -> dict[str, Any]:
        output_path = request.output_path.expanduser().resolve()
        sidecar_path = output_path.with_suffix(output_path.suffix + ".json")
        if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ImageGenerationError("Image output must be .png, .jpg, or .jpeg.")
        if not query.strip():
            raise ImageGenerationError("NASA search query cannot be empty.")
        if not request.overwrite and (output_path.exists() or sidecar_path.exists()):
            raise ImageGenerationError(f"Output already exists: {output_path}. Use --overwrite deliberately.")

        day, request_number = self._reserve_request()
        search_url = NASA_SEARCH_URL + "?" + urllib.parse.urlencode({"q": query, "media_type": "image", "page_size": 25})
        item = _select_item(_json_request(search_url), query)
        source_url = _asset_url(item)
        if not source_url:
            raise ImageGenerationError(f"NASA did not provide a source image for query: {query}")
        image_bytes = _vertical_crop(_download(source_url))
        image_format, width, height = _validate_image(image_bytes)
        _atomic_write(output_path, image_bytes)
        record = (item.get("data") or [{}])[0]
        metadata = {
            "schema_version": "1.0",
            "provider": "NASA Image and Video Library",
            "model": "curated-public-imagery",
            "scene_id": request.scene_id,
            "query": query,
            "title": record.get("title"),
            "description": record.get("description"),
            "nasa_id": record.get("nasa_id"),
            "source_url": source_url,
            "search_url": search_url,
            "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
            "prompt": request.prompt,
            "aspect_ratio": request.aspect_ratio,
            "format": image_format,
            "width": width,
            "height": height,
            "bytes": len(image_bytes),
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "quota_guard": {"utc_day": day, "request_number": request_number, "daily_limit": self.max_requests_per_day},
            "license_review": "NASA imagery is generally reusable, but verify third-party credits and item-specific restrictions before monetization.",
        }
        _write_json_atomic(sidecar_path, metadata)
        return metadata
