#!/usr/bin/env python3
"""Create the branded outro card that fades from channel texture to black."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

WIDTH = 1080
HEIGHT = 1920
LOGO_WIDTH = 620


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--background", type=Path, required=True)
    parser.add_argument("--logo", type=Path, required=True)
    args = parser.parse_args()

    if not args.background.is_file():
        raise SystemExit(f"Outro background is missing: {args.background}")
    if not args.logo.is_file():
        raise SystemExit(f"Transparent wordmark is missing: {args.logo}")

    background = Image.open(args.background).convert("RGB")
    scale = max(WIDTH / background.width, HEIGHT / background.height)
    background = background.resize(
        (round(background.width * scale), round(background.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (background.width - WIDTH) // 2
    top = (background.height - HEIGHT) // 2
    background = background.crop((left, top, left + WIDTH, top + HEIGHT))
    background = ImageEnhance.Brightness(background).enhance(0.32).filter(ImageFilter.GaussianBlur(1.8))
    image = background.convert("RGBA")

    # Preserve the recognizable banner texture without letting its title compete
    # with the final channel lockup.
    image.alpha_composite(Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 122)))
    cover = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    cover_draw = ImageDraw.Draw(cover)
    cover_draw.rectangle((0, 0, WIDTH, 300), fill=(0, 0, 0, 255))
    cover_draw.rectangle((0, 1130, WIDTH, HEIGHT), fill=(0, 0, 0, 255))
    image.alpha_composite(cover)
    gradient = Image.new("RGBA", (1, HEIGHT))
    pixels = gradient.load()
    for y in range(HEIGHT):
        alpha = round(55 + 170 * (y / HEIGHT) ** 1.7)
        pixels[0, y] = (0, 0, 0, alpha)
    image.alpha_composite(gradient.resize((WIDTH, HEIGHT)))

    wordmark = Image.open(args.logo).convert("RGBA")
    scale = LOGO_WIDTH / wordmark.width
    wordmark = wordmark.resize(
        (LOGO_WIDTH, round(wordmark.height * scale)), Image.Resampling.LANCZOS
    )
    x = (WIDTH - wordmark.width) // 2
    y = (HEIGHT - wordmark.height) // 2 - 20
    image.alpha_composite(wordmark, (x, y))

    # A restrained red pulse anchors the established channel palette.
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse(
        (WIDTH // 2 - 260, HEIGHT // 2 - 240, WIDTH // 2 + 260, HEIGHT // 2 + 240),
        fill=(190, 20, 28, 22),
    )
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(65)))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
