#!/usr/bin/env python3
"""Build a more intelligible Mars short from free factual stills.

The NASA stills remain the source of truth. This layer adds restrained,
scene-specific editorial graphics so the viewer can read trajectory drift,
unit mismatch, danger and signal loss without requiring generated imagery.
It creates a new output and never replaces the previous visual source.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DEFAULT_ASSETS = ROOT / "mars-assets"
DEFAULT_OUTPUT = ROOT / "mars-climate-orbiter-visual-editorial-v1.mp4"
WIDTH, HEIGHT, FPS = 1080, 1920, 30
SCENES = [("S01", 8), ("S02", 9), ("S03", 11), ("S04", 11), ("S05", 10), ("S06", 9)]

MOTION_PLAN = {
    "S01": (1.00, 1.06), "S02": (1.00, 1.02), "S03": (1.00, 1.05),
    "S04": (1.02, 1.09), "S05": (1.04, 1.01), "S06": (1.08, 1.00),
}

PALETTE = {"white": (245, 247, 250, 235), "cyan": (76, 196, 255, 235),
           "orange": (255, 158, 70, 240), "red": (247, 65, 65, 220),
           "navy": (7, 15, 29, 105)}


def font(size: int, bold: bool = False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(path, size)


def label(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], color, size=28):
    draw.text(xy, text, font=font(size, True), fill=color, stroke_width=1, stroke_fill=(0, 0, 0, 140))


def make_overlay(scene_id: str, path: Path) -> None:
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Consistent editorial locator, deliberately small and away from captions.
    draw.rounded_rectangle((64, 74, 360, 132), radius=15, fill=(5, 12, 24, 180), outline=(255, 255, 255, 90), width=2)
    labels = {"S01": "ARRIVAL / 1999", "S02": "UNIT MISMATCH", "S03": "PATH DEVIATION",
              "S04": "DANGEROUS APPROACH", "S05": "WARNING SIGNS", "S06": "SIGNAL LOST"}
    label(draw, labels[scene_id], (86, 88), PALETTE["white"], 23)

    if scene_id == "S02":
        # A compact, factual visual explanation of the two unit systems.
        draw.rounded_rectangle((95, 270, 985, 560), radius=28, fill=(4, 12, 26, 190), outline=(255, 255, 255, 90), width=3)
        label(draw, "GROUND SOFTWARE", (145, 318), PALETTE["orange"], 24)
        label(draw, "lb·s", (145, 365), PALETTE["orange"], 72)
        draw.line((450, 415, 630, 415), fill=PALETTE["white"], width=5)
        draw.polygon([(630, 415), (600, 397), (600, 433)], fill=PALETTE["white"])
        label(draw, "NAVIGATION", (670, 318), PALETTE["cyan"], 24)
        label(draw, "N·s", (670, 365), PALETTE["cyan"], 72)
        label(draw, "same signal / different scale", (260, 500), PALETTE["white"], 24)
    elif scene_id == "S03":
        # Two paths make the abstract “drift” visible over the spacecraft still.
        draw.arc((60, 430, 1010, 1350), 205, 342, fill=PALETTE["cyan"], width=8)
        draw.arc((60, 430, 1010, 1350), 222, 359, fill=PALETTE["orange"], width=8)
        draw.ellipse((850, 690, 882, 722), fill=PALETTE["cyan"])
        draw.ellipse((772, 830, 804, 862), fill=PALETTE["orange"])
        label(draw, "CALCULATED", (92, 1435), PALETTE["cyan"], 23)
        label(draw, "ACTUAL", (92, 1480), PALETTE["orange"], 23)
    elif scene_id == "S04":
        # Red approach corridor and a small craft marker clarify the danger.
        draw.arc((110, 690, 1030, 1640), 205, 330, fill=PALETTE["red"], width=13)
        draw.line((760, 460, 675, 760), fill=PALETTE["white"], width=5)
        draw.ellipse((743, 430, 777, 464), fill=PALETTE["white"])
        label(draw, "TOO LOW", (784, 430), PALETTE["red"], 24)
    elif scene_id == "S05":
        # Warning glow, not a fake screen or invented telemetry.
        for box, alpha in [((780, 280, 1010, 510), 24), ((820, 320, 970, 470), 42), ((860, 360, 930, 430), 180)]:
            draw.ellipse(box, fill=(247, 65, 65, alpha))
        draw.rounded_rectangle((720, 245, 1010, 545), radius=30, outline=(247, 65, 65, 170), width=5)
        label(draw, "NO CONFIRMATION", (730, 575), PALETTE["red"], 23)
    elif scene_id == "S06":
        # Fading radio rings communicate disappearance without claiming a real signal plot.
        center = (820, 560)
        for radius, alpha in [(55, 210), (120, 145), (190, 80)]:
            draw.arc((center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius), 210, 330,
                     fill=(76, 196, 255, alpha), width=7)
        draw.ellipse((805, 545, 835, 575), fill=PALETTE["white"])
        draw.line((820, 590, 700, 820), fill=(76, 196, 255, 125), width=4)
        label(draw, "CONTACT FADES", (650, 850), PALETTE["cyan"], 23)

    layer.save(path, format="PNG", optimize=True)


def motion_filter(scene_id: str, duration: int) -> str:
    start, end = MOTION_PLAN[scene_id]
    frames = max(2, duration * FPS)
    progress = f"min(1,max(0,on/{frames - 1}))"
    eased = f"({progress}*{progress}*(3-2*{progress}))"
    zoom = f"{start}+({end-start})*{eased}"
    return (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    assets, output = args.assets.resolve(), args.output.resolve()
    with tempfile.TemporaryDirectory(prefix="mars-editorial-") as temp_dir:
        temp = Path(temp_dir)
        clips = []
        for scene_id, duration in SCENES:
            source = assets / f"{scene_id.lower()}-background.png"
            sidecar = source.with_suffix(source.suffix + ".json")
            if not source.is_file() or not sidecar.is_file():
                print(f"Missing approved source or provenance: {scene_id}")
                return 2
            overlay = temp / f"{scene_id.lower()}-overlay.png"
            clip = temp / f"{scene_id.lower()}.mp4"
            make_overlay(scene_id, overlay)
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", str(source), "-loop", "1", "-i", str(overlay),
                "-t", str(duration), "-filter_complex", f"[0:v]{motion_filter(scene_id, duration)}[base];[1:v]format=rgba[ov];[base][ov]overlay=0:0:shortest=1,format=yuv420p[v]",
                "-map", "[v]", "-frames:v", str(duration * FPS), "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(clip),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            clips.append(clip)
        concat = temp / "concat.txt"
        concat.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in clips) + "\n", encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(output)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    output.with_suffix(output.suffix + ".json").write_text(json.dumps({
        "schema_version": "1.0", "source": "NASA public stills + independent editorial graphics",
        "editor_profile": "senior-editor-v2-editorial-clarity", "scene_count": 6,
        "overlays": {"S02": "unit-system comparison", "S03": "calculated-vs-actual path",
                     "S04": "danger corridor", "S05": "warning glow", "S06": "fading signal"},
        "transitions": "hard cuts; no decorative transitions", "output": str(output)
    }, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
