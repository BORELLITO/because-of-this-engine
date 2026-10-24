#!/usr/bin/env python3
"""Shared contract for Because of This Engine v2 video-only episodes.

The contract is intentionally fail-closed.  A scene is renderable only when
its approved video asset has a traceable source, an explicit licence, a
verified checksum and a fresh-use status.  Static narrative images are never
accepted by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2.0"
MIN_STORY_SECONDS = 60.0
MAX_STORY_SECONDS = 75.0
ALLOWED_MATCHES = {"EXACT", "NEAR", "EXPLANATORY", "SYMBOLIC", "ATMOSPHERE"}
ALLOWED_TRUTH = {"VERIFIED_FACT", "EXPLAINED_PHENOMENON", "DECLARED_FICTION"}
ALLOWED_STATUSES = {"APPROVED", "REVIEW_REQUIRED", "REJECTED"}


class VideoContractError(ValueError):
    """Raised when an episode violates the v2 contract."""


def resolve_inside(base: Path, value: str, label: str = "Path") -> Path:
    if not isinstance(value, str) or not value.strip():
        raise VideoContractError(f"{label} must be a non-empty relative path.")
    root = base.resolve()
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        raise VideoContractError(f"{label} escapes the episode directory: {value}")
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def perceptual_hash(path: Path) -> str:
    """Return a small deterministic video fingerprint from the first frame.

    This is deliberately not used as a copyright identifier.  It catches the
    common mistake of reusing the same clip under a different filename or
    crop.  FFmpeg is already a runtime dependency of the renderer.
    """
    command = [
        "ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1",
        "-vf", "scale=16:16,format=gray", "-f", "rawvideo", "-",
    ]
    try:
        raw = subprocess.run(command, check=True, capture_output=True, timeout=60).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise VideoContractError(f"Could not fingerprint video asset: {path}") from exc
    if len(raw) != 256:
        raise VideoContractError(f"Video asset has no readable first frame: {path}")
    average = sum(raw) / len(raw)
    bits = "".join("1" if value >= average else "0" for value in raw)
    return f"{int(bits, 2):064x}"


def ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        data = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not inspect video asset: {path}") from exc
    streams = data.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not video:
        raise VideoContractError(f"Asset has no video stream: {path}")
    try:
        duration = float(video.get("duration") or data.get("format", {}).get("duration"))
    except (TypeError, ValueError) as exc:
        raise VideoContractError(f"Asset duration is unavailable: {path}") from exc
    if duration <= 0:
        raise VideoContractError(f"Asset duration is not positive: {path}")
    return {"duration": duration, "width": int(video.get("width", 0)), "height": int(video.get("height", 0)), "codec": video.get("codec_name")}


def _required_text(record: dict[str, Any], key: str, label: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VideoContractError(f"{label} requires {key}.")
    return value.strip()


def validate_asset_record(record: dict[str, Any], base: Path, episode_id: str, *, check_file: bool = True) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise VideoContractError("Each video asset record must be an object.")
    asset_id = _required_text(record, "asset_id", "Video asset")
    path = resolve_inside(base, record.get("path"), f"Asset {asset_id} path")
    provider = _required_text(record, "provider", f"Asset {asset_id}").lower()
    if provider not in {"mixkit", "pixabay", "pexels", "drive", "authorial"}:
        raise VideoContractError(f"Asset {asset_id} uses an unsupported provider: {provider}")
    _required_text(record, "source_page_url", f"Asset {asset_id}")
    _required_text(record, "license", f"Asset {asset_id}")
    _required_text(record, "sha256", f"Asset {asset_id}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", record["sha256"]):
        raise VideoContractError(f"Asset {asset_id} sha256 must be 64 hexadecimal characters.")
    if record.get("rights_status") != "APPROVED" or record.get("approved_for_render") is not True:
        raise VideoContractError(f"Asset {asset_id} is not approved for render.")
    if record.get("reuse_status", "FRESH") == "PERMANENTLY_RETIRED":
        raise VideoContractError(f"Asset {asset_id} is permanently retired and cannot be reused.")
    if record.get("episode_id") not in {None, episode_id}:
        raise VideoContractError(f"Asset {asset_id} is assigned to another episode.")
    if check_file:
        if not path.is_file():
            raise VideoContractError(f"Approved video asset is missing: {path}")
        actual = sha256_file(path)
        if actual.lower() != str(record["sha256"]).lower():
            raise VideoContractError(f"Asset {asset_id} sha256 does not match the downloaded file.")
        metadata = ffprobe(path)
    else:
        metadata = {}
    return {**record, "asset_id": asset_id, "path": path, "metadata": metadata}


def validate_manifest(manifest: dict[str, Any], episode_dir: Path, *, mode: str = "preview", check_files: bool = True) -> dict[str, Any]:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise VideoContractError(f"Video-only manifests must use schema_version {SCHEMA_VERSION}.")
    episode_id = _required_text(manifest, "video_id", "Manifest")
    story = manifest.get("story_profile")
    if not isinstance(story, dict):
        raise VideoContractError("Manifest requires a story_profile object.")
    if story.get("truth_mode") not in ALLOWED_TRUTH:
        raise VideoContractError("story_profile.truth_mode is invalid.")
    for key in ("primary_emotion", "central_question", "visual_symbol"):
        _required_text(story, key, "story_profile")
    audio = manifest.get("audio")
    if not isinstance(audio, dict):
        raise VideoContractError("Manifest requires an audio object.")
    audio_path = resolve_inside(episode_dir, audio.get("path"), "Narration path")
    if check_files and not audio_path.is_file():
        raise VideoContractError(f"Narration file is missing: {audio_path}")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise VideoContractError("Manifest requires at least one video scene.")
    seen_ids: set[str] = set()
    seen_asset_ids: set[str] = set()
    seen_hashes: set[str] = set()
    seen_phashes: set[str] = set()
    normalized: list[dict[str, Any]] = []
    total = 0.0
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise VideoContractError(f"Scene {index} must be an object.")
        scene_id = _required_text(scene, "scene_id", f"Scene {index}")
        if scene_id in seen_ids:
            raise VideoContractError(f"Duplicate scene_id: {scene_id}")
        seen_ids.add(scene_id)
        if "image" in scene or "image_path" in scene:
            raise VideoContractError(f"Scene {scene_id} contains a forbidden narrative image field.")
        duration = scene.get("duration")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            raise VideoContractError(f"Scene {scene_id} requires a positive duration.")
        if duration > 20:
            raise VideoContractError(f"Scene {scene_id} is too long; split the visual beat below 20 seconds.")
        for key in ("story_beat", "visual_intent", "visual_function", "visual_match", "visual_truth"):
            _required_text(scene, key, f"Scene {scene_id}")
        if scene["visual_match"] not in ALLOWED_MATCHES:
            raise VideoContractError(f"Scene {scene_id} has an invalid visual_match.")
        score = scene.get("match_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise VideoContractError(f"Scene {scene_id} requires match_score between 0 and 1.")
        if score < 0.55 and scene["visual_match"] not in {"SYMBOLIC", "ATMOSPHERE"}:
            raise VideoContractError(f"Scene {scene_id} is below the semantic-match threshold.")
        asset = validate_asset_record(scene.get("asset"), episode_dir, episode_id, check_file=check_files)
        for key, seen, label in (("asset_id", seen_asset_ids, "asset"), ("sha256", seen_hashes, "sha256")):
            value = str(asset[key]).lower()
            if value in seen:
                raise VideoContractError(f"Narrative {label} is repeated in episode {episode_id}: {value}")
            seen.add(value)
        if asset.get("perceptual_hash"):
            phash = str(asset["perceptual_hash"]).lower()
            if phash in seen_phashes:
                raise VideoContractError(f"Narrative animation perceptually repeats in episode {episode_id}: {phash}")
            seen_phashes.add(phash)
        total += float(duration)
        normalized.append({**scene, "scene_id": scene_id, "duration": float(duration), "asset": asset})
    if total < MIN_STORY_SECONDS or total > MAX_STORY_SECONDS:
        raise VideoContractError(f"Scene timeline must be between {MIN_STORY_SECONDS:.0f}s and {MAX_STORY_SECONDS:.0f}s; got {total:.3f}s.")
    captions = manifest.get("captions")
    if not isinstance(captions, dict):
        raise VideoContractError("Manifest requires captions generated from the final narration.")
    caption_path = resolve_inside(episode_dir, captions.get("path"), "Captions path")
    if check_files and not caption_path.is_file():
        raise VideoContractError(f"Captions file is missing: {caption_path}")
    music = manifest.get("music")
    if mode == "final" and not isinstance(music, dict):
        raise VideoContractError("Final release requires a licensed suspense music object.")
    if music is not None:
        if not isinstance(music, dict) or not music.get("license") or music.get("commercial_use") is not True:
            raise VideoContractError("Music requires explicit commercial_use=true and a licence.")
        volume = music.get("volume", 0.06)
        if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not 0 < volume <= 0.18:
            raise VideoContractError("Music volume must be between 0 and 0.18 for voice-first mixing.")
        music_path = resolve_inside(episode_dir, music.get("path"), "Music path")
        if check_files and not music_path.is_file():
            raise VideoContractError(f"Licensed music file is missing: {music_path}")
    brand = manifest.get("brand", {})
    if not isinstance(brand, dict):
        raise VideoContractError("brand must be an object.")
    return {
        "video_id": episode_id,
        "scenes": normalized,
        "audio_path": audio_path,
        "caption_path": caption_path,
        "music": music,
        "total_scene_duration": total,
        "brand": brand,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise VideoContractError("Manifest must be a JSON object.")
    return value


