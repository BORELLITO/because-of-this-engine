#!/usr/bin/env python3
"""Render the independent Because of This authorial episode pipeline.

The renderer is audio-first and deliberately conservative: no shake, no
random motion, no hidden image regeneration.  Motion is subpixel-stable and
selected from narrative metadata by :mod:`motion_engine`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from PIL import Image

try:  # works both as `python -m` and as the documented script path
    from production.motion_engine import normalize_motion, normalize_transition
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from motion_engine import normalize_motion, normalize_transition

FPS = 25
TRANSITION_DEFAULT = 0.33
SIZES = {"preview": (1080, 1920), "final": (2160, 3840)}


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
    if not isinstance(video_id, str) or not video_id.strip():
        raise RenderError("Manifest requires a non-empty video_id.")
    if not isinstance(scenes, list) or not scenes:
        raise RenderError("Manifest requires at least one scene.")
    if not isinstance(audio, dict):
        raise RenderError("Manifest requires an audio object.")
    audio_path = resolve_inside(episode_dir, audio.get("path"))
    if not audio_path.is_file():
        raise RenderError(f"Narration file not found: {audio_path}")

    default_transition = manifest.get("transition_duration", TRANSITION_DEFAULT)
    if not isinstance(default_transition, (int, float)) or default_transition < 0:
        raise RenderError("transition_duration must be non-negative.")
    normalized: list[dict[str, Any]] = []
    scene_ids: set[str] = set()
    previous_motion: str | None = None
    transition_durations: list[float] = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise RenderError(f"Scene {index + 1} must be an object.")
        scene_id = scene.get("scene_id", f"S{index + 1:02d}")
        image_path = resolve_inside(episode_dir, scene.get("image"))
        duration = scene.get("duration")
        if not isinstance(scene_id, str) or not scene_id.strip() or scene_id in scene_ids:
            raise RenderError(f"Scene {index + 1} has an invalid or duplicate scene_id.")
        scene_ids.add(scene_id)
        if not image_path.is_file():
            raise RenderError(f"Scene image not found: {image_path}")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise RenderError(f"Scene {scene_id} requires a positive duration.")
        zoom_end = scene.get("zoom_end", 1.07)
        if not isinstance(zoom_end, (int, float)) or not 1.0 <= zoom_end <= 1.15:
            raise RenderError(f"Scene {scene_id} has an unsafe zoom_end.")
        try:
            motion = normalize_motion(scene, index, previous_motion)
            transition = normalize_transition(scene, float(default_transition), index)
        except ValueError as exc:
            raise RenderError(str(exc)) from exc
        if index == 0:
            transition = {"type": "hard_cut", "duration": 0.0}
        else:
            # Legacy manifests keep their single safe crossfade default.  New
            # manifests can opt into a per-scene transition object.
            if not isinstance(scene.get("transition"), dict):
                transition = {"type": "crossfade", "duration": float(default_transition)}
            transition_durations.append(float(transition["duration"]))
        previous_motion = motion["type"]
        normalized.append({
            "scene_id": scene_id.strip(),
            "image": image_path,
            "duration": float(duration),
            "zoom_end": float(zoom_end),
            "motion": motion,
            "transition": transition,
        })

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

    output = manifest.get("output", {})
    if not isinstance(output, dict):
        raise RenderError("Manifest output must be an object.")
    output_path = output.get("path") or f"rendered/{video_id}-{{mode}}.mp4"
    narration_seconds = audio_duration(audio_path)
    timeline = sum(scene["duration"] for scene in normalized) - sum(transition_durations)
    if timeline <= 0 or abs(timeline - narration_seconds) > 0.75:
        raise RenderError(
            f"Scene timeline {timeline:.3f}s does not match narration {narration_seconds:.3f}s."
        )
    return {
        "video_id": video_id.strip(),
        "scenes": normalized,
        "audio": audio_path,
        "captions": caption_path,
        "transition": float(default_transition),
        "output_template": output_path,
        "audio_duration": narration_seconds,
        "timeline": timeline,
    }


def scene_filter(width: int, height: int, frames: int, zoom_end: float) -> str:
    """Compatibility filter for external callers; rendering uses subpixel Pillow."""
    step = (zoom_end - 1.0) / max(frames - 1, 1)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(1+on*{step:.8f},{zoom_end:.4f})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={FPS},format=yuv420p"
    )


def _ease(value: float, easing: str) -> float:
    if easing == "linear":
        return value
    if easing == "ease_in_out":
        return value * value * (3.0 - 2.0 * value)
    # smoothstep is the default and has zero velocity at both ends.
    return value * value * (3.0 - 2.0 * value)


def _motion_center(motion: dict[str, Any], progress: float) -> tuple[float, float, float]:
    eased = _ease(progress, motion.get("easing", "smoothstep"))
    intensity = float(motion.get("intensity", 1.0))
    focus = motion.get("focus", {"x": 0.5, "y": 0.5})
    x, y = float(focus.get("x", 0.5)), float(focus.get("y", 0.5))
    kind = motion.get("type", "slow_push_in")
    zoom_delta = 1.0
    if kind == "slow_pull_out":
        zoom_delta = 1.0 - 0.015 * intensity * eased
    elif kind == "static_hold":
        zoom_delta = 1.0
    elif kind == "pan_left":
        x += (0.12 - 0.24 * eased) * intensity
        zoom_delta = 1.0 + 0.015 * intensity
    elif kind == "pan_right":
        x += (-0.12 + 0.24 * eased) * intensity
        zoom_delta = 1.0 + 0.015 * intensity
    elif kind == "pan_up":
        y += (0.12 - 0.24 * eased) * intensity
        zoom_delta = 1.0 + 0.015 * intensity
    elif kind == "pan_down":
        y += (-0.12 + 0.24 * eased) * intensity
        zoom_delta = 1.0 + 0.015 * intensity
    elif kind == "focus_reframe":
        zoom_delta = 1.0 + 0.02 * intensity * eased
    else:  # slow_push_in and subtle_rotation_push_in
        zoom_delta = 1.0 + 0.025 * intensity * eased
    return max(0.0, min(1.0, x)), max(0.0, min(1.0, y)), zoom_delta


def _motion_frame(image: Image.Image, width: int, height: int, progress: float, scene: dict[str, Any]) -> Image.Image:
    motion = scene["motion"]
    focus_x, focus_y, local_zoom = _motion_center(motion, progress)
    base_zoom = float(scene.get("zoom_end", 1.07))
    kind = motion.get("type")
    if kind == "static_hold":
        zoom = 1.0
    elif kind == "slow_pull_out":
        zoom = max(1.0, base_zoom * (2.0 - local_zoom))
    else:
        zoom = max(1.0, base_zoom ** _ease(progress, motion.get("easing", "smoothstep"))) * local_zoom
    frame_image = image
    if kind == "subtle_rotation_push_in":
        frame_image = image.rotate(-0.35 + 0.7 * progress, resample=Image.Resampling.BICUBIC, expand=True)
    source_width, source_height = frame_image.size
    output_ratio = width / height
    source_ratio = source_width / source_height
    if source_ratio > output_ratio:
        crop_height = source_height / zoom
        crop_width = crop_height * output_ratio
    else:
        crop_width = source_width / zoom
        crop_height = crop_width / output_ratio
    left = focus_x * source_width - crop_width / 2.0
    top = focus_y * source_height - crop_height / 2.0
    left = max(0.0, min(source_width - crop_width, left))
    top = max(0.0, min(source_height - crop_height, top))
    return frame_image.transform(
        (width, height),
        Image.Transform.EXTENT,
        (left, top, left + crop_width, top + crop_height),
        # Pillow's EXTENT transform supports bicubic but not Lanczos.  Bicubic
        # keeps the crop continuous while avoiding per-frame integer rounding.
        resample=Image.Resampling.BICUBIC,
    ).convert("RGB")


def render_scene(scene: dict[str, Any], width: int, height: int, output: Path) -> None:
    """Render stable motion through a raw-video pipe, avoiding integer crop jitter."""
    frames = max(1, round(scene["duration"] * FPS))
    command = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with Image.open(scene["image"]) as opened:
            source = opened.convert("RGB")
            for frame_index in range(frames):
                progress = frame_index / max(frames - 1, 1)
                frame = _motion_frame(source, width, height, progress, scene)
                assert process.stdin is not None
                process.stdin.write(frame.tobytes())
        assert process.stdin is not None
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr else b""
        return_code = process.wait(timeout=900)
    except Exception:
        process.kill()
        process.wait()
        raise
    if return_code:
        detail = stderr.decode("utf-8", errors="replace")[-2000:]
        raise RenderError(f"FFmpeg scene render failed: {detail}")


def xfade_filter(
    count: int,
    durations: list[float],
    transition: float,
    transitions: list[dict[str, Any]] | None = None,
) -> str:
    if count == 1:
        return "[0:v]null[v]"
    parts: list[str] = []
    accumulated = durations[0]
    previous = "0:v"
    transitions = transitions or [
        {"type": "crossfade", "duration": transition} for _ in range(count - 1)
    ]
    for index in range(1, count):
        spec = transitions[index - 1]
        duration = max(float(spec.get("duration", transition)), 1.0 / FPS)
        transition_name = str(spec.get("type", "crossfade"))
        ffmpeg_transition = {
            "crossfade": "fade",
            "soft_dissolve": "fade",
            "dip_to_black": "fadeblack",
            "hard_cut": "fade",
            "motion_match": "smoothright",
        }.get(transition_name, "fade")
        label = f"x{index}"
        offset = accumulated - duration
        parts.append(
            f"[{previous}][{index}:v]xfade=transition={ffmpeg_transition}:"
            f"duration={duration:.3f}:offset={offset:.3f}[{label}]"
        )
        previous = label
        accumulated = accumulated + durations[index] - float(spec.get("duration", transition))
    parts.append(f"[{previous}]format=yuv420p[v]")
    return ";".join(parts)


def assemble_scenes(
    scene_files: list[Path],
    durations: list[float],
    transition: float,
    output: Path,
    transitions: list[dict[str, Any]] | None = None,
) -> None:
    command = ["ffmpeg", "-y"]
    for scene_file in scene_files:
        command.extend(["-i", str(scene_file)])
    command.extend([
        "-filter_complex", xfade_filter(len(scene_files), durations, transition, transitions),
        "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p", str(output),
    ])
    run(command)


def caption_filter(path: Path) -> str:
    return f"subtitles={path.as_posix().replace(':', r'\\:')}"


def mux_audio(video: Path, audio: Path, captions: Path | None, duration: float, output: Path) -> None:
    command = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio)]
    if captions:
        command.extend(["-filter_complex", f"[0:v]{caption_filter(captions)}[v]", "-map", "[v]", "-map", "1:a:0"])
    else:
        command.extend(["-map", "0:v:0", "-map", "1:a:0"])
    command.extend([
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-ac", "1", "-movflags", "+faststart", "-f", "mp4", str(output),
    ])
    run(command)


def render(manifest_path: Path, mode: str, output_override: Path | None) -> Path:
    episode_dir = manifest_path.parent.resolve()
    spec = validate_manifest(read_json(manifest_path), episode_dir)
    width, height = SIZES[mode]
    output_value = output_override if output_override else episode_dir / spec["output_template"].format(mode=mode)
    output = (output_value if output_value.is_absolute() else episode_dir / output_value).resolve()
    if episode_dir not in output.parents and output != episode_dir:
        raise RenderError("Output path must remain inside the episode directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    transitions = [scene["transition"] for scene in spec["scenes"][1:]]
    with tempfile.TemporaryDirectory(prefix=".authorial-render-", dir=episode_dir) as temp_dir:
        temp = Path(temp_dir)
        scene_files: list[Path] = []
        for scene in spec["scenes"]:
            scene_output = temp / f"{scene['scene_id']}.mp4"
            render_scene(scene, width, height, scene_output)
            scene_files.append(scene_output)
        silent = temp / "silent.mp4"
        assemble_scenes(scene_files, [scene["duration"] for scene in spec["scenes"]], spec["transition"], silent, transitions)
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
            "timeline": round(spec["timeline"], 3),
            "motion": [{"scene_id": s["scene_id"], **s["motion"]} for s in spec["scenes"]],
            "mode_sizes": SIZES,
            "human_review_required": True,
        }, indent=2))
        return 0
    print(render(manifest_path, args.mode, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
