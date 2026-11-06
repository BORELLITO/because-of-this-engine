#!/usr/bin/env python3
"""Render the creative Episode 005 preview with the locked channel profile.

This route is intentionally separate from final publication, but it is no
longer a voice-only technical smoke test. A creative preview must carry the
approved narration identity, suspense bed, cinematic-dread grade and brand
lockup. Missing creative inputs fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from production.visual_continuity import validate_sequence


FPS = 60
WIDTH = 1080
HEIGHT = 1920
MAX_SOURCE_LOOPS = 8
CREATIVE_PROFILE = "cinematic_dread_v73"
APPROVED_VOICE_PROVIDER = "gemini_tts"
APPROVED_VOICE_NAME = "Charon"
APPROVED_VOICE_MODEL = "gemini-3.8-flash-tts"


class PreviewRenderError(RuntimeError):
    pass


def run(command: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise PreviewRenderError(f"FFmpeg command failed: {detail[-2500:]}") from exc


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
    assignments: dict[str, str] = {}
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
            "scene": shot,
            "asset": asset,
        })
    if len(plan) != 16 or len({item["candidate_id"] for item in plan}) != 16:
        raise PreviewRenderError("Episode 005 preview requires 16 distinct assigned assets.")
    return plan


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def validate_voice_profile(profile_path: Path, audio_path: Path) -> dict[str, Any]:
    if not profile_path.is_file():
        raise PreviewRenderError("Approved Charon voice-profile.json is required.")
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreviewRenderError("Voice profile is not valid JSON.") from exc
    if not isinstance(profile, dict):
        raise PreviewRenderError("Voice profile must be a JSON object.")
    expected = {
        "provider": APPROVED_VOICE_PROVIDER,
        "voice_name": APPROVED_VOICE_NAME,
        "model": APPROVED_VOICE_MODEL,
    }
    for key, value in expected.items():
        if profile.get(key) != value:
            raise PreviewRenderError(f"Voice identity mismatch: {key} must be {value!r}.")
    if profile.get("identity_status") != "APPROVED_REFERENCE_MATCH":
        raise PreviewRenderError("Voice profile is not marked APPROVED_REFERENCE_MATCH.")
    if not audio_path.is_file():
        raise PreviewRenderError(f"Narration file is missing: {audio_path}")
    actual = sha256_file(audio_path)
    if str(profile.get("audio_sha256", "")).lower() != actual:
        raise PreviewRenderError("Voice profile audio_sha256 does not match narration.wav.")
    return {
        "provider": profile["provider"],
        "voice_name": profile["voice_name"],
        "model": profile["model"],
        "audio_sha256": actual,
        "identity_status": profile["identity_status"],
    }


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
        "scale=ceil(iw*1.045/2)*2:ceil(ih*1.045/2)*2,"
        f"crop={WIDTH}:{HEIGHT}:(iw-ow)/2:(ih-oh)/2,"
        "eq=brightness=-0.045:contrast=1.12:saturation=0.84:gamma=0.94,"
        "colorbalance=rs=-0.035:gs=-0.016:bs=0.035:rh=0.012:gh=0.006:bh=-0.012,"
        "unsharp=5:5:0.12:5:5:0.0,"
        "vignette=angle=PI/5.8:eval=frame,"
        f"fps={FPS},format=yuv420p,setsar=1,"
        f"fade=t=in:st=0:d=0.16,fade=t=out:st={fade_out_start:.3f}:d=0.18"
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
    music_path: Path,
    logo_path: Path,
    voice_profile_path: Path,
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    scene_manifest = json.loads(scene_manifest_path.read_text(encoding="utf-8"))
    story = json.loads(story_path.read_text(encoding="utf-8"))
    plan = build_scene_plan(scene_manifest, story)
    continuity_profile = scene_manifest.get("visual_continuity_profile")
    if continuity_profile:
        continuity_gate = validate_sequence(
            plan,
            continuity_profile,
            mode="preview",
        )
        if continuity_gate.get("status") != "PASS":
            reasons = continuity_gate.get("blocking_reasons", []) or continuity_gate.get("review_reasons", [])
            raise PreviewRenderError(
                "Visual continuity gate blocked preview: " + "; ".join(reasons)
            )
    else:
        # Legacy manifests remain renderable under their existing contracts;
        # adopting continuity is opt-in until the profile is present.
        continuity_gate = {
            "status": "NOT_CONFIGURED",
            "mode": "preview",
            "strict_preview_block": False,
        }
    if not captions_path.is_file():
        raise PreviewRenderError("Frozen narration.ass is required.")
    if not music_path.is_file():
        raise PreviewRenderError("Deterministic suspense bed is required.")
    if not logo_path.is_file():
        raise PreviewRenderError("Canonical Because Of This logo is required.")
    voice_profile = validate_voice_profile(voice_profile_path, audio_path)
    audio_seconds = media_duration(audio_path)
    if not 60.0 <= audio_seconds <= 80.0:
        raise PreviewRenderError(
            f"Creative narration duration must be between 60 and 80 seconds; got {audio_seconds:.3f}."
        )
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
            "".join(
                f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n"
                for path in scene_files
            ),
            encoding="utf-8",
        )
        scene_seconds = sum(float(item["duration"]) for item in plan)
        tail = max(0.0, audio_seconds - scene_seconds)
        final_start = max(0.0, audio_seconds - 3.2)
        fade_start = max(0.0, audio_seconds - 2.1)
        subtitle_path = escape_filter_path(captions_path.resolve())
        filter_complex = ";".join([
            f"[0:v]tpad=stop_mode=clone:stop_duration={tail:.3f},"
            f"fade=t=out:st={fade_start:.3f}:d=0.85,format=yuv420p[base]",
            f"[base]subtitles='{subtitle_path}'[captioned]",
            "[3:v]format=rgba,split=2[logo_top_raw][logo_outro_raw]",
            "[logo_top_raw]scale=210:-1:flags=lanczos,colorchannelmixer=aa=0.84[logo_top]",
            "[logo_outro_raw]scale=620:-1:flags=lanczos,colorchannelmixer=aa=0.94[logo_outro]",
            f"[captioned][logo_top]overlay=x=main_w-overlay_w-42:y=64:"
            f"enable='lt(t,{final_start:.3f})':eof_action=repeat[with_top]",
            f"[with_top][logo_outro]overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2:"
            f"enable='gte(t,{final_start:.3f})':eof_action=repeat[v]",
            "[1:a]aresample=48000,asetpts=PTS-STARTPTS,volume=1.0[voice]",
            f"[2:a]aresample=48000,volume=0.14,atrim=duration={audio_seconds:.3f},"
            "asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.6[bed]",
            "[bed][voice]sidechaincompress=threshold=0.055:ratio=8:attack=20:release=420:makeup=1[ducked]",
            "[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "loudnorm=I=-16:TP=-1.0:LRA=7,alimiter=limit=0.95[a]",
        ])
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-i", str(audio_path), "-stream_loop", "-1", "-i", str(music_path),
            "-loop", "1", "-framerate", "1", "-i", str(logo_path),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]", "-t", f"{audio_seconds:.3f}",
            "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-ac", "2", "-movflags", "+faststart", str(output_path),
        ], timeout=1800)

    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise PreviewRenderError(f"Preview output was not created: {output_path}")
    report = {
        "status": "V21_CREATIVE_PREVIEW_RENDER_PASS",
        "mode": "preview",
        "episode_id": "episode-005",
        "creative_profile": CREATIVE_PROFILE,
        "scene_count": len(plan),
        "scene_duration_seconds": round(sum(float(item["duration"]) for item in plan), 3),
        "audio_duration_seconds": round(audio_seconds, 3),
        "visual_continuity_gate": continuity_gate,
        "tail_extension_seconds": round(max(0.0, audio_seconds - sum(float(item["duration"]) for item in plan)), 3),
        "voice": voice_profile,
        "music": {
            "status": "DETERMINISTIC_SUSPENSE_BED_MIXED",
            "path": str(music_path),
            "target_lufs": -16,
            "sample_rate_hz": 48000,
        },
        "branding": {"logo_overlay": True, "final_center_lockup": True},
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
    parser.add_argument("--music", type=Path, required=True)
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--voice-profile", type=Path, required=True)
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
            args.music,
            args.logo,
            args.voice_profile,
            args.output,
            args.report,
        )
    except (OSError, ValueError, PreviewRenderError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "V21_CREATIVE_PREVIEW_RENDER_BLOCKED", "failure": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
