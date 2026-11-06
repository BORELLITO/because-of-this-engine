#!/usr/bin/env python3
"""Create the locked black stacked Because Of This Stories outro card."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not Path(FONT_PATH).is_file():
        raise SystemExit(f"Required font is missing: {FONT_PATH}")

    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, 170)
    for text, y in zip(("BECAUSE", "OF", "THIS", "STORIES"), (390, 600, 810, 1020)):
        box = draw.textbbox((0, 0), text, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
