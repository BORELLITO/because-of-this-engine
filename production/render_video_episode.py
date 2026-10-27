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


def scene_filter(
    width: int,
    height: int,
    focus_x: float,
    focus_y: float,
    color_grade: dict[str, Any] | None = None,
) -> str:
    grade = color_grade or {}
    filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=increase",
        f"crop={width}:{height}:x='(iw-ow)*{focus_x:.4f}':y='(ih-oh)*{focus_y:.4f}'",
    ]
    if grade.get("enabled") is True:
        brightness = float(grade.get("brightness", -0.03))
        contrast = float(grade.get("contrast", 1.08))
        saturation = float(grade.get("saturation", 0.90))
        gamma = float(grade.get("gamma", 0.96))
        if not -0.20 <= brightness <= 0.20 or not 0.80 <= contrast <= 1.30:
            raise RenderError("Color grade brightness/contrast is outside the safe editorial range.")
        if not 0.65 <= saturation <= 1.15 or not 0.80 <= gamma <= 1.15:
            raise RenderError("Color grade saturation/gamma is outside the safe editorial range.")
        filters.append(
            f"eq=brightness={brightness:.4f}:contrast={contrast:.4f}:"
            f"saturation={saturation:.4f}:gamma={gamma:.4f}"
        )

        suspense = grade.get("cinematic_suspense") or {}
        suspense_enabled = suspense.get("enabled") is True
        if suspense_enabled:
            cool_shadows = float(suspense.get("cool_shadows", 0.025))
            warm_highlights = float(suspense.get("warm_highlights", 0.010))
            if not 0.0 <= cool_shadows <= 0.10:
                raise RenderError("Cinematic suspense cool_shadows is outside the safe editorial range.")
            if not 0.0 <= warm_highlights <= 0.06:
                raise RenderError("Cinematic suspense warm_highlights is outside the safe editorial range.")
            # Cool, slightly desaturated shadows plus restrained warm highlights
            # create the channel's investigative-noir suspense signature.
            filters.append(
                "colorbalance="
                f"rs={-cool_shadows:.4f}:gs={-(cool_shadows * 0.45):.4f}:"
                f"bs={cool_shadows:.4f}:rh={warm_highlights:.4f}:"
                f"gh={(warm_highlights * 0.55):.4f}:bh={-warm_highlights:.4f}"
            )

        if grade.get("vignette", True) is True:
            filters.append("vignette=PI/5")
    filters.extend([f"fps={FPS}", "setpts=PTS-STARTPTS", "format=yuv420p", "setsar=1"])
    return ",".join(filters)

def render_scene(
    scene: dict[str, Any],
    width: int,
    height: int,
    output: Path,
    color_grade: dict[str, Any] | None = None,
) -> None:
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
        "-i", str(source), "-an", "-vf", scene_filter(width, height, focus_x, focus_y, color_grade),
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
    parts.append(f"[{previous}]format=yuv420p,setsar=1[v]")
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


def load_narration_coverage(manifest_path: Path) -> dict[str, Any]:
    report_path = manifest_path.parent / "rendered" / "narration-coverage.json"
    if not report_path.is_file():
        raise RenderError(
            "Narration coverage report is missing; render requires forced-alignment scene timing."
        )
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"Could not read narration coverage report: {report_path}") from exc
    coverage = report.get("narration_coverage") or {}
    if report.get("status") != "STORY_INTELLIGENCE_PASS":
        raise RenderError("Narration coverage report is not STORY_INTELLIGENCE_PASS.")
    if coverage.get("timing_status") != "FORCED_ALIGNMENT_SCENE_TIMES_PASS":
        raise RenderError("Narration coverage report has no forced-alignment scene times.")
    scenes = coverage.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise RenderError("Narration coverage report contains no scene timing spans.")
    return report


def _audio_timed_scene_durations(
    scenes: list[dict[str, Any]],
    narration_seconds: float,
    spans: list[dict[str, Any]],
    clip_policy: dict[str, Any],
) -> list[float]:
    if len(scenes) != len(spans):
        raise RenderError("Forced-alignment scene timing count does not match the manifest.")
    scene_ids = [str(scene.get("scene_id")) for scene in scenes]
    span_ids = [str(span.get("scene_id")) for span in spans]
    if scene_ids != span_ids:
        raise RenderError(
            f"Forced-alignment scene order mismatch: expected {scene_ids}, got {span_ids}."
        )
    boundaries = [0.0]
    for index in range(len(spans) - 1):
        current_end = float(spans[index].get("audio_end", -1))
        next_start = float(spans[index + 1].get("audio_start", -1))
        if current_end < 0 or next_start < 0 or next_start + 0.001 < current_end:
            raise RenderError("Forced-alignment scene spans overlap or contain invalid timestamps.")
        boundaries.append((current_end + next_start) / 2.0)
    boundaries.append(float(narration_seconds))
    durations: list[float] = []
    min_seconds = float(clip_policy.get("min_scene_seconds", 2.0))
    max_seconds = float(clip_policy.get("max_scene_seconds", 20.0))
    for index, scene in enumerate(scenes):
        base_duration = boundaries[index + 1] - boundaries[index]
        transition_after = (
            transition_duration(scenes[index + 1].get("transition", {}))
            if index < len(scenes) - 1
            else 0.0
        )
        duration = base_duration + transition_after
        if base_duration < min_seconds - 0.02:
            raise RenderError(
                f"Scene {scene.get('scene_id')} narration span is {base_duration:.3f}s, "
                f"below the {min_seconds:.2f}s visual-beat minimum."
            )
        if base_duration > max_seconds + 0.02:
            raise RenderError(
                f"Scene {scene.get('scene_id')} narration span is {base_duration:.3f}s, "
                f"above the {max_seconds:.2f}s visual-beat maximum; split the beat."
            )
        source_duration = (scene.get("asset") or {}).get("metadata", {}).get("duration")
        if source_duration is None:
            source_duration = (scene.get("asset") or {}).get("duration_seconds")
        if source_duration is not None:
            source_in = float(scene.get("source_in", 0.0))
            if source_in + duration > float(source_duration) + 0.05:
                raise RenderError(
                    f"Scene {scene.get('scene_id')} forced-alignment duration exceeds source duration."
                )
        durations.append(duration)
    if abs(sum(durations) - sum(boundaries[-1:] or [0]) - sum(
        transition_duration(scenes[index + 1].get("transition", {}))
        for index in range(len(scenes) - 1)
    )) > 0.05:
        raise RenderError("Forced-alignment scene durations do not reconcile with narration duration.")
    return durations


def narration_locked_scenes(
    scenes: list[dict[str, Any]],
    narration_seconds: float,
    clip_policy: dict[str, Any] | None = None,
    narration_spans: list[dict[str, Any]] | None = None,
    *,
    allow_legacy: bool = False,
) -> list[dict[str, Any]]:
    """Lock scene boundaries to forced-alignment spans from the final WAV.

    The proportional allocator is retained only for explicit legacy unit-test
    callers. Production rendering is fail-closed when forced timing is absent.
    """
    if not scenes:
        raise RenderError("Narration-locked rendering requires at least one scene.")
    if not 60.0 <= narration_seconds <= 75.0:
        raise RenderError(
            f"Narration duration must remain between 60s and 75s; got {narration_seconds:.3f}s."
        )

    policy = clip_policy or {
        "min_scene_seconds": 2.0,
        "max_scene_seconds": 20.0,
    }
    if narration_spans is None and not allow_legacy:
        raise RenderError(
            "Forced-alignment narration spans are mandatory; legacy proportional timing is disabled for production."
        )
    if narration_spans is not None:
        durations = _audio_timed_scene_durations(
            scenes,
            narration_seconds,
            narration_spans,
            policy,
        )
        locked: list[dict[str, Any]] = []
        for scene, duration, span in zip(scenes, durations, narration_spans):
            copy = dict(scene)
            copy["duration"] = duration
            copy["narration_span"] = {
                "audio_start": float(span["audio_start"]),
                "audio_end": float(span["audio_end"]),
                "word_start_index": span.get("word_start_index"),
                "word_end_index": span.get("word_end_index"),
                "timing_source": span.get("timing_source"),
            }
            locked.append(copy)
        return locked

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
    locked = []
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


def write_loop_ass(
    path: Path,
    title: str,
    duration: float,
    fade_in_seconds: float = 0.24,
    fade_out_seconds: float = 0.36,
) -> Path:
    """Render the branded loop card through libass, not FFmpeg drawtext."""
    safe_title = str(title).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    fade_in_ms = max(80, min(round(fade_in_seconds * 1000), round(duration * 1000 * 0.45)))
    fade_out_ms = max(120, min(round(fade_out_seconds * 1000), round(duration * 1000 * 0.55)))
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Loop,Arial,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,0,5,40,40,40,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,{ass_time(duration)},Loop,,0,0,0,,{{\\fad({fade_in_ms},{fade_out_ms})}}{safe_title}
"""
    path.write_text(ass, encoding="utf-8")
    return path


def loop_outro_seconds(manifest: dict[str, Any]) -> float:
    loop = manifest.get("loop") or {}
    if loop.get("enabled") is not True:
        return 0.0
    seconds = float(loop.get("outro_seconds", 1.2))
    if not 0.8 <= seconds <= 1.5:
        raise RenderError("Loop outro must be between 0.8s and 1.5s for a smooth branded close.")
    return seconds


def rendered_duration(manifest: dict[str, Any], narration_seconds: float) -> float:
    return narration_seconds + loop_outro_seconds(manifest)


def mux_audio(
    video: Path,
    audio: Path,
    captions: Path,
    output: Path,
    narration_duration: float,
    music: Path | None,
    music_volume: float,
    brand_ass: Path | None,
    logo_path: Path | None,
    brand: dict[str, Any],
    width: int = 1080,
    height: int = 1920,
    loop: dict[str, Any] | None = None,
) -> None:
    loop = loop or {}
    outro_seconds = loop_outro_seconds({"loop": loop})
    total_duration = narration_duration + outro_seconds
    audio_fade = min(float(loop.get("audio_fade_seconds", 0.60)), max(0.1, outro_seconds))
    tail_fade_seconds = float(loop.get("tail_fade_seconds", 0.55))
    card_fade_in_seconds = float(loop.get("card_fade_in_seconds", 0.24))
    card_fade_out_seconds = float(loop.get("card_fade_out_seconds", 0.36))
    if not 0.25 <= tail_fade_seconds <= 0.90:
        raise RenderError("Loop tail_fade_seconds must be between 0.25s and 0.90s.")
    if not 0.12 <= card_fade_in_seconds <= 0.60:
        raise RenderError("Loop card_fade_in_seconds must be between 0.12s and 0.60s.")
    if not 0.18 <= card_fade_out_seconds <= 0.70:
        raise RenderError("Loop card_fade_out_seconds must be between 0.18s and 0.70s.")
    command = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio)]
    filters: list[str] = []
    filters.append(f"[0:v]subtitles='{_escape_filter_path(captions)}'[captioned]")

    logo_enabled = logo_path is not None and brand.get("logo_enabled", False) is True
    if logo_enabled:
        command.extend(["-loop", "1", "-framerate", "1", "-i", str(logo_path)])
        logo_width = int(brand.get("logo_width", 540))
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
                "eof_action=repeat:shortest=1[main_visual]"
            ),
        ])
    elif brand_ass:
        filters.append(f"[captioned]subtitles='{_escape_filter_path(brand_ass)}'[main_visual]")
    else:
        filters.append("[captioned]null[main_visual]")

    loop_ass_path: Path | None = None
    if outro_seconds > 0:
        loop_title = str(loop.get("title", "BECAUSE OF THIS"))
        loop_ass_path = output.parent / f".{output.stem}-loop.ass"
        write_loop_ass(
            loop_ass_path,
            loop_title,
            outro_seconds,
            fade_in_seconds=card_fade_in_seconds,
            fade_out_seconds=card_fade_out_seconds,
        )
        card_start_fade = max(0.0, outro_seconds - card_fade_out_seconds)
        filters.extend([
            (
                f"color=c=black:s={width}x{height}:r={FPS}:d={outro_seconds:.3f},"
                f"fade=t=in:st=0:d={card_fade_in_seconds:.3f},"
                f"fade=t=out:st={card_start_fade:.3f}:d={card_fade_out_seconds:.3f},"
                "format=yuv420p,setsar=1,setpts=PTS-STARTPTS[outro_base]"
            ),
            f"[outro_base]subtitles='{_escape_filter_path(loop_ass_path)}'[outro]",
            (
                f"[main_visual]format=yuv420p,"
                f"fade=t=out:st={max(0.0, narration_duration - tail_fade_seconds):.3f}:"
                f"d={tail_fade_seconds:.3f},setsar=1,setpts=PTS-STARTPTS[main]"
            ),
            "[main][outro]concat=n=2:v=1:a=0[v]",
        ])
    else:
        filters.append("[main_visual]format=yuv420p,setpts=PTS-STARTPTS[v]")

    if music is None:
        raise RenderError("Background suspense music is mandatory; refusing a voice-only render.")
    if not music.is_file():
        raise RenderError(f"Background suspense music file is missing: {music}")
    music_input_index = 2 + int(logo_enabled)
    command.extend(["-stream_loop", "-1", "-i", str(music)])
    voice_pad = f",apad=pad_dur={outro_seconds:.3f}" if outro_seconds > 0 else ""
    filters.extend([
        f"[1:a]aresample=48000{voice_pad},asplit=2[voice_sc][voice_mix]",
        f"[{music_input_index}:a]aresample=48000,volume={music_volume:.4f}[music]",
        "[music][voice_sc]sidechaincompress=threshold=0.050:ratio=8:attack=20:release=400:makeup=1[ducked]",
        "[voice_mix][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mixed]",
        f"[mixed]loudnorm=I=-15:TP=-1.0:LRA=11,alimiter=limit=0.95"
        + (f",afade=t=out:st={max(0.0, total_duration - audio_fade):.3f}:d={audio_fade:.3f}" if outro_seconds > 0 else "")
        + "[a]",
    ])
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", "[a]",
        "-t", f"{total_duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])
    try:
        run(command)
    finally:
        if loop_ass_path is not None:
            loop_ass_path.unlink(missing_ok=True)

def prepare_logo(source: Path, output: Path, width: int) -> Path:
    """Decode and resize the static logo once before the long mux."""
    run([
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-vf", f"scale={width}:-1:flags=lanczos,format=rgba",
        "-frames:v", "1", "-update", "1", str(output),
    ])
    return output


def render(manifest_path: Path, mode: str) -> Path:
    manifest = load_manifest(manifest_path)
    spec = validate_manifest(manifest, manifest_path.parent, mode=mode, check_files=True, enforce_canonical=True)
    narration_seconds = audio_duration(spec["audio_path"])
    coverage_report = load_narration_coverage(manifest_path)
    coverage = coverage_report["narration_coverage"]
    locked_scenes = narration_locked_scenes(
        spec["scenes"],
        narration_seconds,
        clip_policy=spec.get("clip_policy"),
        narration_spans=coverage["scenes"],
    )
    width, height = SIZES[mode]
    output_template = str(manifest.get("output", {}).get("path", "rendered/{video_id}-{mode}.mp4"))
    output = (manifest_path.parent / output_template.format(video_id=spec["video_id"], mode=mode)).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="because-of-this-scenes-") as temp:
        scene_files: list[Path] = []
        for index, scene in enumerate(locked_scenes, start=1):
            target = Path(temp) / f"scene-{index:02d}.mp4"
            render_scene(scene, width, height, target, manifest.get("color_grade"))
            scene_files.append(target)
        assembled = Path(temp) / "assembled.mp4"
        assemble(scene_files, locked_scenes, assembled)
        music_spec = spec.get("music")
        if not isinstance(music_spec, dict):
            raise RenderError("Manifest must declare a licensed suspense music object.")
        music_path = (manifest_path.parent / str(music_spec["path"])).resolve()
        if not music_path.is_file():
            raise RenderError(f"Licensed suspense music file is missing: {music_path}")
        music_volume = float(music_spec.get("volume", 0.12))
        logo_path = spec.get("brand_logo_path")
        if logo_path is not None and spec["brand"].get("logo_enabled", False) is True:
            logo_path = prepare_logo(
                logo_path,
                Path(temp) / "brand-logo-runtime.png",
                int(spec["brand"].get("logo_width", 540)),
            )
        if logo_path is None or spec["brand"].get("logo_enabled") is not True:
            raise RenderError("Canonical profile requires the Because Of This logo overlay.")
        brand_ass = None
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
            width,
            height,
            manifest.get("loop") or {},
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
            coverage = load_narration_coverage(args.manifest.resolve())
            print(json.dumps({
                "status": "VIDEO_CONTRACT_PASS",
                "video_id": spec["video_id"],
                "mode": args.mode,
                "scenes": len(spec["scenes"]),
                "timeline_seconds": round(spec["total_scene_duration"], 3),
                "narration_timing": coverage["narration_coverage"].get("timing_status"),
            }, ensure_ascii=False))
        else:
            output = render(args.manifest.resolve(), args.mode)
            print(json.dumps({"status": "VIDEO_RENDER_COMPLETE", "video_id": spec["video_id"], "mode": args.mode, "output": str(output)}, ensure_ascii=False))
        return 0
    except (VideoContractError, RenderError, OSError, ValueError) as exc:
        print(f"VIDEO RENDER BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


