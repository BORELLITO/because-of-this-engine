#!/usr/bin/env python3
"""Render the creative Episode 005 preview with the locked channel profile.

This route is intentionally separate from final publication. A creative
preview carries the approved narration identity, cinematic-dread grade,
transparent wordmark, karaoke captions and a narration-free branded outro.
Missing creative inputs fail closed.
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
from production.active_visual_source_v21 import validate_scene_manifest
from production.scene_disclosures_v21 import load_for_preview, ffmpeg_nasa_overlay, ffmpeg_actor_overlay, NASA_ID, ACTOR_ID
from production.v21_visual_contract import (
    ACTIVE_WORD_COLOR as CONTRACT_ACTIVE_WORD_COLOR,
    CAPTION_MARGIN_V as CONTRACT_CAPTION_MARGIN_V,
    IN_VIDEO_LOGO_OPACITY as CONTRACT_IN_VIDEO_LOGO_OPACITY,
    IN_VIDEO_LOGO_WIDTH as CONTRACT_IN_VIDEO_LOGO_WIDTH,
    IN_VIDEO_LOGO_Y as CONTRACT_IN_VIDEO_LOGO_Y,
    OUTRO_SECONDS as CONTRACT_OUTRO_SECONDS,
    VIDEO_FPS as CONTRACT_VIDEO_FPS,
    VIDEO_HEIGHT as CONTRACT_VIDEO_HEIGHT,
    VIDEO_WIDTH as CONTRACT_VIDEO_WIDTH,
    validate_caption_ass,
    validate_logo_path,
)


MAX_SOURCE_LOOPS = 8
CREATIVE_PROFILE = "cinematic_dread_v73"
APPROVED_VOICE_PROVIDER = "gemini_tts"
APPROVED_VOICE_NAME = "Charon"
APPROVED_VOICE_MODEL = "gemini-3.8-flash-tts"

# These compiled literals are checked against production/v21_visual_contract.py
# by tests; keeping them explicit lets the immutable guard inspect the route
# without executing arbitrary imports.
FPS = 60
WIDTH = 1080
HEIGHT = 1920
IN_VIDEO_LOGO_Y = 190
IN_VIDEO_LOGO_WIDTH = 360
IN_VIDEO_LOGO_OPACITY = 0.90
OUTRO_SECONDS = 5.5
ACTIVE_WORD_COLOR = "#F04444"
CAPTION_MARGIN_V = 650


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
    assignments: dict[str, dict[str, Any]] = {}
    for item in scene_manifest.get("shot_assignments", []):
        if not isinstance(item, dict):
            continue
        assignment = item.get("assignment")
        if isinstance(assignment, dict):
            assignments[str(item.get("shot_id"))] = item
    plan: list[dict[str, Any]] = []
    for shot in story.get("shot_plan", []):
        shot_id = str(shot.get("shot_id", "")).strip()
        assignment_record = assignments.get(shot_id, {})
        assignment = assignment_record.get("assignment")
        assignment = assignment if isinstance(assignment, dict) else {}
        candidate_id = str(assignment.get("candidate_id", ""))
        asset = assets.get(candidate_id)
        if not asset:
            raise PreviewRenderError(f"No approved manifest asset assignment for {shot_id}")
        # Some historical manifest assets predate the continuity schema, while
        # their approved shot assignments already carry the reviewed metadata.
        # Hydrate only the missing asset field; never overwrite asset-level
        # metadata or invent tags for a candidate without assignment evidence.
        asset_for_scene = dict(asset)
        if not asset_for_scene.get("continuity_tags") and isinstance(
            (
                assignment_record.get("continuity_tags")
                or assignment.get("continuity_tags")
            ),
            dict,
        ):
            asset_for_scene["continuity_tags"] = (
                assignment_record.get("continuity_tags")
                or assignment.get("continuity_tags")
            )
        start, end = parse_range(str(shot.get("range", "")))
        plan.append({
            "shot_id": shot_id,
            "candidate_id": candidate_id,
            "duration": end - start,
            "role": str(shot.get("role", "")),
            "scene": shot,
            "asset": asset_for_scene,
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


def render_scene(scene: dict[str, Any], asset_path: Path, output: Path, disclosure: dict[str, Any] | None = None) -> None:
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
