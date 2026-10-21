#!/usr/bin/env python3
"""Assemble approved Nano Banana stills into a silent vertical motion source.

This stage intentionally refuses to invent substitute art. Every scene must
have a generated asset with a provenance sidecar before it can enter the edit.
Captions are added by the existing independent render stage.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_ASSETS = ROOT / "mars-assets"
DEFAULT_OUTPUT = ROOT / "mars-climate-orbiter-visual-ai-v1.mp4"
WIDTH, HEIGHT, FPS = 1080, 1920, 30
SCENES = [("S01", 8), ("S02", 9), ("S03", 11), ("S04", 11), ("S05", 10), ("S06", 9)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a motion source from approved generated Mars scene assets.")
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    assets = args.assets.resolve()
    output = args.output.resolve()

    missing: list[str] = []
    for scene_id, _duration in SCENES:
        image = assets / f"{scene_id.lower()}-background.png"
        sidecar = image.with_suffix(image.suffix + ".json")
        if not image.exists() or not sidecar.exists():
            missing.append(scene_id)
    if missing:
        print(f"Refusing to build: missing approved assets or sidecars for {', '.join(missing)}")
        print("Run generate_mars_images.py and review every scene before assembling the MP4.")
        return 2

    with tempfile.TemporaryDirectory(prefix="mars-ai-motion-") as temp_dir:
        temp = Path(temp_dir)
        clips: list[Path] = []
        for scene_id, duration in SCENES:
            source = assets / f"{scene_id.lower()}-background.png"
            clip = temp / f"{scene_id.lower()}.mp4"
            # A restrained push-in creates motion without changing the story.
            vf = (
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT},format=yuv420p"
            )
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(source), "-t", str(duration),
                    "-vf", vf, "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", str(clip),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            clips.append(clip)

        concat = temp / "concat.txt"
        concat.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in clips) + "\n", encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    provenance = {
        "schema_version": "1.0",
        "source": "approved Gemini Nano Banana scene assets",
        "assets_dir": str(assets),
        "scene_count": len(SCENES),
        "scenes": [scene_id for scene_id, _duration in SCENES],
        "output": str(output),
    }
    output.with_suffix(output.suffix + ".json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
