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

from production.editorial_policy import (
    EditorialPolicyError,
    clip_quantity_policy,
    validate_clip_quantity,
)

SCHEMA_VERSION = "2.0"
MIN_STORY_SECONDS = 60.0
MAX_STORY_SECONDS = 75.0
ALLOWED_MATCHES = {"EXACT", "NEAR", "EXPLANATORY", "SYMBOLIC", "ATMOSPHERE"}
ALLOWED_TRUTH = {"VERIFIED_FACT", "EXPLAINED_PHENOMENON", "DECLARED_FICTION"}
ALLOWED_STATUSES = {"APPROVED", "REVIEW_REQUIRED", "REJECTED"}
ALLOWED_PROVIDERS = {"mixkit", "pixabay", "pexels", "drive", "original"}
ALLOWED_TRANSITIONS = {"hard_cut", "crossfade", "soft_dissolve", "dip_to_black", "motion_match"}
MATCH_THRESHOLDS = {"EXACT": 0.80, "NEAR": 0.68, "EXPLANATORY": 0.60, "SYMBOLIC": 0.55, "ATMOSPHERE": 0.55}
FINAL_PROVENANCE_FIELDS = ("author", "acquisition_timestamp", "original_filename", "mime_type", "duration_seconds", "width", "height", "filesize_bytes", "drive_file_id", "job_ownership", "scene_usage")


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


def _rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        data = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not inspect media: {path}") from exc
    streams = data.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video:
        raise VideoContractError(f"Media has no video stream: {path}")
    try:
        duration = float(data.get("format", {}).get("duration") or video.get("duration"))
    except (TypeError, ValueError) as exc:
        raise VideoContractError(f"Media duration is unavailable: {path}") from exc
    if duration <= 0:
        raise VideoContractError(f"Media duration is not positive: {path}")
    return {
        "duration": duration,
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "codec": video.get("codec_name"),
        "pix_fmt": video.get("pix_fmt"),
        "fps": _rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "sample_rate": int(audio.get("sample_rate", 0)) if audio and str(audio.get("sample_rate", "0")).isdigit() else None,
        "channels": int(audio.get("channels", 0)) if audio else 0,
        "format_name": data.get("format", {}).get("format_name"),
        "size": int(data.get("format", {}).get("size", 0) or 0),
    }

def _required_text(record: dict[str, Any], key: str, label: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VideoContractError(f"{label} requires {key}.")
    return value.strip()


def validate_asset_record(record: dict[str, Any], base: Path, episode_id: str, *, mode: str = "preview", check_file: bool = True) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise VideoContractError("Each video asset record must be an object.")
    asset_id = _required_text(record, "asset_id", "Video asset")
    path = resolve_inside(base, record.get("path"), f"Asset {asset_id} path")
    provider = _required_text(record, "provider", f"Asset {asset_id}").lower()
    if provider not in ALLOWED_PROVIDERS:
        raise VideoContractError(f"Asset {asset_id} uses an unsupported video provider: {provider}")
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
    if mode == "final":
        for key in FINAL_PROVENANCE_FIELDS:
            value = record.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise VideoContractError(f"Asset {asset_id} is missing final provenance field: {key}.")
        if str(record.get("job_ownership")) != episode_id:
            raise VideoContractError(f"Asset {asset_id} provenance ownership does not match video_id.")
        if str(record.get("drive_file_id")).strip() == "":
            raise VideoContractError(f"Asset {asset_id} requires a Drive file ID for final release.")
        for key in ("duration_seconds", "width", "height", "filesize_bytes"):
            if isinstance(record.get(key), bool) or not isinstance(record.get(key), (int, float)) or record[key] <= 0:
                raise VideoContractError(f"Asset {asset_id} provenance field {key} must be positive.")
    if check_file:
        if not path.is_file():
            raise VideoContractError(f"Approved video asset is missing: {path}")
        actual = sha256_file(path)
        if actual.lower() != str(record["sha256"]).lower():
            raise VideoContractError(f"Asset {asset_id} sha256 does not match the downloaded file.")
        metadata = ffprobe(path)
        actual_phash = perceptual_hash(path)
        declared_phash = record.get("perceptual_hash")
        if declared_phash:
            if not re.fullmatch(r"[0-9a-fA-F]{64}", str(declared_phash)):
                raise VideoContractError(f"Asset {asset_id} perceptual_hash must be 64 hexadecimal characters.")
            if actual_phash.lower() != str(declared_phash).lower():
                raise VideoContractError(f"Asset {asset_id} perceptual_hash does not match the downloaded file.")
    else:
        metadata = {}
        actual_phash = None
    return {**record, "asset_id": asset_id, "path": path, "metadata": metadata, "animation_fingerprint": actual_phash}


def validate_manifest(manifest: dict[str, Any], episode_dir: Path, *, mode: str = "preview", check_files: bool = True) -> dict[str, Any]:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise VideoContractError(f"Video-only manifests must use schema_version {SCHEMA_VERSION}.")
    episode_id = _required_text(manifest, "video_id", "Manifest")
    job_id = manifest.get("job_id") or (manifest.get("job") or {}).get("job_id")
    if job_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,119}", str(job_id)):
        raise VideoContractError("Manifest job_id is unsafe or invalid.")
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
    try:
        clip_policy = clip_quantity_policy(manifest)
    except EditorialPolicyError as exc:
        raise VideoContractError(str(exc)) from exc
    seen_ids: set[str] = set()
    seen_asset_ids: set[str] = set()
    seen_hashes: set[str] = set()
    seen_sources: set[str] = set()
    seen_phashes: set[str] = set()
    normalized: list[dict[str, Any]] = []
    quantity_report = None
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
        if duration < clip_policy["min_scene_seconds"]:
            raise VideoContractError(
                f"Scene {scene_id} is too short; keep visual beats at or above "
                f"{clip_policy['min_scene_seconds']:.2f}s."
            )
        if duration > clip_policy["max_scene_seconds"]:
            raise VideoContractError(
                f"Scene {scene_id} is too long; split the visual beat below "
                f"{clip_policy['max_scene_seconds']:.2f}s."
            )
        for key in ("story_beat", "visual_intent", "visual_function", "visual_match", "visual_truth"):
            _required_text(scene, key, f"Scene {scene_id}")
        if scene["visual_match"] not in ALLOWED_MATCHES:
            raise VideoContractError(f"Scene {scene_id} has an invalid visual_match.")
        score = scene.get("match_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise VideoContractError(f"Scene {scene_id} requires match_score between 0 and 1.")
        required_score = MATCH_THRESHOLDS[scene["visual_match"]]
        if score < required_score:
            raise VideoContractError(
                f"Scene {scene_id} is below the {scene['visual_match']} semantic-match threshold "
                f"({score:.2f} < {required_score:.2f})."
            )
        transition = scene.get("transition", {"type": "crossfade", "duration": 0.25})
        if not isinstance(transition, dict):
            raise VideoContractError(f"Scene {scene_id} transition must be an object.")
        transition_type = str(transition.get("type", "crossfade"))
        transition_duration = transition.get("duration", 0.25)
        if transition_type not in ALLOWED_TRANSITIONS:
            raise VideoContractError(f"Scene {scene_id} has an unsupported transition type.")
        if isinstance(transition_duration, bool) or not isinstance(transition_duration, (int, float)) or transition_duration < 0:
            raise VideoContractError(f"Scene {scene_id} transition duration must be non-negative.")
        if transition_type == "hard_cut" and transition_duration > 0.08:
            raise VideoContractError(f"Scene {scene_id} hard_cut must remain effectively instantaneous.")
        if transition_duration >= duration:
            raise VideoContractError(f"Scene {scene_id} transition cannot consume the entire scene.")
        asset = validate_asset_record(scene.get("asset"), episode_dir, episode_id, mode=mode, check_file=check_files)
        for key, seen, label in (("asset_id", seen_asset_ids, "asset"), ("sha256", seen_hashes, "sha256")):
            value = str(asset[key]).lower()
            if value in seen:
                raise VideoContractError(f"Narrative {label} is repeated in episode {episode_id}: {value}")
            seen.add(value)
        source_url = str(asset.get("source_page_url", "")).strip().lower()
        if source_url and source_url in seen_sources:
            raise VideoContractError(f"Narrative source page is repeated in episode {episode_id}: {source_url}")
        if source_url:
            seen_sources.add(source_url)
        phash = asset.get("animation_fingerprint") or asset.get("perceptual_hash")
        if phash:
            phash = str(phash).lower()
            if phash in seen_phashes:
                raise VideoContractError(f"Narrative animation perceptually repeats in episode {episode_id}: {phash}")
            seen_phashes.add(phash)
        total += float(duration)
        normalized.append({**scene, "scene_id": scene_id, "duration": float(duration), "asset": asset})
    try:
        quantity_report = validate_clip_quantity(len(normalized), clip_policy)
    except EditorialPolicyError as exc:
        raise VideoContractError(str(exc)) from exc
    if total < MIN_STORY_SECONDS or total > MAX_STORY_SECONDS:
        raise VideoContractError(f"Scene timeline must be between {MIN_STORY_SECONDS:.0f}s and {MAX_STORY_SECONDS:.0f}s; got {total:.3f}s.")
    captions = manifest.get("captions")
    if not isinstance(captions, dict):
        raise VideoContractError("Manifest requires captions generated from the final narration.")
    caption_path = resolve_inside(episode_dir, captions.get("path"), "Captions path")
    if check_files and not caption_path.is_file():
        raise VideoContractError(f"Captions file is missing: {caption_path}")
    if captions.get("alignment_mode") != "forced_alignment" or captions.get("word_level_available") is not True:
        raise VideoContractError(
            "Every v2 render requires forced_alignment captions with real word timestamps."
        )
    alignment_sidecar = resolve_inside(
        episode_dir,
        captions.get("alignment_sidecar", "captions/narration.alignment.json"),
        "Caption alignment sidecar",
    )
    if check_files and not alignment_sidecar.is_file():
        raise VideoContractError(f"Caption alignment sidecar is missing: {alignment_sidecar}")
    music = manifest.get("music")
    if not isinstance(music, dict):
        raise VideoContractError("Every v2 render requires a licensed suspense music object.")
    if not music.get("license") or music.get("commercial_use") is not True:
        raise VideoContractError("Music requires explicit commercial_use=true and a licence.")
    volume = music.get("volume", 0.12)
    if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not 0.08 <= volume <= 0.18:
        raise VideoContractError("Music volume must be between 0.08 and 0.18 for audible voice-first mixing.")
    music_path = resolve_inside(episode_dir, music.get("path"), "Music path")
    if check_files and not music_path.is_file():
        raise VideoContractError(f"Licensed music file is missing: {music_path}")
    if mode == "final":
        research = manifest.get("research")
        if not isinstance(research, dict) or not isinstance(research.get("sources"), list) or not research["sources"]:
            raise VideoContractError("Final release requires research.sources with verified references.")
        if not str(research.get("accessed_at", "")).strip():
            raise VideoContractError("Final release requires research.accessed_at.")
        if research.get("confidence") not in {"HIGH", "MEDIUM"}:
            raise VideoContractError("Final release requires research confidence HIGH or MEDIUM.")
        editorial = manifest.get("editorial_qa")
        if not isinstance(editorial, dict) or editorial.get("status") != "PASS":
            raise VideoContractError("Final release requires editorial_qa.status=PASS after human review.")
        for key in ("reviewer", "reviewed_at"):
            if not str(editorial.get(key, "")).strip():
                raise VideoContractError(f"Final release requires editorial_qa.{key}.")
    brand = manifest.get("brand", {})
    if not isinstance(brand, dict):
        raise VideoContractError("brand must be an object.")

    brand_logo_path = None
    if brand.get("logo_enabled", False) is True:
        logo_value = brand.get("logo_path")
        if not isinstance(logo_value, str) or not logo_value.strip():
            raise VideoContractError("brand.logo_path is required when brand.logo_enabled=true.")
        logo_root = episode_dir.parent.parent if episode_dir.parent.name == "episodes" else episode_dir
        logo_candidate = (logo_root / logo_value).resolve()
        if logo_candidate != logo_root and logo_root not in logo_candidate.parents:
            raise VideoContractError("Brand logo path must remain inside the project root.")
        if check_files and not logo_candidate.is_file():
            raise VideoContractError(f"Brand logo file is missing: {logo_candidate}")
        width = brand.get("logo_width", 360)
        opacity = brand.get("logo_opacity", 0.82)
        margin = brand.get("logo_margin", 54)
        top = brand.get("logo_top", 72)
        if isinstance(width, bool) or not isinstance(width, (int, float)) or not 240 <= float(width) <= 720:
            raise VideoContractError("brand.logo_width must be between 240 and 720 pixels.")
        if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not 0.2 <= float(opacity) <= 1.0:
            raise VideoContractError("brand.logo_opacity must be between 0.2 and 1.0.")
        if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not 24 <= float(margin) <= 240:
            raise VideoContractError("brand.logo_margin must be between 24 and 240 pixels.")
        if isinstance(top, bool) or not isinstance(top, (int, float)) or not 24 <= float(top) <= 360:
            raise VideoContractError("brand.logo_top must be between 24 and 360 pixels.")
        brand_logo_path = logo_candidate

    return {
        "video_id": episode_id,
        "job_id": str(job_id) if job_id else None,
        "scenes": normalized,
        "audio_path": audio_path,
        "caption_path": caption_path,
        "music": music,
        "total_scene_duration": total,
        "brand": brand,
        "brand_logo_path": brand_logo_path,
        "clip_policy": clip_policy,
        "clip_quantity_gate": quantity_report,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise VideoContractError("Manifest must be a JSON object.")
    return value


