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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
OUT = ROOT / "mars-climate-orbiter-visual-draft.mp4"
WIDTH, HEIGHT = 1080, 1920
FPS = 30
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

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


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD_PATH if bold else FONT_REGULAR_PATH, size)


def text_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill: tuple[int, int, int], bold: bool = True) -> None:
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor="mm")


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: tuple[int, int, int], width: int = 7) -> None:
    draw.line((*start, *end), fill=fill, width=width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 24
    tip = end
    left = (int(end[0] - ux * size + px * size * 0.55), int(end[1] - uy * size + py * size * 0.55))
    right = (int(end[0] - ux * size - px * size * 0.55), int(end[1] - uy * size - py * size * 0.55))
    draw.polygon([tip, left, right], fill=fill)


def mars(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, glow: bool = True) -> None:
    if glow:
        # The glow is intentionally restrained: it reads as atmosphere, not an explosion.
        pass
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(178, 56, 28), outline=(230, 130, 60), width=5)
    draw.arc((cx - radius + 22, cy - radius + 12, cx + radius - 22, cy + radius - 12), 205, 330, fill=(228, 142, 74), width=5)


def earth(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int) -> None:
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(46, 113, 177), outline=(135, 207, 240), width=5)
    draw.arc((cx - radius + 12, cy - radius + 20, cx + radius - 12, cy + radius - 10), 20, 175, fill=(116, 188, 127), width=12)


def antenna(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float = 1.0) -> None:
    cx, cy = center
    draw.arc((cx - int(75 * scale), cy - int(75 * scale), cx + int(75 * scale), cy + int(75 * scale)), 200, 340, fill=(178, 188, 202), width=max(3, int(6 * scale)))
    draw.line((cx, cy + int(15 * scale), cx, cy + int(105 * scale)), fill=(178, 188, 202), width=max(3, int(6 * scale)))
    draw.line((cx - int(44 * scale), cy + int(105 * scale), cx + int(44 * scale), cy + int(105 * scale)), fill=(178, 188, 202), width=max(3, int(6 * scale)))


def render_scene(kind: str, seed: int) -> Image.Image:
    image = base_frame(seed)
    draw = ImageDraw.Draw(image)

    if kind == "trajectory":
        # The hook must show the actual relationship: Earth -> spacecraft -> Mars.
        glow_circle(image, (155, 610), 125, (45, 110, 190), 130)
        glow_circle(image, (850, 1180), 285, (176, 56, 28), 155)
        earth(draw, (155, 610), 105)
        mars(draw, (850, 1180), 285)
        spacecraft(draw, (495, 850), 0.78)
        arrow(draw, (265, 680), (420, 810), (242, 187, 75), 6)
        # Communication line disappears at the hook's payoff.
        draw.line((265, 570, 410, 650), fill=(90, 192, 234), width=5)
        draw.line((410, 650, 540, 730), fill=(90, 192, 234), width=5)
        draw.line((540, 730, 650, 800), fill=(90, 192, 234), width=5)
        draw.line((650, 800, 735, 875), fill=(90, 192, 234), width=5)
        draw.line((735, 875, 705, 850), fill=(224, 70, 54), width=8)
        draw.line((705, 820, 735, 850), fill=(224, 70, 54), width=8)
        draw.line((735, 820, 705, 850), fill=(224, 70, 54), width=8)
    elif kind == "units":
        # Make the mismatch legible without pretending to show a NASA screen.
        draw.rounded_rectangle((80, 420, 1000, 840), radius=34, fill=(28, 22, 24), outline=(224, 132, 54), width=6)
        draw.rounded_rectangle((80, 1040, 1000, 1460), radius=34, fill=(15, 27, 45), outline=(80, 150, 220), width=6)
        text_center(draw, (540, 535), "GROUND SOFTWARE", 42, (245, 195, 105))
        text_center(draw, (540, 675), "POUND-SECONDS", 58, (250, 220, 160))
        text_center(draw, (540, 1155), "NAVIGATION", 42, (125, 201, 245))
        text_center(draw, (540, 1295), "NEWTON-SECONDS", 58, (160, 220, 250))
        draw.line((540, 840, 540, 1040), fill=(235, 174, 70), width=8)
        draw.line((500, 930, 580, 930), fill=(235, 174, 70), width=8)
        draw.line((540, 910, 540, 950), fill=(235, 174, 70), width=8)
    elif kind == "navigation":
        draw.rounded_rectangle((70, 330, 1010, 1470), radius=34, fill=(8, 15, 30), outline=(50, 88, 128), width=4)
        for x in range(150, 980, 110):
            draw.line((x, 470, x, 1350), fill=(20, 45, 70), width=2)
        for y in range(500, 1400, 110):
            draw.line((120, y, 960, y), fill=(20, 45, 70), width=2)
        start = (150, 1270)
        intended = [(150, 1270), (310, 1190), (455, 1120), (600, 950), (750, 760), (910, 535)]
        actual = [(150, 1270), (310, 1210), (455, 1230), (600, 1180), (750, 1040), (900, 1145)]
        draw.line(intended, fill=(90, 192, 234), width=8)
        draw.line(actual, fill=(224, 132, 54), width=8)
        draw.ellipse((870, 1115, 930, 1175), fill=(224, 70, 54))
        text_center(draw, (350, 420), "EXPECTED PATH", 30, (120, 205, 245))
        text_center(draw, (730, 1335), "REAL PATH", 30, (245, 170, 95))
    elif kind == "approach":
        glow_circle(image, (540, 1250), 430, (165, 48, 24), 190)
        mars(draw, (540, 1250), 430)
        # A narrow, visibly dangerous corridor makes "too close" concrete.
        draw.arc((55, 780, 1025, 1740), 205, 335, fill=(234, 151, 66), width=8)
        draw.arc((160, 850, 920, 1610), 205, 335, fill=(224, 70, 54), width=6)
        spacecraft(draw, (540, 580), 0.62)
        arrow(draw, (540, 690), (540, 875), (234, 151, 66), 7)
    elif kind == "signal":
        antenna(draw, (190, 1080), 1.0)
        spacecraft(draw, (800, 650), 0.52)
        # Broken link + unresolved warning markers, rather than a generic radio arc.
        draw.line((300, 980, 510, 850), fill=(90, 192, 234), width=6)
        draw.line((510, 850, 620, 790), fill=(224, 70, 54), width=6)
        draw.line((620, 790, 680, 755), fill=(224, 70, 54), width=6)
        for x, y in ((380, 720), (505, 640), (635, 560)):
            draw.ellipse((x - 22, y - 22, x + 22, y + 22), outline=(238, 175, 75), width=6)
            draw.line((x - 12, y - 12, x + 12, y + 12), fill=(238, 175, 75), width=5)
            draw.line((x + 12, y - 12, x - 12, y + 12), fill=(238, 175, 75), width=5)
    elif kind == "consequence":
        glow_circle(image, (540, 1100), 315, (178, 56, 28), 170)
        mars(draw, (540, 1100), 315)
        spacecraft(draw, (540, 520), 0.45)
        draw.line((540, 600, 540, 820), fill=(224, 132, 54), width=7)
        draw.line((510, 760, 570, 820), fill=(224, 70, 54), width=7)
        draw.line((570, 760, 510, 820), fill=(224, 70, 54), width=7)
    return image.convert("RGB")


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for index, (_name, _duration, kind) in enumerate(SCENES, start=1):
        frame_path = FRAMES / f"scene-{index:02d}.png"
        render_scene(kind, 100 + index).save(frame_path, quality=95)

    # Build a single canonical concat file; the voice and captions are added later.
    concat = FRAMES / "concat.txt"
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

