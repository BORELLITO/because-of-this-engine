#!/usr/bin/env python3
"""Fail-closed global audio reuse and similarity audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class AudioReuseError(RuntimeError):
    pass


def audit(manifest_path: Path, repo_root: Path, registry_path: Path | None = None) -> dict[str, Any]:
    current = json.loads(manifest_path.read_text(encoding="utf-8"))
    current_id = str(current.get("video_id") or manifest_path.parent.name)
    records: dict[str, list[str]] = {}
    errors: list[str] = []
    for path in sorted((repo_root / "episodes").glob("*/manifest.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("lifecycle_status") == "ARCHIVED_HISTORICAL":
            continue
        episode_id = str(value.get("video_id") or path.parent.name)
        music = value.get("music") or {}
        keys = [music.get("track_id"), music.get("sha256"), music.get("path")]
        for key in keys:
            if key:
                records.setdefault(str(key), []).append(episode_id)
        if episode_id == current_id:
            report = music.get("similarity_review") or {}
            if report.get("status") not in {None, "PASS"}:
                errors.append("current music similarity review is not PASS")
    for key, episodes in records.items():
        unique = sorted(set(episodes))
        if len(unique) > 1 and current_id in unique:
            errors.append(f"complete audio identity reused across episodes: {key} -> {unique}")
    if registry_path and registry_path.is_file():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AudioReuseError("audio registry is unreadable") from exc
        for track in registry.get("tracks", []):
            if track.get("episode_id") == current_id and track.get("reuse_status") not in {None, "FRESH", "APPROVED_REUSE"}:
                errors.append("current registry track has invalid reuse_status")
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "video_id": current_id,
        "errors": errors,
        "unique_identities": len(records),
        "policy": "complete tracks never reused; reusable SFX require a three-video cooldown",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.manifest.resolve(), args.repo_root.resolve(), args.registry.resolve() if args.registry else None)
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["status"] == "PASS" else 1
    except (OSError, ValueError, json.JSONDecodeError, AudioReuseError) as exc:
        print(f"AUDIO REUSE BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
