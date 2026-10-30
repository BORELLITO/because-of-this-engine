#!/usr/bin/env python3
"""Global source-level asset memory for Because of This.

The no-reuse rule is global: once a source video is used by an episode, the
whole source asset is retired. A different segment, filename, re-encode, crop,
or Drive copy is not a new clip. Manifests remain the local evidence source and
an optional durable registry preserves the memory after runtime media cleanup.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LEGACY_BASELINE_EPISODES = {
    "because-of-this-episode-001",
    "because-of-this-episode-002",
}
IDENTITY_FIELDS = (
    "sha256",
    "drive_file_id",
    "perceptual_hash",
    "animation_fingerprint",
)
REGISTRY_SCHEMA_VERSION = 1
_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref", "ref_")
_PROVIDER_ID_KEYS = ("provider_asset_id", "source_asset_id", "provider_id")


class AssetReuseBrainError(ValueError):
    """Raised when the global no-repeat audit cannot be completed."""


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def canonicalize_source_url(value: Any) -> str:
    """Normalize a source page URL without collapsing distinct provider assets."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.lower().rstrip("/")
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(_TRACKING_PREFIXES)
    ]
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        urlencode(sorted(query)),
        "",
    )).rstrip("/")


def _provider_asset_id(asset: dict[str, Any]) -> str:
    for key in _PROVIDER_ID_KEYS:
        value = _norm(asset.get(key))
        if value:
            return value
    provider = _norm(asset.get("provider"))
    source = canonicalize_source_url(asset.get("source_page_url"))
    if provider == "pexels":
        match = re.search(r"/video/(?:[^/]+-)?(\d+)$", source)
        if match:
            return match.group(1)
    if provider == "pixabay":
        match = re.search(r"/videos/(?:[^/]+-)?(\d+)", source)
        if match:
            return match.group(1)
    if provider == "mixkit":
        match = re.search(r"-(\d+)$", source)
        if match:
            return match.group(1)
    return ""


def source_asset_key(asset: dict[str, Any]) -> str | None:
    """Return a segment-independent identity for the provider source video."""
    provider = _norm(asset.get("provider")) or "unknown"
    provider_id = _provider_asset_id(asset)
    if provider_id:
        return f"{provider}:{provider_id}"
    source = canonicalize_source_url(asset.get("source_page_url"))
    return f"url:{source}" if source else None


def source_segment_key(asset: dict[str, Any]) -> str | None:
    source = source_asset_key(asset)
    if not source:
        return None
    segment_in = asset.get("source_segment_in")
    segment_out = asset.get("source_segment_out")
    if segment_in is None or segment_out is None:
        return source
    try:
        return f"{source}|segment={float(segment_in):.3f}-{float(segment_out):.3f}"
    except (TypeError, ValueError):
        return source


def _manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetReuseBrainError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise AssetReuseBrainError(f"Manifest must be an object: {path}")
    return value


def _asset_keys(asset: dict[str, Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    for field in IDENTITY_FIELDS:
        value = _norm(asset.get(field))
        if value:
            keys.append((field, value))
    source = _norm(asset.get("source_asset_key")) or source_asset_key(asset)
    if source:
        keys.append(("source_asset", source))
    canonical_url = canonicalize_source_url(asset.get("source_page_url"))
    if canonical_url:
        keys.append(("canonical_source_url", canonical_url))
    return keys


def _episode_records(path: Path) -> list[dict[str, Any]]:
    manifest = _manifest(path)
    video_id = _norm(manifest.get("video_id"))
    if not video_id:
        raise AssetReuseBrainError(f"Manifest video_id is missing: {path}")
    records: list[dict[str, Any]] = []
    for scene in manifest.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        asset = scene.get("asset") or {}
        if not isinstance(asset, dict):
            continue
        records.append({
            "episode_id": video_id,
            "manifest": str(path),
            "scene_id": scene.get("scene_id"),
            "asset_id": asset.get("asset_id"),
            "provider": asset.get("provider"),
            "source_asset_key": source_asset_key(asset),
            "source_segment_key": source_segment_key(asset),
            "status": "RETIRED",
            "retired_reason": f"used_by:{video_id}",
            "keys": _asset_keys(asset),
        })
    return records


def _all_manifests(repo_root: Path) -> list[Path]:
    episodes = repo_root / "episodes"
    if not episodes.is_dir():
        raise AssetReuseBrainError(f"Episode root is missing: {episodes}")
    return sorted(path for path in episodes.glob("*/manifest.json") if path.is_file())


def _registry_records(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetReuseBrainError(f"Could not read asset memory registry: {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise AssetReuseBrainError("Asset memory registry has an unsupported schema.")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise AssetReuseBrainError("Asset memory registry assets must be a list.")
    records: list[dict[str, Any]] = []
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise AssetReuseBrainError(f"Asset memory registry record {index} is invalid.")
        episode_id = _norm(asset.get("first_used_video_id") or asset.get("episode_id"))
        if not episode_id:
            raise AssetReuseBrainError(f"Asset memory registry record {index} has no first-used episode.")
        records.append({
            "episode_id": episode_id,
            "manifest": str(path),
            "scene_id": asset.get("first_used_scene_id") or asset.get("scene_usage"),
            "asset_id": asset.get("asset_id") or asset.get("registry_id"),
            "provider": asset.get("provider"),
            "source_asset_key": _norm(asset.get("source_asset_key")) or source_asset_key(asset),
            "source_segment_key": _norm(asset.get("source_segment_key")) or source_segment_key(asset),
            "status": asset.get("status", "RETIRED"),
            "retired_reason": asset.get("retired_reason", "registry"),
            "keys": _asset_keys(asset),
        })
    return records


def _registry_snapshot(repo_root: Path, registry_path: Path | None = None) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in _all_manifests(repo_root):
        records.extend(_episode_records(path))
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        source = record.get("source_asset_key")
        if not source:
            continue
        if source not in grouped:
            grouped[source] = {
                "registry_id": f"asset-{len(grouped) + 1:05d}",
                "source_asset_key": source,
                "source_segment_key": record.get("source_segment_key"),
                "provider": record.get("provider"),
                "asset_id": record.get("asset_id"),
                "first_used_video_id": record.get("episode_id"),
                "first_used_scene_id": record.get("scene_id"),
                "status": "RETIRED",
                "retired_reason": "used_by_episode",
                "keys": record.get("keys", []),
            }
    if registry_path and registry_path.is_file():
        existing = _registry_records(registry_path)
        for record in existing:
            source = record.get("source_asset_key")
            if source and source not in grouped:
                grouped[source] = {
                    "registry_id": record.get("asset_id") or f"asset-{len(grouped) + 1:05d}",
                    "source_asset_key": source,
                    "source_segment_key": record.get("source_segment_key"),
                    "provider": record.get("provider"),
                    "first_used_video_id": record.get("episode_id"),
                    "first_used_scene_id": record.get("scene_id"),
                    "status": record.get("status", "RETIRED"),
                    "retired_reason": record.get("retired_reason", "registry"),
                    "keys": record.get("keys", []),
                }
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "policy": "GLOBAL_NO_REPEAT_SOURCE_ASSET",
        "assets": list(grouped.values()),
    }


def audit(
    manifest_path: Path,
    repo_root: Path,
    *,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    repo_root = repo_root.resolve()
    target_manifest = _manifest(manifest_path)
    target_id = _norm(target_manifest.get("video_id"))
    if not target_id:
        raise AssetReuseBrainError("Target manifest video_id is missing.")
    if registry_path is not None:
        registry_path = registry_path.resolve()
        if not registry_path.is_file():
            raise AssetReuseBrainError("ASSET_MEMORY_UNAVAILABLE: registry file is missing.")
        registry_records = _registry_records(registry_path)
    else:
        registry_records = []

    manifests = _all_manifests(repo_root)
    if manifest_path not in {path.resolve() for path in manifests}:
        manifests.append(manifest_path)
        manifests.sort()
    manifest_records: list[dict[str, Any]] = []
    for path in manifests:
        manifest_records.extend(_episode_records(path))
    archived_episode_ids = {
        _norm(_manifest(path).get("video_id"))
        for path in manifests
        if _norm(_manifest(path).get("lifecycle_status")) == "archived_historical"
    }
    # An archived story is not permission to reuse a previously consumed source.
    # Keep even archival records in the global source history. Legacy baseline
    # collisions remain explicitly recorded and release-blocked below.
    all_records = manifest_records + registry_records
    target_records = [record for record in manifest_records if record["episode_id"] == target_id]
    if not target_records:
        raise AssetReuseBrainError("Target manifest contains no usable video assets.")

    within_episode: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for record in target_records:
        for key in record["keys"]:
            previous = seen.get(key)
            if previous:
                within_episode.append({
                    "key_type": key[0],
                    "key": key[1],
                    "first_scene": previous["scene_id"],
                    "duplicate_scene": record["scene_id"],
                })
            else:
                seen[key] = record

    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in all_records:
        for key in record["keys"]:
            by_key.setdefault(key, []).append(record)

    cross_episode: list[dict[str, Any]] = []
    for record in target_records:
        for key in record["keys"]:
            for other in by_key.get(key, []):
                if other["episode_id"] == target_id:
                    continue
                cross_episode.append({
                    "key_type": key[0],
                    "key": key[1],
                    "current_scene": record["scene_id"],
                    "current_asset": record["asset_id"],
                    "previous_episode": other["episode_id"],
                    "previous_scene": other["scene_id"],
                    "previous_asset": other["asset_id"],
                    "historical": (
                        other["episode_id"] in LEGACY_BASELINE_EPISODES
                        or other["episode_id"] in archived_episode_ids
                    ),
                })

    unique_cross: list[dict[str, Any]] = []
    seen_collisions: set[tuple[str, str, str, str]] = set()
    for item in cross_episode:
        signature = (
            item["key_type"],
            item["key"],
            item["current_scene"],
            item["previous_episode"],
        )
        if signature not in seen_collisions:
            seen_collisions.add(signature)
            unique_cross.append(item)

    policy = target_manifest.get("asset_reuse_brain") or {}
    legacy_baseline = (
        target_id in LEGACY_BASELINE_EPISODES
        and policy.get("legacy_baseline") is True
        and _norm(policy.get("policy")) == "global_no_repeat"
    )
    invalid_legacy_flag = policy.get("legacy_baseline") is True and not legacy_baseline

    if invalid_legacy_flag:
        status = "BLOCKED"
        reason = "legacy_baseline is only valid for the locked pilot manifests."
    elif within_episode:
        status = "BLOCKED"
        reason = "the same source or asset identity appears more than once in this episode."
    elif unique_cross and legacy_baseline:
        status = "HISTORICAL_COLLISION_RECORDED"
        reason = "historical pilot overlap recorded; every colliding source is retired for future episodes."
    elif unique_cross:
        status = "BLOCKED"
        reason = "a new episode reuses a source asset already assigned to another story."
    else:
        status = "ASSET_REUSE_PASS"
        reason = "no source asset identity overlaps another episode."

    return {
        "status": status,
        "release_blocked": status in {"BLOCKED", "HISTORICAL_COLLISION_RECORDED"},
        "policy": "GLOBAL_NO_REPEAT_SOURCE_ASSET",
        "video_id": target_id,
        "manifest": str(manifest_path),
        "registry_status": "AVAILABLE" if registry_path else "MANIFEST_BACKED",
        "scanned_episode_count": len(manifests),
        "scanned_episode_ids": sorted({_norm(_manifest(path).get("video_id")) for path in manifests}),
        "candidate_asset_count": len(target_records),
        "within_episode_duplicates": within_episode,
        "cross_episode_duplicates": unique_cross,
        "legacy_baseline": legacy_baseline,
        "ignored_historical_episode_ids": [],
        "audited_historical_episode_ids": sorted(archived_episode_ids - {target_id}),
        "retired_source_assets": sorted({
            item["key"] for item in unique_cross if item["key_type"] == "source_asset"
        }),
        "reason": reason,
    }


def write_registry(repo_root: Path, output: Path, existing: Path | None = None) -> dict[str, Any]:
    payload = _registry_snapshot(repo_root.resolve(), existing.resolve() if existing else None)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--write-registry", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if args.write_registry:
            payload = write_registry(args.repo_root, args.write_registry, args.registry)
            print(json.dumps({
                "status": "ASSET_MEMORY_REGISTRY_WRITTEN",
                "assets": len(payload["assets"]),
                "path": str(args.write_registry),
            }))
            return 0
        if not args.manifest or not args.report:
            parser.error("--manifest and --report are required for an audit.")
        report = audit(args.manifest, args.repo_root, registry_path=args.registry)
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["status"] == "ASSET_REUSE_PASS" else 1
    except (AssetReuseBrainError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ASSET REUSE BRAIN BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
