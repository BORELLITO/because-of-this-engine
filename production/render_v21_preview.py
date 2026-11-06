#!/usr/bin/env python3
"""Render an isolated Episode 005 V2.1 preview with FFmpeg.

This renderer is deliberately separate from the V7 canonical renderer. It
accepts only the approved Episode 005 scene plan, frozen Edge TTS audio and
native Edge captions, and writes a preview artifact. It never changes the
production record, Drive, the global catalog or publication state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


FPS = 60
WIDTH = 1080
HEIGHT = 1920
MAX_SOURCE_LOOPS = 8


class PreviewRenderError(RuntimeError):
    pass


def run(command: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise PreviewRenderError(f"FFmpeg command failed: {detail[-2000:]}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def media_duration(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], timeout=60)
    try:
        value = float(result.stdout.strip())
    except ValueError as exc:
        raise PreviewRenderError(f"Could not read media duration: {path}") from exc
    if value <= 0:
        raise PreviewRenderError(f"Media duration is not positive: {path}")
    return value


def parse_clock(value: str) -> float:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise PreviewRenderError(f"Invalid shot clock: {value}")
    minutes, seconds = (int(item) for item in parts)
    return minutes * 60 + seconds


def parse_range(value: str) -> tuple[float, float]:
    try:
        start, end = value.split("-", 1)
        start_seconds = parse_clock(start)
        end_seconds = parse_clock(end)
    except (ValueError, TypeError) as exc:
        raise PreviewRenderError(f"Invalid shot range: {value}") from exc
    if end_seconds <= start_seconds:
        raise PreviewRenderError(f"Shot range is not positive: {value}")
    return start_seconds, end_seconds


def build_scene_plan(scene_manifest: dict[str, Any], story: dict[str, Any]) -> list[dict[str, Any]]:
    assets = {
        str(item.get("candidate_id")): item
        for item in scene_manifest.get("assets", [])
        if isinstance(item, dict) and str(item.get("candidate_id", "")).strip()
    }
    assignments = {}
    for item in scene_manifest.get("shot_assignments", []):
        if not isinstance(item, dict):
            continue
        assignment = item.get("assignment")
        if isinstance(assignment, dict):
            assignments[str(item.get("shot_id"))] = str(assignment.get("candidate_id", ""))
    plan: list[dict[str, Any]] = []
    for shot in story.get("shot_plan", []):
        shot_id = str(shot.get("shot_id", "")).strip()
        candidate_id = assignments.get(shot_id, "")
        asset = assets.get(candidate_id)
        if not asset:
            raise PreviewRenderError(f"No approved manifest asset assignment for {shot_id}")
        start, end = parse_range(str(shot.get("range", "")))
        plan.append({
            "shot_id": shot_id,
            "candidate_id": candidate_id,
            "duration": end - start,
            "role": str(shot.get("role", "")),
            "asset": asset,
        })
    if len(plan) != 16 or len({item["candidate_id"] for item in plan}) != 16:
        raise PreviewRenderError("Episode 005 preview requires 16 distinct assigned assets.")
    return plan


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def render_scene(scene: dict[str, Any], asset_path: Path, output: Path) -> None:
    duration = float(scene["duration"])
    source_duration = media_duration(asset_path)
    loop_count = max(0, math.ceil(duration / source_duration) - 1)
    if loop_count > MAX_SOURCE_LOOPS:
        raise PreviewRenderError(
            f"Asset {scene['candidate_id']} needs too many loops for {scene['shot_id']}: {loop_count}"
        )
    fade_out_start = max(0.0, duration - 0.18)
    filters = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT}:(iw-ow)/2:(ih-oh)/2,"
        f"fps={FPS},format=yuv420p,setsar=1,"
        f"fade=t=in:st=0:d=0.12,fade=t=out:st={fade_out_start:.3f}:d=0.18"
    )
    input_args = ["-stream_loop", str(loop_count)] if loop_count else []
    run([
        "ffmpeg", "-y", *input_args, "-i", str(asset_path), "-an",
        "-vf", filters, "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])


def render_preview(
    scene_manifest_path: Path,
    story_path: Path,
    asset_root: Path,
    audio_path: Path,
    captions_path: Path,
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    scene_manifest = json.loads(scene_manifest_path.read_text(encoding="utf-8"))
    story = json.loads(story_path.read_text(encoding="utf-8"))
    plan = build_scene_plan(scene_manifest, story)
    if not audio_path.is_file() or not captions_path.is_file():
        raise PreviewRenderError("Frozen narration.wav and narration.ass are required.")
    audio_seconds = media_duration(audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="because-of-this-v21-preview-") as raw:
        work = Path(raw)
        scene_files: list[Path] = []
        for index, scene in enumerate(plan, start=1):
            asset = scene["asset"]
            candidate_id = scene["candidate_id"]
            asset_path = asset_root / candidate_id / "candidate.mp4"
            if not asset_path.is_file():
                raise PreviewRenderError(f"Downloaded visual is missing: {asset_path}")
            expected_sha = str(asset.get("sha256", "")).lower()
            if sha256_file(asset_path).lower() != expected_sha:
                raise PreviewRenderError(f"Visual SHA-256 mismatch: {candidate_id}")
            scene_file = work / f"scene-{index:02d}.mp4"
            render_scene(scene, asset_path, scene_file)
            scene_files.append(scene_file)

        concat = work / "concat.txt"
        concat.write_text(
            "".join(f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for path in scene_files),
            encoding="utf-8",
        )
        scene_seconds = sum(float(item["duration"]) for item in plan)
        tail = max(0.0, audio_seconds - scene_seconds)
        subtitle_path = escape_filter_path(captions_path.resolve())
        video_filter = f"tpad=stop_mode=clone:stop_duration={tail:.3f},subtitles={subtitle_path}"
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-i", str(audio_path), "-vf", video_filter,
            "-map", "0:v:0", "-map", "1:a:0", "-t", f"{audio_seconds:.3f}",
            "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "24000",
            "-ac", "1", "-movflags", "+faststart", str(output_path),
        ], timeout=1800)

    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise PreviewRenderError(f"Preview output was not created: {output_path}")
    report = {
        "status": "V21_PREVIEW_RENDER_PASS",
        "mode": "preview",
        "episode_id": "episode-005",
        "scene_count": len(plan),
        "scene_duration_seconds": round(sum(float(item["duration"]) for item in plan), 3),
        "audio_duration_seconds": round(audio_seconds, 3),
        "tail_extension_seconds": round(max(0.0, audio_seconds - sum(float(item["duration"]) for item in plan)), 3),
        "output": str(output_path),
        "output_sha256": sha256_file(output_path),
        "production_enablement": False,
        "publication": "MANUAL_ONLY_NOT_RUN",
        "drive_written": False,
        "global_catalog_updated": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-manifest", type=Path, required=True)
    parser.add_argument("--story-architecture", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--captions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        render_preview(
            args.scene_manifest,
            args.story_architecture,
            args.asset_root,
            args.audio,
            args.captions,
            args.output,
            args.report,
        )
    except (OSError, ValueError, PreviewRenderError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "V21_PREVIEW_RENDER_BLOCKED", "failure": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
