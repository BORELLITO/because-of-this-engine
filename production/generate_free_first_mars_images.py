#!/usr/bin/env python3
"""Generate Mars assets using the free-first visual policy."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cloudflare_image_provider import CloudflareImageProvider
from free_first_image_provider import FreeFirstImageProvider
from generate_mars_images import NASA_SCENE_QUERIES, SCENE_PROMPTS
from image_provider import ImageGenerationError, ImageRequest
from nasa_image_provider import NASAImageProvider

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "mars-assets"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Mars assets with factual-first routing.")
    parser.add_argument("--scene", choices=["ALL", *SCENE_PROMPTS], default="ALL")
    parser.add_argument("--output-dir", type=Path, default=ASSET_DIR)
    parser.add_argument("--max-requests", type=int, default=6)
    parser.add_argument("--allow-generative-fallback", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        factual = NASAImageProvider(
            quota_ledger=args.output_dir / "usage.json",
            max_requests_per_day=args.max_requests,
        )
        generative = None
        if args.allow_generative_fallback:
            generative = CloudflareImageProvider(
                account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
                api_token=os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(),
                model=os.environ.get(
                    "IMAGE_MODEL",
                    "@cf/stabilityai/stable-diffusion-xl-base-1.0",
                ),
                quota_ledger=args.output_dir / "usage.json",
                max_requests_per_day=args.max_requests,
            )

        provider = FreeFirstImageProvider(
            factual_provider=factual,
            generative_provider=generative,
            allow_generative_fallback=args.allow_generative_fallback,
        )
        scenes = list(SCENE_PROMPTS) if args.scene == "ALL" else [args.scene]
        for scene_id in scenes:
            output = args.output_dir / f"{scene_id.lower()}-background.png"
            request = ImageRequest(
                scene_id=scene_id,
                prompt=SCENE_PROMPTS[scene_id],
                output_path=output,
                aspect_ratio="9:16",
                image_size="1K",
                overwrite=args.overwrite,
            )
            result = provider.generate(request, query=NASA_SCENE_QUERIES[scene_id])
            print(
                f"{scene_id}: {output} ({result['width']}x{result['height']}, "
                f"{result['selected_source']})"
            )
    except ImageGenerationError as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
