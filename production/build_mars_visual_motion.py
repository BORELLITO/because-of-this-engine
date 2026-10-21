#!/usr/bin/env python3
"""Build the independent Mars visual timing draft with restrained motion.

This deliberately creates a silent editorial motion pass. It does not claim
audio sync and does not modify any other project or engine.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
SEGMENTS = ROOT / "motion_segments_v4"
OUT = ROOT / "mars-climate-orbiter-visual-draft-v4.mp4"
WIDTH, HEIGHT, FPS = 1080, 1920, 30

# Scene duration, zoom expression, and crop direction. The expressions are
# intentionally gentle; the story, not the filter, should carry the suspense.
SCENES = [
    ("scene-01.png", 8, "min(zoom+0.00070,1.06)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("scene-02.png", 9, "1.0+0.015*on/269", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("scene-03.png", 11, "min(zoom+0.00045,1.05)", "iw/2-(iw/zoom/2)+18*on/329", "ih/2-(ih/zoom/2)"),
    ("scene-04.png", 11, "min(zoom+0.00075,1.09)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)+26*on/329"),
    ("scene-05.png", 10, "1.04-0.03*on/299", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("scene-06.png", 9, "1.08-0.08*on/269", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    segment_paths: list[Path] = []
    for index, (filename, seconds, zoom, x, y) in enumerate(SCENES, start=1):
        source = FRAMES / filename
        segment = SEGMENTS / f"segment-{index:02d}.mp4"
        frames = seconds * FPS
        if index == 4:
            # Keep the high-detail approach frame stable. This avoids an
            # FFmpeg zoompan parser failure on the dense Mars atmosphere
            # frame while preserving the intended visual beat.
            vf = f"scale={WIDTH}:{HEIGHT},format=yuv420p"
            run([
                "ffmpeg", "-y", "-loop", "1", "-i", str(source),
                "-vf", vf, "-t", str(seconds), "-r", str(FPS), "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", str(segment),
            ])
        else:
            vf = (
                f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:"
                f"s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p"
            )
            run([
                "ffmpeg", "-y", "-loop", "1", "-i", str(source),
                "-vf", vf, "-frames:v", str(frames), "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", str(segment),
            ])
        segment_paths.append(segment)

    concat = SEGMENTS / "concat.txt"
    concat.write_text("\n".join(f"file '{path.as_posix()}'" for path in segment_paths) + "\n", encoding="utf-8")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", "-movflags", "+faststart", str(OUT),
    ])
    print(OUT)


if __name__ == "__main__":
    main()

