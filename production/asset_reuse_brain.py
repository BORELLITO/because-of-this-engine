#!/usr/bin/env python3
"""Global no-repeat brain for Because of This video assets.

The episode contract already prevents the same clip from appearing twice inside
one story. This module adds the missing memory layer: it scans every tracked
episode manifest and blocks a new story from reusing an approved clip by
checksum, Drive identity, perceptual fingerprint, or exact source clip.

The two pilot episodes were rendered before this gate existed. They are
explicitly treated as a locked historical baseline so the upgrade can be
introduced without invalidating their already-delivered test renders.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

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


class AssetReuseBrainError(ValueError):
    """Raised when the global no-repeat audit cannot be completed."""


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _source_key(asset: dict[str, Any]) -> str | None:
    source = _norm(asset.get("source_page_url"))
    if not source:
        return None
    segment_in = asset.get("source_segment_in")
    segment_out = asset.get("source_segment_out")
    if segment_in is not None and segment_out is not None:
        return f"{source}|segment={float(segment_in):.3f}-{float(segment_out):.3f}"
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
    source = _source_key(asset)
    if source:
        keys.append(("source_clip", source))
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
            "keys": _asset_keys(asset),
        })
    return records


def _all_manifests(repo_root: Path) -> list[Path]:
    episodes = repo_root / "episodes"
    if not episodes.is_dir():
        raise AssetReuseBrainError(f"Episode root is missing: {episodes}")
    return sorted(
        path for path in episodes.glob("*/manifest.json")
        if path.is_file()
    )


def audit(manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    repo_root = repo_root.resolve()
    target_manifest = _manifest(manifest_path)
    target_id = _norm(target_manifest.get("video_id"))
    if not target_id:
        raise AssetReuseBrainError("Target manifest video_id is missing.")

    manifests = _all_manifests(repo_root)
    if manifest_path not in {path.resolve() for path in manifests}:
        manifests.append(manifest_path)
        manifests.sort()

    all_records: list[dict[str, Any]] = []
    for path in manifests:
        all_records.extend(_episode_records(path))

    target_records = [
        record for record in all_records
        if record["episode_id"] == target_id
    ]
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
            matches = [
                other for other in by_key.get(key, [])
                if other["episode_id"] not in {target_id}
            ]
            for other in matches:
                cross_episode.append({
                    "key_type": key[0],
                    "key": key[1],
                    "current_scene": record["scene_id"],
                    "current_asset": record["asset_id"],
                    "previous_episode": other["episode_id"],
                    "previous_scene": other["scene_id"],
                    "previous_asset": other["asset_id"],
                })

    # Avoid emitting the same collision repeatedly when an asset shares more
    # than one identity field with its historical record.
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
    invalid_legacy_flag = (
        policy.get("legacy_baseline") is True
        and not legacy_baseline
    )

    if invalid_legacy_flag:
        status = "BLOCKED"
        reason = "legacy_baseline is only valid for the locked pilot manifests."
    elif within_episode:
        status = "BLOCKED"
        reason = "the same asset identity appears more than once in this episode."
    elif unique_cross and not legacy_baseline:
        status = "BLOCKED"
        reason = "a new episode reuses a clip already assigned to another story."
    elif unique_cross and legacy_baseline:
        status = "LEGACY_BASELINE_PASS"
        reason = "historical pilot reuse recorded; new episodes remain blocked."
    else:
        status = "ASSET_REUSE_PASS"
        reason = "no clip identity overlaps another episode."

    return {
        "status": status,
        "policy": "GLOBAL_NO_REPEAT",
        "video_id": target_id,
        "manifest": str(manifest_path),
        "scanned_episode_count": len(manifests),
        "scanned_episode_ids": sorted({_norm(_manifest(path).get("video_id")) for path in manifests}),
        "candidate_asset_count": len(target_records),
        "within_episode_duplicates": within_episode,
        "cross_episode_duplicates": unique_cross,
        "legacy_baseline": legacy_baseline,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.repo_root)
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["status"] != "BLOCKED" else 1
    except (AssetReuseBrainError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ASSET REUSE BRAIN BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
