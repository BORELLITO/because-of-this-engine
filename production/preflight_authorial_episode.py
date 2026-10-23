#!/usr/bin/env python3
"""Run the non-destructive preflight before generating an authorial preview."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from production.render_authorial_episode import RenderError, read_json, validate_manifest
except ModuleNotFoundError:  # documented script execution path
    from render_authorial_episode import RenderError, read_json, validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight an authorial episode before rendering.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    try:
        manifest = read_json(manifest_path)
        spec = validate_manifest(manifest, manifest_path.parent, mode=args.mode)
    except RenderError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, indent=2))
        return 1

    missing_sidecars = []
    unreadable_images = []
    try:
        from PIL import Image
        for scene in spec["scenes"]:
            image = Path(scene["image"])
            sidecar = image.with_suffix(image.suffix + ".json")
            if not sidecar.is_file():
                missing_sidecars.append(str(sidecar))
            try:
                with Image.open(image) as opened:
                    opened.verify()
            except Exception:
                unreadable_images.append(str(image))
    except ImportError:
        unreadable_images.append("Pillow is not installed")

    ready_status = "READY_FOR_FINAL_PREFLIGHT" if args.mode == "final" else "READY_FOR_PREVIEW"
    status = ready_status if not missing_sidecars and not unreadable_images else "BLOCKED"
    payload = {
        "status": status,
        "video_id": spec["video_id"],
        "audio_duration_seconds": round(spec["audio_duration"], 3),
        "timeline_seconds": round(spec["timeline"], 3),
        "scene_count": len(spec["scenes"]),
        "motions": [{"scene_id": s["scene_id"], "type": s["motion"]["type"]} for s in spec["scenes"]],
        "missing_provenance_sidecars": missing_sidecars,
        "unreadable_images": unreadable_images,
        "next_step": (
            "check approval and render final only after READY_FOR_FINAL_PREFLIGHT"
            if status == "READY_FOR_FINAL_PREFLIGHT"
            else "render preview only after READY_FOR_PREVIEW"
            if status == "READY_FOR_PREVIEW"
            else "repair listed inputs first"
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == "READY_FOR_PREVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
