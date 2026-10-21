#!/usr/bin/env python3
"""Render the Mars Short once the independent audio asset is present.

The script performs a real local render: narration is mixed above an original
procedural ambient bed, captions are burned from the approved ASS file, and
the visual motion draft is padded to the actual 58.36-second WAV duration.
It never touches another project or repository.
"""

from __future__ import annotations

import subprocess
import wave
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "mars-climate-orbiter-visual-draft-v2.mp4"
VOICE = ROOT / "mars-climate-orbiter-charon.wav"
CAPTIONS = ROOT / "mars-climate-orbiter-captions.ass"
MUSIC = ROOT / "mars-climate-orbiter-original-ambient.wav"
OUT = ROOT / "mars-climate-orbiter-final.mp4"
MANIFEST = ROOT / "mars-climate-orbiter-episode.json"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getnchannels() != 1:
            raise ValueError("Narration must be mono.")
        if wav_file.getframerate() <= 0 or wav_file.getnframes() <= 0:
            raise ValueError("Narration has invalid audio metadata.")
        return wav_file.getnframes() / wav_file.getframerate()


def build_music(duration: float) -> None:
    # Original, deliberately restrained procedural bed. It is not a stock
    # recording and remains well below the narration in the final mix.
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"anoisesrc=color=pink:amplitude=0.035:duration={duration},lowpass=f=850,highpass=f=45,afade=t=in:st=0:d=2,afade=t=out:st={max(0.0, duration - 3):.3f}:d=3",
        "-f", "lavfi", "-i",
        f"sine=frequency=55:sample_rate=24000:duration={duration},volume=0.018,afade=t=in:st=0:d=3,afade=t=out:st={max(0.0, duration - 4):.3f}:d=4",
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0,volume=0.42[a]",
        "-map", "[a]", "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(MUSIC),
    ])


def main() -> None:
    for required in (VIDEO, VOICE, CAPTIONS, MANIFEST):
        if not required.exists():
            raise FileNotFoundError(required)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("audio", {}).get("path") != VOICE.name:
        raise ValueError("Manifest audio path does not match the render input.")
    duration = audio_duration(VOICE)
    build_music(duration)
    captions_filter = f"subtitles={CAPTIONS.as_posix()}"
    filter_complex = (
        f"[0:v]tpad=stop_mode=clone:stop_duration=0.36,{captions_filter}[v];"
        "[1:a]volume=1.0[voice];"
        "[2:a]volume=0.22[music];"
        "[voice][music]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.93:level=disabled[a]"
    )
    run([
        "ffmpeg", "-y", "-i", str(VIDEO), "-i", str(VOICE), "-i", str(MUSIC),
        "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]",
        "-t", f"{duration:.3f}", "-r", "30", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(OUT),
    ])
    print(OUT)


if __name__ == "__main__":
    main()
