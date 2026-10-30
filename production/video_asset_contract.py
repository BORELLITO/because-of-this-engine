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
from production.visual_semantics import require_visual_fit
from production.canonical_config import CanonicalConfigError, validate_canonical_manifest

SCHEMA_VERSION = "2.0"
SUPPORTED_SCHEMA_VERSIONS = {"2.0", "3.0.0"}
MIN_STORY_SECONDS = 60.0
MAX_STORY_SECONDS = 75.0
ALLOWED_MATCHES = {"EXACT", "NEAR", "EXPLANATORY", "SYMBOLIC", "ATMOSPHERE"}
ALLOWED_TRUTH = {"VERIFIED_FACT", "DOCUMENTED_RECONSTRUCTION", "EXPLAINED_PHENOMENON", "DECLARED_FICTION"}
ALLOWED_STATUSES = {"APPROVED", "REVIEW_REQUIRED", "REJECTED"}
ALLOWED_PROVIDERS = {"mixkit", "pixabay", "pexels", "drive", "original"}
ALLOWED_TRANSITIONS = {"hard_cut", "crossfade", "soft_dissolve", "dip_to_black", "motion_match"}
PREVIEW_ONLY_MODE = "draft-preview"
MATCH_THRESHOLDS = {"EXACT": 0.80, "NEAR": 0.68, "EXPLANATORY": 0.60, "SYMBOLIC": 0.55, "ATMOSPHERE": 0.55}
FINAL_PROVENANCE_FIELDS = (
    "author",
    "acquisition_timestamp",
    "original_filename",
    "mime_type",
    "duration_seconds",
    "width",
    "height",
    "filesize_bytes",
    "drive_file_id",
    "job_ownership",
    "scene_usage",
    "source_segment_in",
    "source_segment_out",
)


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


FINGERPRINT_VERSION = 2
FINGERPRINT_SAMPLE_FRACTIONS = (0.15, 0.35, 0.50, 0.65, 0.85)
FINGERPRINT_FRAME_WIDTH = 24
FINGERPRINT_FRAME_HEIGHT = 24
FINGERPRINT_FRAME_BYTES = FINGERPRINT_FRAME_WIDTH * FINGERPRINT_FRAME_HEIGHT * 3


def perceptual_hash(path: Path, *, duration: float | None = None) -> str:
    """Return a deterministic multi-frame visual fingerprint for an asset.

    The previous implementation fingerprinted only the first grayscale frame.
    Dark clips commonly begin with a near-black frame, collapsing unrelated
    animations to the same all-f hash and blocking valid episodes.  v2 samples
    five normalized positions across the clip, preserves coarse RGB structure,
    and quantizes the pixels before hashing for stability across ordinary
    encoding differences.  This is an anti-reuse signal, not a copyright
    identifier.
    """
    if duration is None:
        duration = float(ffprobe(path)["duration"])
    if duration <= 0:
        raise VideoContractError(f"Video duration is not positive: {path}")

    # Keep every sample inside the media.  The small margin avoids requesting
    # a frame exactly at EOF, which is unreliable across codecs.
    margin = min(0.05, duration / 10.0)
    timestamps = [
        min(max(duration * fraction, 0.0), max(0.0, duration - margin))
        for fraction in FINGERPRINT_SAMPLE_FRACTIONS
    ]
    normalized_frames: list[bytes] = []
    for timestamp in timestamps:
        command = [
            "ffmpeg", "-v", "error",
            "-ss", f"{timestamp:.3f}", "-i", str(path),
            "-frames:v", "1", "-an",
            "-vf",
            (
                f"scale={FINGERPRINT_FRAME_WIDTH}:{FINGERPRINT_FRAME_HEIGHT}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={FINGERPRINT_FRAME_WIDTH}:{FINGERPRINT_FRAME_HEIGHT}:"
                "(ow-iw)/2:(oh-ih)/2,format=rgb24"
            ),
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ]
        try:
            raw = subprocess.run(
                command, check=True, capture_output=True, timeout=60
            ).stdout
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise VideoContractError(
                f"Could not fingerprint video asset at {timestamp:.3f}s: {path}"
            ) from exc
        if len(raw) != FINGERPRINT_FRAME_BYTES:
            raise VideoContractError(
                f"Video asset has no readable fingerprint frame at {timestamp:.3f}s: {path}"
            )
        # Four-bit quantization suppresses tiny codec noise while retaining
        # enough spatial and chromatic structure to distinguish clips.
        normalized_frames.append(bytes(value >> 4 for value in raw))

    return hashlib.sha256(b"".join(normalized_frames)).hexdigest()


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
    try:
        video_duration = float(video.get("duration") or 0.0)
    except (TypeError, ValueError):
        video_duration = 0.0
    try:
        audio_duration = float(audio.get("duration") or 0.0) if audio else 0.0
    except (TypeError, ValueError):
        audio_duration = 0.0
    return {
        "duration": duration,
        "video_duration": video_duration,
        "audio_duration": audio_duration,
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


def _sample_strip_luma(path: Path, timestamp: float, crop_y: str) -> int:
    """Return mean luma for a normalized horizontal strip of a video frame."""
    command = [
        "ffmpeg", "-v", "error",
        "-ss", f"{timestamp:.3f}", "-i", str(path),
        "-frames:v", "1", "-an",
        "-vf", f"crop=iw:ih*0.08:0:{crop_y},scale=1:1,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    try:
        raw = subprocess.run(
            command, check=True, capture_output=True, timeout=60
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise VideoContractError(
            f"Could not inspect frame layout for video asset: {path}"
        ) from exc
    if not raw:
        raise VideoContractError(f"Video asset has no readable layout sample: {path}")
    return int(sum(raw) / len(raw))


def _validate_clean_frame_layout(
    path: Path,
    asset_id: str,
    duration: float,
    *,
    allow_disclosed_preview_compositor: bool = False,
) -> None:
    """Reject source files with baked black/letterbox bands before composition.

    The locked engine owns all framing, captions, branding and outro treatment.
    Source assets must therefore be clean footage, not an already-composed
    vertical card.  This catches persistent black bands in at least two of
    three normalized samples while allowing naturally dark footage.
    """
    if allow_disclosed_preview_compositor:
        # Draft preview may deliberately contain an editorial evidence layer
        # (for example a camera label or authored red emergency lamp).  It is
        # allowed only when the manifest explicitly discloses it and the
        # asset is already restricted to PREVIEW_ONLY. Final validation never
        # passes this escape hatch, so production still requires clean source.
        return
    margin = min(0.05, duration / 10.0)
    suspect_samples = 0
    for fraction in (0.15, 0.50, 0.85):
        timestamp = min(max(duration * fraction, 0.0), max(0.0, duration - margin))
        top = _sample_strip_luma(path, timestamp, "0")
        center = _sample_strip_luma(path, timestamp, "ih*0.46")
        bottom = _sample_strip_luma(path, timestamp, "ih-ih*0.08")
        if center >= 45 and (top <= 8 or bottom <= 8):
            suspect_samples += 1
    if suspect_samples >= 2:
        raise VideoContractError(
            f"Asset {asset_id} contains an embedded black/letterbox band or "
            "pre-composed layout; supply clean full-frame footage."
        )


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
    approved = record.get("rights_status") == "APPROVED" and record.get("approved_for_render") is True
    preview_only = (
        mode == PREVIEW_ONLY_MODE
        and record.get("rights_status") == "PREVIEW_ONLY"
        and record.get("approved_for_render") is False
        and record.get("preview_only") is True
        and str(record.get("preview_only_reason", "")).strip()
    )
    if not approved and not preview_only:
        raise VideoContractError(
            f"Asset {asset_id} is not approved for this render mode. "
            "Only explicit PREVIEW_ONLY assets may enter draft-preview."
        )
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
        segment_in = record.get("source_segment_in")
        segment_out = record.get("source_segment_out")
        if (
            isinstance(segment_in, bool)
            or not isinstance(segment_in, (int, float))
            or segment_in < 0
            or isinstance(segment_out, bool)
            or not isinstance(segment_out, (int, float))
            or segment_out <= segment_in
        ):
            raise VideoContractError(
                f"Asset {asset_id} source segment must satisfy 0 <= source_segment_in < source_segment_out."
            )
    if check_file:
        if not path.is_file():
            raise VideoContractError(f"Approved video asset is missing: {path}")
        actual = sha256_file(path)
        if actual.lower() != str(record["sha256"]).lower():
            raise VideoContractError(f"Asset {asset_id} sha256 does not match the downloaded file.")
        metadata = ffprobe(path)
        pixel_qc = ((record.get("visual_evidence") or {}).get("pixel_qc") or {})
        embedded_layout = str(pixel_qc.get("embedded_layout", "")).strip().lower()
        if embedded_layout in {"letterbox", "pillarbox", "baked_captions", "embedded_logo", "precomposed", "composited"}:
            disclosed_preview_compositor = (
                mode == PREVIEW_ONLY_MODE
                and record.get("preview_only") is True
                and pixel_qc.get("compositor_layers_disclosed") is True
            )
            if not disclosed_preview_compositor:
                raise VideoContractError(
                    f"Asset {asset_id} declares a forbidden embedded layout: {embedded_layout}."
                )
        else:
            disclosed_preview_compositor = (
                mode == PREVIEW_ONLY_MODE
                and record.get("preview_only") is True
                and pixel_qc.get("compositor_layers_disclosed") is True
            )
        _validate_clean_frame_layout(
            path,
            asset_id,
            float(metadata["duration"]),
            allow_disclosed_preview_compositor=disclosed_preview_compositor,
        )
        actual_phash = perceptual_hash(path, duration=float(metadata["duration"]))
        declared_phash = record.get("perceptual_hash")
        hydrated_phash = record.get("hydrated_perceptual_hash")
        for label, candidate in (("perceptual_hash", declared_phash), ("hydrated_perceptual_hash", hydrated_phash)):
            if candidate and not re.fullmatch(r"[0-9a-fA-F]{64}", str(candidate)):
                raise VideoContractError(f"Asset {asset_id} {label} must be 64 hexadecimal characters.")
        # Hydration recalculates decoded-pixel evidence with the runner's
        # actual FFmpeg.  SHA-256 remains the immutable source check; this
        # runtime value prevents harmless FFmpeg-version drift from blocking
        # an otherwise byte-identical approved asset.
        expected_phash = hydrated_phash or declared_phash
        if expected_phash and actual_phash.lower() != str(expected_phash).lower():
            field = "hydrated_perceptual_hash" if hydrated_phash else "perceptual_hash"
            raise VideoContractError(f"Asset {asset_id} {field} does not match the downloaded file.")
    else:
        metadata = {}
        actual_phash = None
    return {**record, "asset_id": asset_id, "path": path, "metadata": metadata, "animation_fingerprint": actual_phash}


def _validate_cinematic_grade(manifest: dict[str, Any], mode: str) -> None:
    """Fail closed when final output does not use the approved suspense look."""
    if mode != "final":
        return
    grade = manifest.get("color_grade")
    if not isinstance(grade, dict) or grade.get("enabled") is not True:
        raise VideoContractError("Final release requires an enabled color_grade.")
    if grade.get("preset") != "investigative_noir_suspense":
        raise VideoContractError("Final release requires the investigative_noir_suspense preset.")
    suspense = grade.get("cinematic_suspense")
    if not isinstance(suspense, dict) or suspense.get("enabled") is not True:
        raise VideoContractError("Final release requires the cinematic_suspense layer.")
    for key, lower, upper in (
        ("cool_shadows", 0.0, 0.10),
        ("warm_highlights", 0.0, 0.06),
    ):
        value = suspense.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= float(value) <= upper:
            raise VideoContractError(f"color_grade.cinematic_suspense.{key} is outside the safe range.")
    if grade.get("vignette") is not True:
        raise VideoContractError("Final release requires the suspense vignette.")
    for key, lower, upper in (
        ("brightness", -0.20, 0.20),
        ("contrast", 0.80, 1.30),
        ("saturation", 0.65, 1.15),
        ("gamma", 0.80, 1.15),
    ):
        value = grade.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= float(value) <= upper:
            raise VideoContractError(f"color_grade.{key} is outside the safe range.")


def _validate_loop(manifest: dict[str, Any], mode: str) -> None:
    """Require a continuity fade so the branded close never hard-cuts."""
    if mode != "final":
        return
    loop = manifest.get("loop")
    if not isinstance(loop, dict) or loop.get("enabled") is not True:
        raise VideoContractError("Final release requires an enabled branded loop outro.")
    if loop.get("transition") != "continuity_fade":
        raise VideoContractError("Final release requires loop.transition=continuity_fade.")
    if loop.get("logo_source") != "brand_logo_transparent":
        raise VideoContractError("Final release requires the transparent brand logo outro.")
    if loop.get("logo_anchor") != "center_center":
        raise VideoContractError("Final release requires loop.logo_anchor=center_center.")
    if loop.get("logo_width") != 820:
        raise VideoContractError("Final release requires loop.logo_width=820.")
    ranges = (
        ("outro_seconds", 0.8, 1.5),
        ("tail_fade_seconds", 0.25, 0.90),
        ("card_fade_in_seconds", 0.12, 0.60),
        ("card_fade_out_seconds", 0.18, 0.70),
        ("audio_fade_seconds", 0.35, 0.90),
    )
    for key, lower, upper in ranges:
        value = loop.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= float(value) <= upper:
            raise VideoContractError(
                f"loop.{key} must be between {lower:.2f}s and {upper:.2f}s for final release."
            )


def validate_manifest(manifest: dict[str, Any], episode_dir: Path, *, mode: str = "preview", check_files: bool = True, enforce_canonical: bool = True) -> dict[str, Any]:
    # Normalize once at the contract boundary.  All path checks below compare
    # absolute resolved paths; keeping a relative episode_dir here would make
    # the brand-logo containment check reject an otherwise valid manifest.
    episode_dir = episode_dir.resolve()
    canonical_report = None
    if enforce_canonical:
        try:
            canonical_report = validate_canonical_manifest(manifest)
        except CanonicalConfigError as exc:
            raise VideoContractError(str(exc)) from exc
    if manifest.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise VideoContractError("Video-only manifests must use schema_version 2.0 or 3.0.0.")
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
    script = manifest.get("script")
    if not isinstance(script, dict):
        raise VideoContractError("Manifest requires a canonical script object.")
    script_path = resolve_inside(episode_dir, script.get("path"), "Script path")
    script_text = ""
    if check_files:
        if not script_path.is_file():
            raise VideoContractError(f"Script file is missing: {script_path}")
        script_text = re.sub(r"\s+", " ", script_path.read_text(encoding="utf-8").lower()).strip()
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise VideoContractError("Manifest requires at least one video scene.")
    _validate_cinematic_grade(manifest, mode)
    _validate_loop(manifest, mode)
    try:
        clip_policy = clip_quantity_policy(manifest)
    except EditorialPolicyError as exc:
        raise VideoContractError(str(exc)) from exc
    seen_ids: set[str] = set()
    seen_asset_ids: set[str] = set()
    seen_paths: set[str] = set()
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
        for key in ("story_beat", "visual_intent", "visual_function", "visual_match", "visual_truth", "narration_excerpt"):
            _required_text(scene, key, f"Scene {scene_id}")
        # V7.1 is the canonical semantic source. The renderer still exposes
        # the older normalized fields internally, so derive only fields
        # that are losslessly represented by the V7 visual contract. The
        # human-approved match_score is deliberately never guessed.
        if manifest.get("schema_version") == "3.0.0":
            scene = dict(scene)
            v7_semantics = scene.get("visual_semantics") if isinstance(scene.get("visual_semantics"), dict) else {}
            anchors = v7_semantics.get("narrative_anchors") if isinstance(v7_semantics.get("narrative_anchors"), dict) else {}
            direct_required = anchors.get("direct_required") if isinstance(anchors.get("direct_required"), list) else []
            scene.setdefault("visual_intent", " | ".join(str(item).strip() for item in direct_required if str(item).strip()))
            scene.setdefault("visual_function", "literal_evidence")
            scene.setdefault("visual_match", "EXACT")
            scene.setdefault("visual_truth", story["truth_mode"])
            if "match_score" not in scene:
                scene["match_score"] = v7_semantics.get("match_score")

        visual_semantics = scene.get("visual_semantics")
        if not isinstance(visual_semantics, dict):
            raise VideoContractError(f"Scene {scene_id} requires visual_semantics.")
        if check_files:
            excerpt = re.sub(r"\s+", " ", str(scene["narration_excerpt"]).lower()).strip()
            if excerpt not in script_text:
                raise VideoContractError(
                    f"Scene {scene_id} narration_excerpt is not present in the canonical script."
                )
        if scene["visual_truth"] not in ALLOWED_TRUTH:
            raise VideoContractError(f"Scene {scene_id} has an invalid visual_truth mode.")
        if scene["visual_truth"] != story["truth_mode"]:
            raise VideoContractError(
                f"Scene {scene_id} visual_truth {scene['visual_truth']!r} "
                f"does not match story_profile.truth_mode {story['truth_mode']!r}."
            )
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
        try:
            visual_qa = require_visual_fit(scene, asset, mode=mode)
        except (ValueError, TypeError) as exc:
            raise VideoContractError(str(exc)) from exc
        actual_score = float(visual_qa.get("score", 0.0))
        if actual_score < required_score:
            raise VideoContractError(
                f"Scene {scene_id} actual semantic score is below the "
                f"{scene['visual_match']} threshold ({actual_score:.2f} < {required_score:.2f})."
            )
        path_key = str(asset["path"]).lower()
        if path_key in seen_paths:
            raise VideoContractError(
                f"Runtime asset path is repeated in episode {episode_id}: {path_key}"
            )
        seen_paths.add(path_key)
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
        normalized.append({
            **scene,
            "scene_id": scene_id,
            "duration": float(duration),
            "asset": asset,
            "visual_qa": visual_qa,
        })
    for index, scene in enumerate(normalized):
        transition = scene.get("transition", {})
        transition_type = str(transition.get("type", "crossfade"))
        if index > 0:
            previous_type = str(normalized[index - 1].get("transition", {}).get("type", "crossfade"))
            if transition_type == "dip_to_black" and previous_type == "dip_to_black":
                raise VideoContractError(
                    f"Scenes {normalized[index - 1]['scene_id']} and {scene['scene_id']} cannot use consecutive dip_to_black transitions."
                )
        if transition_type != "hard_cut" and float(transition.get("duration", 0.25)) > 0.30:
            raise VideoContractError(
                f"Scene {scene['scene_id']} transition is too long for short-form narrative pacing."
            )
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
    if captions.get("alignment_mode") not in {"forced_alignment", "audio_final_forced_alignment"} or captions.get("word_level_available") is not True:
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
    loop_logo_path = None
    loop = manifest.get("loop") or {}
    if loop.get("logo_enabled", False) is True:
        loop_logo_value = loop.get("logo_path")
        if not isinstance(loop_logo_value, str) or not loop_logo_value.strip():
            raise VideoContractError("loop.logo_path is required when loop.logo_enabled=true.")
        loop_logo_path = resolve_inside(episode_dir, loop_logo_value, "Loop logo path")
        if check_files and not loop_logo_path.is_file():
            raise VideoContractError(f"Loop logo file is missing: {loop_logo_path}")
    music = manifest.get("music")
    if not isinstance(music, dict):
        raise VideoContractError("Every v2 render requires a licensed suspense music object.")
    if mode == PREVIEW_ONLY_MODE:
        if (
            not music.get("license")
            or music.get("license_status") != "PREVIEW_ONLY"
            or music.get("preview_only") is not True
        ):
            raise VideoContractError(
                "draft-preview music must be explicitly marked license_status=PREVIEW_ONLY "
                "and preview_only=true."
            )
        if not isinstance(music.get("commercial_use"), bool):
            raise VideoContractError("draft-preview music requires an explicit commercial_use boolean.")
    elif not music.get("license") or music.get("commercial_use") is not True:
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
        width = brand.get("logo_width", 540)
        opacity = brand.get("logo_opacity", 0.82)
        margin = brand.get("logo_margin", 54)
        top = brand.get("logo_top", 72)
        if brand.get("logo_anchor") != "center_top":
            raise VideoContractError("Canonical brand logo anchor must be center_top.")
        if isinstance(width, bool) or not isinstance(width, (int, float)) or not 240 <= float(width) <= 720:
            raise VideoContractError("brand.logo_width must be between 240 and 720 pixels.")
        if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not 0.2 <= float(opacity) <= 1.0:
            raise VideoContractError("brand.logo_opacity must be between 0.2 and 1.0.")
        if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not 24 <= float(margin) <= 240:
            raise VideoContractError("brand.logo_margin must be between 24 and 240 pixels.")
        if isinstance(top, bool) or not isinstance(top, (int, float)) or not 24 <= float(top) <= 360:
            raise VideoContractError("brand.logo_top must be between 24 and 360 pixels.")
        if mode == "final" and float(width) < 540:
            raise VideoContractError("Final release requires the enlarged logo width of at least 540 pixels.")
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
        "loop_logo_path": loop_logo_path,
        "clip_policy": clip_policy,
        "clip_quantity_gate": quantity_report,
        "canonical_config": canonical_report,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise VideoContractError("Manifest must be a JSON object.")
    return value


