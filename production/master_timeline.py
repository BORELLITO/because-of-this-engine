#!/usr/bin/env python3
"""Master-clock contract and post-render QA for the independent authorial engine.

The module is intentionally conservative: it never invents word timestamps.
When no word-level aligner is available, it records a reviewed phrase-level
alignment and validates the real audio duration, frame conversion, anchors,
source fingerprint and final mux.
"""

from __future__ import annotations

import hashlib
import json
import math
import wave
from fractions import Fraction
from pathlib import Path
from typing import Any

FPS_DEFAULT = 25
SAMPLE_RATE_DEFAULT = 24_000
TIMELINE_VERSION = "1.0"
SYNC_TOLERANCE_FRAMES_DEFAULT = 3
ANCHOR_FRACTIONS = (0.0, 0.25, 0.50, 0.75, 1.0)


class MasterTimelineError(ValueError):
    """Raised when a hard-lock timeline contract fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_metadata(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frames = handle.getnframes()
            if channels != 1 or sample_width != 2 or sample_rate != SAMPLE_RATE_DEFAULT or frames <= 0:
                raise MasterTimelineError(
                    "Audio master must be mono, 16-bit PCM, 24 kHz and non-empty."
                )
            return {
                "sample_rate": sample_rate,
                "channels": channels,
                "sample_width_bytes": sample_width,
                "sample_count": frames,
                "duration_seconds": frames / sample_rate,
                "audio_sha256": sha256_file(path),
            }
    except (OSError, wave.Error) as exc:
        raise MasterTimelineError(f"Could not inspect audio master: {path}") from exc


def _resolve_inside(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise MasterTimelineError("Manifest paths must be non-empty strings.")
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise MasterTimelineError(f"Path escapes episode directory: {relative}")
    if not path.is_file():
        raise MasterTimelineError(f"Required source is missing: {relative}")
    return path


def source_fingerprint(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    episode_dir = manifest_path.parent.resolve()
    audio_path = _resolve_inside(episode_dir, manifest["audio"]["path"])
    caption_path = _resolve_inside(episode_dir, manifest["captions"]["path"])
    images = []
    for scene in manifest["scenes"]:
        image_path = _resolve_inside(episode_dir, scene["image"])
        images.append({
            "scene_id": scene["scene_id"],
            "path": scene["image"],
            "sha256": sha256_file(image_path),
        })
    sources = {
        "manifest_sha256": sha256_file(manifest_path),
        "audio_sha256": sha256_file(audio_path),
        "captions_sha256": sha256_file(caption_path),
        "images": images,
    }
    canonical = json.dumps(sources, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    sources["source_fingerprint"] = hashlib.sha256(canonical).hexdigest()
    return sources


def _frame_index(seconds: float, fps: int) -> int:
    return int(round(seconds * fps))


def _event_report(events: list[tuple[float, float, str]], fps: int) -> list[dict[str, Any]]:
    report = []
    for index, (start, end, text) in enumerate(events, start=1):
        start_frame = _frame_index(start, fps)
        end_frame = _frame_index(end, fps)
        report.append({
            "caption_id": f"C{index:03d}",
            "start_seconds": round(start, 4),
            "end_seconds": round(end, 4),
            "start_frame": start_frame,
            "end_frame": end_frame,
            "start_quantization_delta_frames": round(abs(start_frame / fps - start) * fps, 4),
            "end_quantization_delta_frames": round(abs(end_frame / fps - end) * fps, 4),
            "text": text,
        })
    return report


def _anchor_report(events: list[tuple[float, float, str]], duration: float, fps: int) -> list[dict[str, Any]]:
    output = []
    for fraction in ANCHOR_FRACTIONS:
        target = duration * fraction
        nearest = min(
            enumerate(events, start=1),
            key=lambda item: min(abs(target - item[1][0]), abs(target - item[1][1])),
        )
        index, event = nearest
        distance = min(abs(target - event[0]), abs(target - event[1]))
        output.append({
            "anchor": f"{int(fraction * 100)}%",
            "target_seconds": round(target, 4),
            "nearest_caption_id": f"C{index:03d}",
            "distance_seconds": round(distance, 4),
            "target_frame": _frame_index(target, fps),
        })
    return output


def build_timeline(
    manifest_path: Path,
    manifest: dict[str, Any],
    caption_events: list[tuple[float, float, str]],
    *,
    audio_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fps = int(manifest.get("fps", FPS_DEFAULT))
    sample_rate = int(manifest.get("audio_sample_rate", SAMPLE_RATE_DEFAULT))
    timebase = str(manifest.get("timebase", f"1/{fps}"))
    if fps <= 0 or sample_rate != SAMPLE_RATE_DEFAULT:
        raise MasterTimelineError("Manifest FPS/sample-rate lock is invalid.")
    if timebase != f"1/{fps}":
        raise MasterTimelineError("Manifest timebase must be the exact rational 1/FPS.")
    if manifest.get("timeline_version") != TIMELINE_VERSION:
        raise MasterTimelineError(f"timeline_version must be {TIMELINE_VERSION}.")
    audio_info = audio_info or audio_metadata(
        _resolve_inside(manifest_path.parent, manifest["audio"]["path"])
    )
    duration = float(audio_info["duration_seconds"])
    captions = manifest.get("captions", {})
    if captions.get("sync_policy") != "narration_locked":
        raise MasterTimelineError("Captions must declare sync_policy=narration_locked.")
    alignment_mode = captions.get("alignment_mode")
    if alignment_mode not in {"forced_alignment", "hybrid_alignment", "phrase_level_manual_reviewed"}:
        raise MasterTimelineError("Captions must declare a supported alignment_mode.")
    tolerance = int(captions.get("sync_tolerance_frames", SYNC_TOLERANCE_FRAMES_DEFAULT))
    if tolerance < 1 or tolerance > 6:
        raise MasterTimelineError("sync_tolerance_frames must stay between 1 and 6.")
    if not caption_events:
        raise MasterTimelineError("The master timeline requires captions.")
    if caption_events[0][0] < -0.001 or caption_events[-1][1] > duration + 0.5:
        raise MasterTimelineError("Caption interval falls outside the narration master.")
    end_gap = duration - caption_events[-1][1]
    end_tolerance = float(captions.get("end_tolerance_seconds", 0.10))
    if end_gap < -0.001 or end_gap > end_tolerance:
        raise MasterTimelineError(
            f"Caption end gap {end_gap:.3f}s exceeds the locked tolerance {end_tolerance:.3f}s."
        )
    event_report = _event_report(caption_events, fps)
    max_quantization = max(
        [item["start_quantization_delta_frames"] for item in event_report]
        + [item["end_quantization_delta_frames"] for item in event_report]
    )
    if max_quantization > 0.51:
        raise MasterTimelineError("Caption frame conversion exceeds half a frame.")
    timeline = {
        "timeline_version": TIMELINE_VERSION,
        "timebase": timebase,
        "fps": fps,
        "audio_sample_rate": sample_rate,
        "audio_duration_seconds": round(duration, 6),
        "audio_sample_count": int(audio_info["sample_count"]),
        "alignment_mode": alignment_mode,
        "word_level_available": bool(captions.get("word_level_available", False)),
        "word_level_status": (
            "available" if captions.get("word_level_available") else "not_available_phrase_alignment_used"
        ),
        "caption_count": len(caption_events),
        "caption_end_gap_seconds": round(end_gap, 6),
        "caption_tolerance_frames": tolerance,
        "captions": event_report,
        "anchors": _anchor_report(caption_events, duration, fps),
        "cumulative_drift": {
            "status": "NOT_DETECTABLE_WITHOUT_WORD_TIMESTAMPS",
            "checked_at_anchors": [item["anchor"] for item in _anchor_report(caption_events, duration, fps)],
            "reason": "Phrase-level reviewed alignment is explicit; no false word precision is claimed.",
        },
    }
    return timeline


def parse_rate(value: Any) -> Fraction | None:
    try:
        if not value:
            return None
        if isinstance(value, (int, float)):
            return Fraction(str(value))
        numerator, denominator = str(value).split("/", 1)
        return Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError):
        return None


def validate_final_media(
    output_metadata: dict[str, Any],
    *,
    expected_duration: float,
    expected_fps: int,
) -> dict[str, Any]:
    streams = output_metadata.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise MasterTimelineError("Final output must contain video and audio streams.")
    video_start = float(video.get("start_time") or 0)
    audio_start = float(audio.get("start_time") or 0)
    video_duration = float(video.get("duration") or 0)
    audio_duration_value = float(audio.get("duration") or 0)
    video_rate = parse_rate(video.get("avg_frame_rate"))
    declared_rate = parse_rate(video.get("r_frame_rate"))
    sample_rate = int(audio.get("sample_rate") or 0)
    if abs(video_start) > 0.05 or abs(audio_start) > 0.05:
        raise MasterTimelineError("Final mux has a non-zero start offset.")
    if video_rate != Fraction(expected_fps, 1) or declared_rate != Fraction(expected_fps, 1):
        raise MasterTimelineError("Final video must be constant FPS at the locked rate.")
    if sample_rate != SAMPLE_RATE_DEFAULT:
        raise MasterTimelineError("Final audio sample rate changed after alignment.")
    if abs(audio_duration_value - expected_duration) > 0.10 or abs(video_duration - expected_duration) > 0.10:
        raise MasterTimelineError("Final media duration drifted from the audio master.")
    return {
        "video_start_seconds": video_start,
        "audio_start_seconds": audio_start,
        "video_duration_seconds": round(video_duration, 6),
        "audio_duration_seconds": round(audio_duration_value, 6),
        "video_avg_frame_rate": str(video_rate),
        "video_declared_frame_rate": str(declared_rate),
        "audio_sample_rate": sample_rate,
        "vfr_detected": False,
        "post_render_sync": "PASS",
    }


def write_contract(path: Path, contract: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_contract(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MasterTimelineError(f"Could not read master contract: {path}") from exc
    if data.get("timeline_version") != TIMELINE_VERSION:
        raise MasterTimelineError("Master contract timeline version is stale.")
    return data
