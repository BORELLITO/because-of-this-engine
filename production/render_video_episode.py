#!/usr/bin/env python3
"""Deterministic video-only renderer for Because of This Engine v2."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.video_asset_contract import VideoContractError, ffprobe, load_manifest, validate_manifest

FPS = 25
SIZES = {"preview": (1080, 1920), "final": (2160, 3840)}


class RenderError(RuntimeError):
    pass


def run(command: list[str], timeout: int = 900) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, timeout=timeout, text=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise RenderError(f"FFmpeg command failed: {detail[-2000:]}") from exc


def audio_duration(path: Path) -> float:
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)]
    try:
        return float(run(command, timeout=60).stdout.strip())
    except (ValueError, RenderError) as exc:
        raise RenderError(f"Could not read narration duration: {path}") from exc


def _escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def scene_filter(width: int, height: int, focus_x: float, focus_y: float) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:x='(iw-ow)*{focus_x:.4f}':y='(ih-oh)*{focus_y:.4f}',"
        f"fps={FPS},setpts=PTS-STARTPTS,format=yuv420p"
    )


def render_scene(scene: dict[str, Any], width: int, height: int, output: Path) -> None:
    asset = scene["asset"]
    source = Path(asset["path"])
    info = ffprobe(source)
    source_in = float(scene.get("source_in", 0.0))
    requested = float(scene["duration"])
    if source_in < 0 or source_in + requested > float(info["duration"]) + 0.05:
        raise RenderError(
            f"Asset {asset['asset_id']} is too short for scene {scene['scene_id']} "
            f"({info['duration']:.3f}s available, {source_in + requested:.3f}s required)."
        )
    focus = scene.get("focus", {"x": 0.5, "y": 0.5})
    focus_x = float(focus.get("x", 0.5))
    focus_y = float(focus.get("y", 0.5))
    if not 0 <= focus_x <= 1 or not 0 <= focus_y <= 1:
        raise RenderError(f"Scene {scene['scene_id']} has an invalid focus point.")
    run([
        "ffmpeg", "-y", "-ss", f"{source_in:.3f}", "-t", f"{requested:.3f}",
        "-i", str(source), "-an", "-vf", scene_filter(width, height, focus_x, focus_y),
        "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])


def xfade_filter(durations: list[float], transitions: list[dict[str, Any]]) -> str:
    if len(durations) == 1:
        return "[0:v]null[v]"
    labels: list[str] = []
    parts: list[str] = []
    accumulated = durations[0]
    previous = "0:v"
    # FFmpeg has no literal hard-cut xfade; one frame of fade is the
    # deterministic, visually instantaneous cut used by the contract.
    names = {
        "hard_cut": "fade",
        "crossfade": "fade",
        "soft_dissolve": "fade",
        "dip_to_black": "fadeblack",
        "motion_match": "smoothright",
    }
    for index in range(1, len(durations)):
        spec = transitions[index - 1] if index - 1 < len(transitions) else {"type": "crossfade", "duration": 0.25}
        duration = transition_duration(spec)
        if duration >= min(accumulated, durations[index]):
            raise RenderError(f"Transition before scene {index + 1} is longer than its adjacent scene.")
        label = f"v{index}"
        kind = names.get(str(spec.get("type", "crossfade")), "fade")
        parts.append(f"[{previous}][{index}:v]xfade=transition={kind}:duration={duration:.3f}:offset={accumulated - duration:.3f}[{label}]")
        labels.append(label)
        previous = label
        accumulated += durations[index] - duration
    parts.append(f"[{previous}]format=yuv420p[v]")
    return ";".join(parts)


def transition_duration(spec: dict[str, Any]) -> float:
    return max(float(spec.get("duration", 0.25)), 1 / FPS)


def _bounded_weighted_allocation(
    planned: list[float],
    lower: list[float],
    upper: list[float],
    target: float,
) -> list[float]:
    if not planned or len(planned) != len(lower) or len(planned) != len(upper):
        raise RenderError("Narration-locked allocation requires matching scene bounds.")
    if sum(lower) - 0.001 > target:
        raise RenderError("Narration is shorter than the minimum visual-beat allocation.")
    if sum(upper) + 0.001 < target:
        raise RenderError("Narration is longer than the source-safe visual-beat allocation.")

    durations = list(lower)
    remaining = target - sum(durations)
    weights = [max(float(value), 0.01) for value in planned]
    while remaining > 0.00001:
        active = [index for index, value in enumerate(upper) if value - durations[index] > 0.00001]
        if not active:
            raise RenderError("Could not distribute the narration across source-safe scene limits.")
        weight_total = sum(weights[index] for index in active)
        progress = 0.0
        for index in active:
            share = remaining * weights[index] / weight_total
            addition = min(share, upper[index] - durations[index])
            durations[index] += addition
            progress += addition
        if progress <= 0.00001:
            raise RenderError("Narration-locked allocation stalled before reaching the target duration.")
        remaining -= progress
    return durations


def narration_locked_scenes(
    scenes: list[dict[str, Any]],
    narration_seconds: float,
    clip_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Scale scenes to narration while respecting source and editorial limits.

    Every unique clip is preserved. Transition overlap is included in the
    scene-sum target, and no locked scene may exceed the usable source length.
    """
    if not scenes:
        raise RenderError("Narration-locked rendering requires at least one scene.")
    if not 60.0 <= narration_seconds <= 75.0:
        raise RenderError(f"Narration duration must remain between 60s and 75s; got {narration_seconds:.3f}s.")

    policy = clip_policy or {
        "min_scene_seconds": 2.0,
        "max_scene_seconds": 20.0,
    }
    planned = [float(scene["duration"]) for scene in scenes]
    planned_total = sum(planned)
    if planned_total <= 0:
        raise RenderError("Scene timeline must have a positive planned duration.")

    transitions = [
        scene.get("transition", {"type": "crossfade", "duration": 0.25})
        for scene in scenes[1:]
    ]
    overlap = sum(transition_duration(spec) for spec in transitions)
    target_scene_sum = narration_seconds + overlap

    lower = [float(policy.get("min_scene_seconds", 2.0)) for _ in scenes]
    upper: list[float] = []
    for scene in scenes:
        scene_limit = float(policy.get("max_scene_seconds", 20.0))
        asset = scene.get("asset") or {}
        metadata = asset.get("metadata") or {}
        source_duration = metadata.get("duration") or asset.get("duration_seconds")
        if source_duration:
            source_in = float(scene.get("source_in", 0.0))
            scene_limit = min(scene_limit, float(source_duration) - source_in - 0.05)
        upper.append(scene_limit)
    for index, (low, high) in enumerate(zip(lower, upper), start=1):
        if high < low:
            raise RenderError(f"Scene {index} source is shorter than its minimum visual beat.")

    locked_durations = _bounded_weighted_allocation(planned, lower, upper, target_scene_sum)
    locked: list[dict[str, Any]] = []
    for scene, duration in zip(scenes, locked_durations):
        copy = dict(scene)
        copy["duration"] = duration
        locked.append(copy)
    return locked


def assemble(scene_files: list[Path], scenes: list[dict[str, Any]], output: Path) -> None:
    command = ["ffmpeg", "-y"]
    for path in scene_files:
        command.extend(["-i", str(path)])
    transitions = [scene.get("transition", {"type": "crossfade", "duration": 0.25}) for scene in scenes[1:]]
    graph = xfade_filter([float(scene["duration"]) for scene in scenes], transitions)
    command.extend(["-filter_complex", graph, "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)])
    run(command)


def ass_time(seconds: float) -> str:
    total_centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_color(value: str) -> str:
    raw = str(value or "#E3262E").lstrip("#")
    if len(raw) != 6 or any(char not in "0123456789abcdefABCDEF" for char in raw):
        raw = "E3262E"
    red, green, blue = raw[0:2], raw[2:4], raw[4:6]
    return f"&H00{blue}{green}{red}"


def write_brand_ass(path: Path, brand: dict[str, Any], duration: float) -> Path | None:
    if brand.get("watermark_enabled", True) is False:
        return None
    text = str(brand.get("watermark_text", "|B")).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Brand,Arial,42,{ass_color(brand.get("accent_color", "#E3262E"))},&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,9,54,54,80,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,{ass_time(duration)},Brand,,0,0,0,,{text}
"""
    path.write_text(ass, encoding="utf-8")
    return path


def mux_audio(
    video: Path,
    audio: Path,
    captions: Path,
    output: Path,
    duration: float,
    music: Path | None,
    music_volume: float,
    brand_ass: Path | None,
    logo_path: Path | None,
    brand: dict[str, Any],
) -> None:
    command = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio)]
    filters: list[str] = []
    filters.append(f"[0:v]subtitles='{_escape_filter_path(captions)}'[captioned]")

    logo_enabled = logo_path is not None and brand.get("logo_enabled", False) is True
    if logo_enabled:
        command.extend(["-loop", "1", "-framerate", str(FPS), "-i", str(logo_path)])
        logo_width = int(brand.get("logo_width", 360))
        logo_opacity = float(brand.get("logo_opacity", 0.82))
        logo_margin = int(brand.get("logo_margin", 54))
        logo_top = int(brand.get("logo_top", 72))
        filters.extend([
            (
                f"[2:v]format=rgba,scale={logo_width}:-1,"
                "colorkey=0x000000:0.18:0.05,"
                f"colorchannelmixer=aa={logo_opacity:.3f}[logo]"
            ),
            (
                f"[captioned][logo]overlay="
                f"x=main_w-overlay_w-{logo_margin}:y={logo_top}:"
                "eof_action=repeat:shortest=1[v]"
            ),
        ])
    elif brand_ass:
        filters.append(f"[captioned]subtitles='{_escape_filter_path(brand_ass)}'[v]")
    else:
        filters.append("[captioned]null[v]")

    music_input_index = 2 + int(logo_enabled)
    if music:
        command.extend(["-stream_loop", "-1", "-i", str(music)])
        filters.extend([
            "[1:a]aresample=48000,asplit=2[voice_sc][voice_mix]",
            f"[{music_input_index}:a]aresample=48000,volume={music_volume:.4f}[music]",
            "[music][voice_sc]sidechaincompress=threshold=0.035:ratio=10:attack=15:release=420[ducked]",
            "[voice_mix][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,loudnorm=I=-15:TP=-1.0:LRA=11,alimiter=limit=0.95[a]",
        ])
    else:
        filters.append("[1:a]aresample=48000,loudnorm=I=-15:TP=-1.0:LRA=11,alimiter=limit=0.95[a]")
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", "[a]",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])
    run(command)


def render(manifest_path: Path, mode: str) -> Path:
    manifest = load_manifest(manifest_path)
    spec = validate_manifest(manifest, manifest_path.parent, mode=mode, check_files=True)
    narration_seconds = audio_duration(spec["audio_path"])
    locked_scenes = narration_locked_scenes(
        spec["scenes"],
        narration_seconds,
        clip_policy=spec.get("clip_policy"),
    )
    width, height = SIZES[mode]
    output_template = str(manifest.get("output", {}).get("path", "rendered/{video_id}-{mode}.mp4"))
    output = (manifest_path.parent / output_template.format(video_id=spec["video_id"], mode=mode)).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="because-of-this-scenes-") as temp:
        scene_files: list[Path] = []
        for index, scene in enumerate(locked_scenes, start=1):
            target = Path(temp) / f"scene-{index:02d}.mp4"
            render_scene(scene, width, height, target)
            scene_files.append(target)
        assembled = Path(temp) / "assembled.mp4"
        assemble(scene_files, locked_scenes, assembled)
        music_path = None
        music_volume = 0.06
        if spec["music"]:
            music_path = (manifest_path.parent / spec["music"]["path"]).resolve()
            music_volume = float(spec["music"].get("volume", 0.06))
        logo_path = spec.get("brand_logo_path")
        brand_ass = None if logo_path else write_brand_ass(Path(temp) / "brand.ass", spec["brand"], narration_seconds)
        mux_audio(
            assembled,
            spec["audio_path"],
            spec["caption_path"],
            output,
            narration_seconds,
            music_path,
            music_volume,
            brand_ass,
            logo_path,
            spec["brand"],
        )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=tuple(SIZES), default="preview")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest.resolve())
        spec = validate_manifest(manifest, args.manifest.resolve().parent, mode=args.mode, check_files=not args.validate_only)
        if args.validate_only:
            print(json.dumps({"status": "VIDEO_CONTRACT_PASS", "video_id": spec["video_id"], "mode": args.mode, "scenes": len(spec["scenes"]), "timeline_seconds": round(spec["total_scene_duration"], 3)}, ensure_ascii=False))
        else:
            output = render(args.manifest.resolve(), args.mode)
            print(json.dumps({"status": "VIDEO_RENDER_COMPLETE", "video_id": spec["video_id"], "mode": args.mode, "output": str(output)}, ensure_ascii=False))
        return 0
    except (VideoContractError, RenderError, OSError, ValueError) as exc:
        print(f"VIDEO RENDER BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


