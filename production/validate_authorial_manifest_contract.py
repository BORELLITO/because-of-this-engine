#!/usr/bin/env python3
"""Validate the authorial manifest contract without requiring episode assets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class ContractError(ValueError):
    pass


def validate(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.1":
        raise ContractError("schema_version must be 1.1")
    if not isinstance(data.get("video_id"), str) or not data["video_id"].strip():
        raise ContractError("video_id is required")
    for section in ("script", "audio", "captions", "approval", "output"):
        if not isinstance(data.get(section), dict):
            raise ContractError(f"{section} must be an object")
    if not isinstance(data["script"].get("path"), str):
        raise ContractError("script.path is required")
    if not isinstance(data["audio"].get("path"), str):
        raise ContractError("audio.path is required")
    if not isinstance(data["captions"].get("path"), str):
        raise ContractError("captions.path is required")
    if not isinstance(data["approval"].get("path"), str):
        raise ContractError("approval.path is required")
    output = data["output"].get("path")
    if not isinstance(output, str) or "{mode}" not in output:
        raise ContractError("output.path must contain {mode}")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ContractError("at least one scene is required")
    ids = set()
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ContractError(f"scene {index} must be an object")
        scene_id = scene.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id.strip() or scene_id in ids:
            raise ContractError(f"scene {index} has an invalid or duplicate scene_id")
        ids.add(scene_id)
        if not isinstance(scene.get("image"), str) or not scene["image"].strip():
            raise ContractError(f"{scene_id} requires image")
        if not isinstance(scene.get("duration"), (int, float)) or scene["duration"] <= 0:
            raise ContractError(f"{scene_id} requires positive duration")
        zoom = scene.get("zoom_end", 1.07)
        if not isinstance(zoom, (int, float)) or not 1.0 <= zoom <= 1.15:
            raise ContractError(f"{scene_id} has unsafe zoom_end")
    if data.get("require_captions") is not True:
        raise ContractError("require_captions must be true")
    if data.get("require_provenance") is not True:
        raise ContractError("require_provenance must be true")
    return {"status": "CONTRACT_VALID", "video_id": data["video_id"], "scene_count": len(scenes)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an authorial manifest contract.")
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.manifest), ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"CONTRACT INVALID: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
