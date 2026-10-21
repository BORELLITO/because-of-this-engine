#!/usr/bin/env python3
"""Render one manifest-defined BECAUSE OF THIS episode safely."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, timeout=900)


def resolve_inside(manifest_dir: Path, relative: str, project_root: Path) -> Path:
    path = (manifest_dir / relative).resolve()
    if project_root not in path.parents and path != project_root:
        raise ValueError(f"Manifest path escapes independent project root: {relative}")
    return path


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
            raise ValueError("Narration must be mono 16-bit PCM.")
        if wav_file.getframerate() != 24000 or wav_file.getnframes() <= 0:
            raise ValueError("Narration must be a non-empty 24 kHz WAV.")
        return wav_file.getnframes() / wav_file.getframerate()


def build_music(duration: float, target: Path) -> None:
    """Build a deterministic original bed and write it only to a temp target."""
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"anoisesrc=color=pink:seed=20261021:amplitude=0.035:duration={duration},lowpass=f=850,highpass=f=45,afade=t=in:st=0:d=2,afade=t=out:st={max(0.0, duration - 3):.3f}:d=3",
        "-f", "lavfi", "-i",
        f"sine=frequency=55:sample_rate=24000:duration={duration},volume=0.018,afade=t=in:st=0:d=3,afade=t=out:st={max(0.0, duration - 4):.3f}:d=4",
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0,volume=0.42[a]",
        "-map", "[a]", "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(target),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one manifest-defined episode safely.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "mars-climate-orbiter-episode.json")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest_dir = manifest_path.parent
    project_root = manifest_dir.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    video = resolve_inside(manifest_dir, manifest["visual"]["source_motion"], project_root)
    voice = resolve_inside(manifest_dir, manifest["audio"]["path"], project_root)
    captions = resolve_inside(manifest_dir, manifest["captions"]["path"], project_root)
    music = resolve_inside(manifest_dir, manifest["mix"]["music_path"], project_root)
    output = resolve_inside(manifest_dir, manifest["output"]["path"], project_root)
    for required in (video, voice, captions):
        if not required.is_file():
            raise FileNotFoundError(required)

    duration = audio_duration(voice)
    music_tmp = music.with_name(f".{music.name}.part.wav")
    output_tmp = output.with_name(f".{output.name}.part.mp4")
    for temp in (music_tmp, output_tmp):
        try:
            temp.unlink()
        except FileNotFoundError:
            pass

    try:
        build_music(duration, music_tmp)
        captions_filter = f"subtitles={captions.as_posix()}"
        filter_complex = (
            f"[0:v]tpad=stop_mode=clone:stop_duration=0.36,{captions_filter}[v];"
            "[1:a]volume=1.0[voice];"
            "[2:a]volume=0.22[music];"
            "[voice][music]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.93:level=disabled[a]"
        )
        run([
            "ffmpeg", "-y", "-i", str(video), "-i", str(voice), "-i", str(music_tmp),
            "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]",
            "-t", f"{duration:.3f}", "-r", "30", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(output_tmp),
        ])
        os.replace(music_tmp, music)
        os.replace(output_tmp, output)
    finally:
        for temp in (music_tmp, output_tmp):
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
    print(output)


if __name__ == "__main__":
    main()
