#!/usr/bin/env python3
"""Render a small reference-adapted BECAUSE OF THIS preview.

This is an independent profile. It borrows the reference video's editorial
grammar (one idea per card, stable composition, hard cuts, top story card)
without copying its assets, wording, music or branding. The default motion is
static; movement can be introduced later only when the narration requires it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT, FPS = 1080, 1920, 30
ROOT = Path(__file__).resolve().parent
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def centered_lines(draw: ImageDraw.ImageDraw, lines: list[str], box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    sizes = [42 if len(lines) == 1 else 38] * len(lines)
    heights = [draw.textbbox((0, 0), line, font=font(size))[3] for line, size in zip(lines, sizes)]
    gap = 8
    total = sum(heights) + gap * (len(lines) - 1)
    y = top + (bottom - top - total) // 2
    for line, size, height in zip(lines, sizes, heights):
        width = draw.textbbox((0, 0), line, font=font(size))[2]
        draw.text(((left + right - width) // 2, y), line, font=font(size), fill=(10, 15, 22, 255))
        y += height + gap


def make_card(source: Path, title: list[str], output: Path) -> None:
    image = Image.open(source).convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    # A restrained vignette keeps the visual legible while preserving the
    # factual source image. It is not a fake depth effect or generated object.
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, WIDTH, 330), fill=(3, 9, 18, 75))
    draw.rectangle((0, HEIGHT - 430, WIDTH, HEIGHT), fill=(3, 9, 18, 80))

    card = (110, 160, 970, 345)
    draw.rounded_rectangle(card, radius=28, fill=(248, 249, 251, 238), outline=(12, 19, 28, 160), width=3)
    centered_lines(draw, title, card)

    # Small channel marker is deliberately generic and independent of the
    # other projects' identities.
    marker = "BECAUSE OF THIS"
    marker_font = font(24)
    draw.text((72, 72), marker, font=marker_font, fill=(246, 179, 71, 245), stroke_width=1, stroke_fill=(0, 0, 0, 160))

    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    image.save(output, format="PNG", optimize=True)


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def build_ambient(path: Path, duration: float) -> None:
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"anoisesrc=color=pink:amplitude=0.025:duration={duration},lowpass=f=850,highpass=f=45,afade=t=in:st=0:d=1,afade=t=out:st={max(0.0, duration-1.5):.3f}:d=1.5",
        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(path),
    ])


def render(args: argparse.Namespace) -> Path:
    assets = args.assets.resolve()
    voice = args.voice.resolve()
    out = args.output.resolve()
    duration = min(args.duration, audio_duration(voice))
    scene_boundary = min(4.5, duration)
    scene_plan = [("S01", 0.0, scene_boundary), ("S02", scene_boundary, duration)]

    with tempfile.TemporaryDirectory(prefix="because-reference-preview-") as tmp:
        temp = Path(tmp)
        clips: list[Path] = []
        labels = {
            "S01": ["NINE MONTHS", "TO REACH MARS"],
            "S02": ["ONE MISMATCH", "CHANGED THE PATH"],
        }
        for scene_id, start, end in scene_plan:
            seconds = max(0.1, end - start)
            source = assets / f"{scene_id.lower()}-background.png"
            sidecar = source.with_suffix(source.suffix + ".json")
            if not source.is_file() or not sidecar.is_file():
                raise FileNotFoundError(f"Missing source/provenance for {scene_id}")
            card = temp / f"{scene_id.lower()}-card.png"
            clip = temp / f"{scene_id.lower()}.mp4"
            make_card(source, labels[scene_id], card)
            run([
                "ffmpeg", "-y", "-loop", "1", "-i", str(card), "-t", f"{seconds:.3f}",
                "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-pix_fmt", "yuv420p", str(clip),
            ])
            clips.append(clip)

        concat = temp / "concat.txt"
        concat.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in clips) + "\n", encoding="utf-8")
        visual = temp / "visual.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visual)])

        ambient = temp / "ambient.wav"
        build_ambient(ambient, duration)
        subtitle_path = ROOT / "mars-climate-orbiter-captions.ass"
        filter_complex = (
            f"[0:v]subtitles={subtitle_path.as_posix()}[v];"
            "[1:a]volume=1.0[voice];[2:a]volume=0.16[bed];"
            "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.93[a]"
        )
        run([
            "ffmpeg", "-y", "-i", str(visual), "-i", str(voice), "-i", str(ambient),
            "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]",
            "-t", f"{duration:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(out),
        ])

    manifest = {
        "profile": "reference_adapted_v1",
        "reference_principles": ["one idea per card", "stable composition", "top story card", "hard cut"],
        "motion": "static by default; no shake; no automatic zoom",
        "transition": "hard cut at semantic scene boundary (4.5s)",
        "caption_policy": "existing BECAUSE OF THIS phrase-level captions in lower safe zone",
        "originality_lock": True,
        "protected_engines": ["Capta Pronto", "Corte Fino", "Publisher", "Creator"],
        "output": str(out),
    }
    out.with_suffix(out.suffix + ".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--voice", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "mars-reference-adapted-preview-v1.mp4")
    parser.add_argument("--duration", type=float, default=9.0)
    args = parser.parse_args()
    print(render(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

