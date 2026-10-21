#!/usr/bin/env python3
"""Generate authorial episode assets from a prompt pack.

This path is deliberately separate from the factual NASA provider. It never
silently falls back to unrelated imagery and it requires an explicit provider.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from image_provider import ImageGenerationError, ImageRequest, GeminiImageProvider
from cloudflare_image_provider import CloudflareImageProvider


def read_pack(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImageGenerationError(f"Could not read prompt pack: {path}") from exc
    if data.get("provider_mode") != "authorial-generative":
        raise ImageGenerationError("Prompt pack is not an authorial-generative pack.")
    if not isinstance(data.get("scenes"), list) or not data["scenes"]:
        raise ImageGenerationError("Prompt pack has no scenes.")
    return data


def build_provider(name: str, output_dir: Path, limit: int):
    ledger = output_dir / "usage.json"
    if name == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        return GeminiImageProvider(
            api_key=key,
            model=os.environ.get("IMAGE_MODEL", "gemini-nano-banana-2.1"),
            quota_ledger=ledger,
            max_requests_per_day=limit,
        )
    if name == "cloudflare":
        return CloudflareImageProvider(
            account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
            api_token=os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(),
            model=os.environ.get("IMAGE_MODEL", "@cf/stabilityai/stable-diffusion-xl-base-1.0"),
            quota_ledger=ledger,
            max_requests_per_day=limit,
        )
    raise ImageGenerationError(f"Unsupported authorial provider: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate authorial images from a prompt pack.")
    parser.add_argument("--prompt-pack", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--provider", choices=("gemini", "cloudflare"), required=True)
    parser.add_argument("--scene", default="ALL")
    parser.add_argument("--max-requests", type=int, default=6)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        pack = read_pack(args.prompt_pack)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        provider = build_provider(args.provider, args.output_dir, args.max_requests)
        scenes = pack["scenes"]
        if args.scene != "ALL":
            scenes = [scene for scene in scenes if scene.get("scene_id") == args.scene]
            if not scenes:
                raise ImageGenerationError(f"Scene not found in prompt pack: {args.scene}")
        for scene in scenes:
            scene_id = scene.get("scene_id")
            prompt = scene.get("prompt")
            if not isinstance(scene_id, str) or not isinstance(prompt, str) or not prompt.strip():
                raise ImageGenerationError("Every prompt-pack scene needs scene_id and prompt.")
            negative = scene.get("negative_prompt", "")
            full_prompt = prompt + (f" Negative prompt: {negative}" if negative else "")
            request = ImageRequest(
                scene_id=scene_id,
                prompt=full_prompt,
                output_path=args.output_dir / f"{scene_id}.png",
                aspect_ratio="9:16",
                image_size="1K",
                overwrite=args.overwrite,
            )
            metadata = provider.generate(request)
            print(f"{scene_id}: {metadata.get('width')}x{metadata.get('height')} {metadata.get('provider')}")
    except ImageGenerationError as exc:
        print(f"AUTHORIAL IMAGE GENERATION FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
