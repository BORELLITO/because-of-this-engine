#!/usr/bin/env python3
"""Render a generic authorial Because of This episode with FFmpeg.

The renderer is independent from the other engines. It consumes a manifest,
renders a low-cost preview or a final vertical export, and fails closed when
inputs are missing or unsafe.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

FPS = 25
TRANSITION_DEFAULT = 0.33
SIZES = {
    "preview": (1080, 1920),
    "final": (2160, 3840),
}


class RenderError(ValueError):
    """Raised when the render contract is invalid."""


def run(command: list[str], timeout: int = 900) -> None:
    subprocess.run(command, check=True, timeout=timeout)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise RenderError("Manifest must be a JSON object.")
    return value


def resolve_inside(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise RenderError("Manifest paths must be non-empty strings.")
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise RenderError(f"Path escapes the episode directory: {relative}")
    return candidate


def audio_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav_file:
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise RenderError("Narration must be mono 16-bit PCM WAV.")
            if wav_file.getframerate() != 24000 or wav_file.getnframes() <= 0:
                raise RenderError("Narration must be a non-empty 24 kHz WAV.")
            return wav_file.getnframes() / wav_file.getframerate()
    except (OSError, wave.Error) as exc:
        raise RenderError(f"Invalid narration WAV: {path}") from exc


def validate_manifest(manifest: dict[str, Any], episode_dir: Path) -> dict[str, Any]:
    if manifest.get("schema_version") != "1.1":
        raise RenderError("Authorial release manifests must use schema_version 1.1.")
    video_id = manifest.get("video_id")
    scenes = manifest.get("scenes")
    audio = manifest.get("audio")
    output = manifest.get("output", {})
    if not isinstance(video_id, str) or not video_id.strip():
        raise RenderError("Manifest requires a non-empty video_id.")
    if not isinstance(scenes, list) or not scenes:
        raise RenderError("Manifest requires at least one scene.")
    if not isinstance(audio, dict):
        raise RenderError("Manifest requires an audio object.")
    audio_path = resolve_inside(episode_dir, audio.get("path"))
    if not audio_path.is_file():
        raise RenderError(f"Narration file not found: {audio_path}")

    normalized: list[dict[str, Any]] = []
    scene_ids: set[str] = set()
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise RenderError(f"Scene {index} must be an object.")
        scene_id = scene.get("scene_id", f"S{index:02d}")
        image_path = resolve_inside(episode_dir, scene.get("image"))
        duration = scene.get("duration")
        if not isinstance(scene_id, str) or not scene_id.strip() or scene_id in scene_ids:
            raise RenderError(f"Scene {index} has an invalid or duplicate scene_id.")
        scene_ids.add(scene_id)
        if not image_path.is_file():
            raise RenderError(f"Scene image not found: {image_path}")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise RenderError(f"Scene {scene_id} requires a positive duration.")
        zoom_end = scene.get("zoom_end", 1.07)
        if not isinstance(zoom_end, (int, float)) or not 1.0 <= zoom_end <= 1.15:
            raise RenderError(f"Scene {scene_id} has an unsafe zoom_end.")
        normalized.append({
            "scene_id": scene_id.strip(),
            "image": image_path,
            "duration": float(duration),
            "zoom_end": float(zoom_end),
        })

    transition = manifest.get("transition_duration", TRANSITION_DEFAULT)
    if not isinstance(transition, (int, float)) or transition < 0 or transition >= min(
        scene["duration"] for scene in normalized
    ):
        raise RenderError("transition_duration must be non-negative and shorter than every scene.")

    caption_path = None
    captions = manifest.get("captions")
    require_captions = manifest.get("require_captions", True)
    if require_captions and not captions:
        raise RenderError("Release manifests must provide external captions.")
    if captions:
        if not isinstance(captions, dict):
            raise RenderError("captions must be an object when provided.")
        caption_path = resolve_inside(episode_dir, captions.get("path"))
        if not caption_path.is_file():
            raise RenderError(f"Caption file not found: {caption_path}")

    output_path = output.get("path") if isinstance(output, dict) else None
    if not output_path:
        output_path = f"rendered/{video_id}-{{mode}}.mp4"

    return {
        "video_id": video_id.strip(),
        "scenes": normalized,
        "audio": audio_path,
        "captions": caption_path,
        "transition": float(transition),
        "output_template": output_path,
        "audio_duration": audio_duration(audio_path),
    }


def scene_filter(width: int, height: int, frames: int, zoom_end: float) -> str:
    step = (zoom_end - 1.0) / max(frames - 1, 1)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(1+on*{step:.8f},{zoom_end:.4f})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={FPS},format=yuv420p"
    )


def render_scene(scene: dict[str, Any], width: int, height: int, output: Path) -> None:
    frames = max(1, round(scene["duration"] * FPS))
    run([
        "ffmpeg", "-y", "-i", str(scene["image"]),
        "-vf", scene_filter(width, height, frames, scene["zoom_end"]),
        "-frames:v", str(frames), "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", str(output),
    ])


def xfade_filter(count: int, durations: list[float], transition: float) -> str:
    if count == 1:
        return "[0:v]null[v]"
    parts: list[str] = []
    accumulated = durations[0]
    previous = "0:v"
    for index in range(1, count):
        label = f"x{index}"
        offset = accumulated - transition
        parts.append(
            f"[{previous}][{index}:v]xfade=transition=fade:"
            f"duration={transition:.3f}:offset={offset:.3f}[{label}]"
        )
        previous = label
        accumulated = accumulated + durations[index] - transition
    parts.append(f"[{previous}]format=yuv420p[v]")
    return ";".join(parts)


def assemble_scenes(scene_files: list[Path], durations: list[float], transition: float, output: Path) -> None:
    command = ["ffmpeg", "-y"]
    for scene_file in scene_files:
        command.extend(["-i", str(scene_file)])
    command.extend([
        "-filter_complex", xfade_filter(len(scene_files), durations, transition),
        "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p", str(output),
    ])
    run(command)


def caption_filter(path: Path) -> str:
    escaped = path.as_posix().replace(":", r"\:")
    return f"subtitles={escaped}"


def mux_audio(video: Path, audio: Path, captions: Path | None, duration: float, output: Path) -> None:
    command = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio)]
    if captions:
        command.extend([
            "-filter_complex", f"[0:v]{caption_filter(captions)}[v]",
            "-map", "[v]", "-map", "1:a:0",
        ])
    else:
        command.extend(["-map", "0:v:0", "-map", "1:a:0"])
    command.extend([
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-ac", "1", "-movflags", "+faststart", str(output),
    ])
    run(command)


def render(manifest_path: Path, mode: str, output_override: Path | None) -> Path:
    episode_dir = manifest_path.parent.resolve()
    spec = validate_manifest(read_json(manifest_path), episode_dir)
    width, height = SIZES[mode]
    if output_override:
        output_value = output_override if output_override.is_absolute() else episode_dir / output_override
    else:
        output_value = episode_dir / spec["output_template"].format(mode=mode)
    output = output_value.resolve()
    if episode_dir not in output.parents and output != episode_dir:
        raise RenderError("Output path must remain inside the episode directory.")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".authorial-render-", dir=episode_dir) as temp_dir:
        temp = Path(temp_dir)
        scene_files: list[Path] = []
        for scene in spec["scenes"]:
            scene_output = temp / f"{scene['scene_id']}.mp4"
            render_scene(scene, width, height, scene_output)
            scene_files.append(scene_output)
        silent = temp / "silent.mp4"
        assemble_scenes(
            scene_files,
            [scene["duration"] for scene in spec["scenes"]],
            spec["transition"],
            silent,
        )
        partial = output.with_name(f".{output.name}.part")
        try:
            mux_audio(silent, spec["audio"], spec["captions"], spec["audio_duration"], partial)
            os.replace(partial, output)
        finally:
            partial.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an authorial vertical episode.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=sorted(SIZES), default="preview")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    spec = validate_manifest(read_json(manifest_path), manifest_path.parent.resolve())
    if args.validate_only:
        print(json.dumps({
            "video_id": spec["video_id"],
            "scenes": len(spec["scenes"]),
            "audio_duration": round(spec["audio_duration"], 3),
            "mode_sizes": SIZES,
            "human_review_required": True,
        }, indent=2))
        return 0
    print(render(manifest_path, args.mode, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
