#!/usr/bin/env python3
"""Safely ingest an externally generated authorial image into an episode.

This command never generates or invents an image. It copies an existing image,
validates it, and records the exact provenance needed by the release gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class IngestError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as handle:
            temporary = handle.name
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    except OSError as exc:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
        raise IngestError(f"Could not copy asset to {target}") from exc


def image_info(path: Path) -> tuple[int, int, str]:
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            if width < 512 or height < 512:
                raise IngestError("Image must be at least 512x512.")
            return width, height, image.format or "unknown"
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"Image is unreadable: {path}") from exc


def prompt_for_scene(pack: Path | None, scene_id: str) -> tuple[str | None, str | None]:
    if pack is None:
        return None, None
    data = json.loads(pack.read_text(encoding="utf-8"))
    for scene in data.get("scenes", []):
        if scene.get("scene_id") == scene_id:
            return scene.get("prompt"), data.get("visual_style_id")
    raise IngestError(f"Scene {scene_id} was not found in prompt pack.")


def ingest(args: argparse.Namespace) -> dict:
    source = args.source.resolve()
    target = args.output.resolve()
    if not source.is_file():
        raise IngestError(f"Source image is missing: {source}")
    if target.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise IngestError("Output must be PNG or JPEG.")
    sidecar = target.with_suffix(target.suffix + ".json")
    if not args.overwrite and (target.exists() or sidecar.exists()):
        raise IngestError(f"Output already exists: {target}")
    width, height, image_format = image_info(source)
    prompt, style_id = prompt_for_scene(args.prompt_pack, args.scene_id) if args.prompt_pack else (None, None)
    atomic_copy(source, target)
    metadata = {
        "schema_version": "1.0",
        "scene_id": args.scene_id,
        "provider": args.provider,
        "model": args.model,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else None,
        "visual_style_id": style_id,
        "source_path": str(source),
        "source_sha256": sha256(source),
        "sha256": sha256(target),
        "width": width,
        "height": height,
        "format": image_format,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "human_review_required": True,
        "review_status": "REVIEW_REQUIRED",
        "note": "Ingested asset; no image generation was performed by this command.",
    }
    sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest an authorial image with provenance.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-pack", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(ingest(args), ensure_ascii=False, indent=2))
    except (IngestError, OSError, json.JSONDecodeError) as exc:
        print(f"ASSET INGEST FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
