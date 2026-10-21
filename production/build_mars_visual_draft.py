#!/usr/bin/env python3
"""Build a silent vertical visual draft for the Mars Climate Orbiter Short.

This is an isolated asset builder for BECAUSE OF THIS. It does not touch any
other channel engine or repository. The generated frames are intentionally
text-free; narration and captions are added after the approved audio is
available.
"""

from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
OUT = ROOT / "mars-climate-orbiter-visual-draft.mp4"
WIDTH, HEIGHT = 1080, 1920
FPS = 30

SCENES = [
    ("01-trajectory", 8, "trajectory"),
    ("02-units", 9, "units"),
    ("03-navigation", 11, "navigation"),
    ("04-approach", 11, "approach"),
    ("05-signal-loss", 10, "signal"),
    ("06-consequence", 9, "consequence"),
]


def glow_circle(base: Image.Image, xy: tuple[int, int], radius: int, color: tuple[int, int, int], alpha: int = 180) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = xy
    for step in range(7, 0, -1):
        r = radius + step * 25
        a = max(1, alpha // (8 - step))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, a))
    layer = layer.filter(ImageFilter.GaussianBlur(16))
    base.alpha_composite(layer)
    draw = ImageDraw.Draw(base)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, 255))


def stars(draw: ImageDraw.ImageDraw, seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(180):
        x = rng.randrange(WIDTH)
        y = rng.randrange(HEIGHT)
        size = rng.choice([1, 1, 1, 2, 3])
        shade = rng.choice([(150, 170, 200), (220, 225, 235), (110, 130, 170)])
        draw.ellipse((x, y, x + size, y + size), fill=shade)


def base_frame(seed: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (5, 8, 18, 255))
    px = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            t = y / HEIGHT
            r = int(5 + 8 * t)
            g = int(8 + 9 * t)
            b = int(18 + 20 * t)
            px[x, y] = (r, g, b, 255)
    draw = ImageDraw.Draw(image)
    stars(draw, seed)
    return image


def spacecraft(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float = 1.0) -> None:
    cx, cy = center
    body = [
        (cx - int(65 * scale), cy - int(35 * scale)),
        (cx + int(65 * scale), cy - int(35 * scale)),
        (cx + int(82 * scale), cy + int(28 * scale)),
        (cx - int(82 * scale), cy + int(28 * scale)),
    ]
    draw.polygon(body, fill=(178, 188, 202), outline=(245, 184, 75), width=max(1, int(3 * scale)))
    draw.rectangle((cx - int(30 * scale), cy - int(58 * scale), cx + int(30 * scale), cy - int(35 * scale)), fill=(40, 62, 88))
    draw.line((cx - int(80 * scale), cy, cx - int(190 * scale), cy - int(30 * scale)), fill=(224, 132, 54), width=max(2, int(4 * scale)))
    draw.line((cx + int(80 * scale), cy, cx + int(190 * scale), cy - int(30 * scale)), fill=(224, 132, 54), width=max(2, int(4 * scale)))
    draw.rectangle((cx - int(190 * scale), cy - int(55 * scale), cx - int(130 * scale), cy - int(5 * scale)), fill=(28, 65, 100), outline=(130, 170, 200), width=max(1, int(2 * scale)))
    draw.rectangle((cx + int(130 * scale), cy - int(55 * scale), cx + int(190 * scale), cy - int(5 * scale)), fill=(28, 65, 100), outline=(130, 170, 200), width=max(1, int(2 * scale)))


def render_scene(kind: str, seed: int) -> Image.Image:
    image = base_frame(seed)
    draw = ImageDraw.Draw(image)

    if kind == "trajectory":
        glow_circle(image, (220, 620), 100, (75, 145, 224), 160)
        glow_circle(image, (850, 1160), 260, (176, 56, 28), 180)
        draw = ImageDraw.Draw(image)
        draw.arc((120, 560, 960, 1380), 205, 335, fill=(220, 138, 62), width=5)
        spacecraft(draw, (500, 850), 0.9)
        draw.line((300, 745, 710, 1060), fill=(242, 187, 75), width=3)
    elif kind == "units":
        draw.rounded_rectangle((100, 550, 980, 920), radius=30, fill=(14, 24, 42), outline=(224, 132, 54), width=5)
        draw.rounded_rectangle((100, 1000, 980, 1370), radius=30, fill=(14, 24, 42), outline=(80, 150, 220), width=5)
        draw.line((540, 920, 540, 1000), fill=(235, 174, 70), width=8)
        draw.line((520, 950, 560, 950), fill=(235, 174, 70), width=8)
        # abstract unit symbols, not factual UI
        draw.text((250, 680), "lb·s", fill=(245, 195, 105), anchor="mm")
        draw.text((810, 680), "GROUND", fill=(178, 188, 202), anchor="mm")
        draw.text((250, 1130), "N·s", fill=(105, 184, 240), anchor="mm")
        draw.text((810, 1130), "NAVIGATION", fill=(178, 188, 202), anchor="mm")
    elif kind == "navigation":
        draw.rounded_rectangle((80, 390, 1000, 1460), radius=30, fill=(8, 15, 30), outline=(50, 88, 128), width=4)
        for x in range(150, 980, 110):
            draw.line((x, 500, x, 1360), fill=(20, 45, 70), width=2)
        for y in range(520, 1400, 110):
            draw.line((120, y, 960, y), fill=(20, 45, 70), width=2)
        points = [(140, 1250), (300, 1170), (420, 1120), (560, 990), (700, 850), (850, 710), (940, 550)]
        draw.line(points, fill=(90, 192, 234), width=8)
        draw.line([(140, 1250), (300, 1190), (420, 1205), (560, 1140), (700, 980), (850, 890), (940, 1020)], fill=(224, 132, 54), width=7)
        draw.ellipse((810, 820, 870, 880), fill=(224, 70, 54))
    elif kind == "approach":
        glow_circle(image, (540, 1150), 430, (165, 48, 24), 210)
        draw = ImageDraw.Draw(image)
        draw.arc((30, 640, 1050, 1680), 190, 350, fill=(234, 151, 66), width=7)
        spacecraft(draw, (560, 590), 0.65)
        draw.line((560, 680, 540, 820), fill=(234, 151, 66), width=5)
    elif kind == "signal":
        spacecraft(draw, (540, 710), 0.55)
        for i in range(4):
            draw.arc((260 - i * 18, 430 - i * 18, 820 + i * 36, 990 + i * 36), 210, 330, fill=(90, 192, 234), width=5)
        draw.line((140, 1330, 940, 1330), fill=(80, 100, 130), width=5)
        for x in (250, 440, 630, 820):
            draw.line((x, 1310, x, 1350), fill=(80, 100, 130), width=5)
        draw.line((140, 1330, 580, 1330), fill=(224, 132, 54), width=7)
    elif kind == "consequence":
        glow_circle(image, (540, 920), 300, (178, 56, 28), 180)
        draw = ImageDraw.Draw(image)
        draw.arc((150, 520, 930, 1320), 190, 350, fill=(230, 160, 70), width=6)
        spacecraft(draw, (540, 460), 0.45)
        draw.line((540, 560, 540, 760), fill=(224, 132, 54), width=7)
        # Keep the consequence frame clean. The causal lesson is carried by
        # the narration and caption layer; an empty card would add noise.
    return image.convert("RGB")


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for index, (_name, _duration, kind) in enumerate(SCENES, start=1):
        frame_path = FRAMES / f"scene-{index:02d}.png"
        render_scene(kind, 100 + index).save(frame_path, quality=95)

    # Build a silent edit with gentle crossfades. The voice is added later.
    concat = FRAMES / "concat.txt"
    with concat.open("w", encoding="utf-8") as handle:
        for name, duration, _kind in SCENES:
            handle.write(f"file '{(FRAMES / ('scene-' + name[:2] + '.png')).as_posix()}'\n")
            handle.write(f"duration {duration}\n")
        handle.write(f"file '{(FRAMES / 'scene-06.png').as_posix()}'\n")

    # Correct concat paths (scene names above are semantic labels).
    concat_lines = []
    for index, (_name, duration, _kind) in enumerate(SCENES, start=1):
        concat_lines.extend([f"file '{(FRAMES / f'scene-{index:02d}.png').as_posix()}'", f"duration {duration}"])
    concat_lines.append(f"file '{(FRAMES / 'scene-06.png').as_posix()}'")
    concat.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-t", str(sum(duration for _name, duration, _kind in SCENES)),
        "-vf", f"scale={WIDTH}:{HEIGHT},format=yuv420p", "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(OUT),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(OUT)


if __name__ == "__main__":
    main()
