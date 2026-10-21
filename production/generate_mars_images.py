#!/usr/bin/env python3
"""Generate coherent, text-free visual assets for the Mars episode.

The generated images are backgrounds. Captions and factual labels remain in
the edit layer, which prevents the image model from inventing unreadable text.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from image_provider import GeminiImageProvider, ImageGenerationError, ImageRequest
from cloudflare_image_provider import CloudflareImageProvider
from nasa_image_provider import NASAImageProvider

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "mars-assets"

SCENE_PROMPTS = {
    "S01": (
        "Vertical 9:16 cinematic documentary still for a science mystery short. "
        "A believable small Mars orbiter spacecraft in the foreground, drifting through deep space; "
        "Mars is a large, clearly recognizable red planet in the lower-right distance; Earth is a tiny blue point far behind in the upper-left. "
        "The visual relationship must read immediately as Earth to spacecraft to Mars. Realistic NASA-era spacecraft proportions, restrained orange and cyan rim light, deep black space, "
        "high contrast, atmospheric, serious suspense. No text, no labels, no logos, no extra planets, no abstract geometry."
    ),
    "S02": (
        "Vertical 9:16 cinematic documentary still inside a 1990s spacecraft mission-control room. "
        "A navigation engineer studies two separate technical printouts and instrument readouts on a desk, with clearly different unit symbols and measurement scales suggested visually, "
        "but no legible text required. Cool blue monitor glow against one warm warning light, realistic paper, cables, old CRT equipment, tense quiet atmosphere. "
        "No logos, no invented readable words, no fantasy interface, no extra people."
    ),
    "S03": (
        "Vertical 9:16 cinematic space-science visualization. A small Mars orbiter is seen from above against the curved limb of Mars, "
        "with one clean intended flight arc and a second subtly displaced arc implied by the spacecraft's wrong approach. "
        "The planet and spacecraft must be physically legible, realistic lighting, restrained documentary color grade, suspenseful but accurate. "
        "Leave clean dark negative space for later vector trajectory overlays. No text, no labels, no arrows, no logos."
    ),
    "S04": (
        "Vertical 9:16 cinematic close approach to Mars. A small spacecraft passes dangerously close above the red planet's curved horizon, "
        "with a thin blue atmospheric rim and the planet filling the lower half of frame. The spacecraft is visibly too low and too close, "
        "creating immediate physical danger. Realistic scale, hard sunlight, deep shadow, red dust haze, suspense documentary style. "
        "No explosion, no text, no labels, no logos, no extra spacecraft."
    ),
    "S05": (
        "Vertical 9:16 cinematic documentary still in a dark mission-control room after a spacecraft anomaly. "
        "One empty operator console and a silent telemetry monitor dominate the frame; a red warning light is reflected on the desk, "
        "chairs slightly pulled back, atmosphere of sudden loss and uncertainty. Late-1990s engineering room, realistic materials, no readable screen text, no logos."
    ),
    "S06": (
        "Vertical 9:16 cinematic final image for a science mystery short. Mars fills the lower frame while a tiny spacecraft disappears behind the planet's dark limb, "
        "leaving only a faint fading signal glow in the distance. Somber, quiet, consequential, realistic space photography, restrained orange and cyan palette, "
        "clear visual ending. No explosion, no text, no labels, no logos, no extra planets."
    ),
}

NASA_SCENE_QUERIES = {
    # Exact NASA IDs are used where possible so search ranking cannot silently
    # swap a spacecraft photo for an unrelated Mars landscape.
    "S01": "KSC-98pc1079",
    "S02": "mission control room",
    "S03": "KSC-98pc1079",
    "S04": "Mars planet",
    "S05": "mission control room",
    "S06": "Mars planet",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one or more Mars episode image assets safely.")
    parser.add_argument("--scene", choices=["ALL", *SCENE_PROMPTS], default="ALL")
    parser.add_argument("--output-dir", type=Path, default=ASSET_DIR)
    parser.add_argument("--provider", choices=["nasa", "cloudflare", "gemini"], default=os.environ.get("IMAGE_PROVIDER", "nasa"))
    parser.add_argument("--model", default=os.environ.get("IMAGE_MODEL", ""))
    parser.add_argument("--image-size", choices=["1K", "2K", "4K"], default=os.environ.get("GEMINI_IMAGE_SIZE", "1K"))
    parser.add_argument("--max-requests", type=int, default=int(os.environ.get("GEMINI_IMAGE_MAX_REQUESTS", "6")))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.provider == "nasa":
            provider = NASAImageProvider(
                quota_ledger=args.output_dir / "usage.json",
                max_requests_per_day=args.max_requests,
            )
        elif args.provider == "cloudflare":
            provider = CloudflareImageProvider(
                account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
                api_token=os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(),
                model=args.model or "@cf/stabilityai/stable-diffusion-xl-base-1.0",
                quota_ledger=args.output_dir / "usage.json",
                max_requests_per_day=args.max_requests,
            )
        else:
            provider = GeminiImageProvider(
                api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
                model=args.model or "gemini-nano-banana-2.1",
                quota_ledger=args.output_dir / "usage.json",
                max_requests_per_day=args.max_requests,
            )
        scenes = list(SCENE_PROMPTS) if args.scene == "ALL" else [args.scene]
        for scene_id in scenes:
            output = args.output_dir / f"{scene_id.lower()}-background.png"
            image_request = ImageRequest(
                scene_id=scene_id,
                prompt=SCENE_PROMPTS[scene_id],
                output_path=output,
                aspect_ratio="9:16",
                image_size=args.image_size,
                overwrite=args.overwrite,
            )
            if args.provider == "nasa":
                result = provider.generate(image_request, query=NASA_SCENE_QUERIES[scene_id])
            else:
                result = provider.generate(image_request)
            print(f"{scene_id}: {output} ({result['width']}x{result['height']}, {result['model']})")
    except ImageGenerationError as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
