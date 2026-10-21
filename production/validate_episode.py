#!/usr/bin/env python3
"""Fail-closed validator for the independent BECAUSE OF THIS engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ValidationFailure(RuntimeError):
    """A release gate failed."""


PROTECTED_TARGETS = {"Capta Pronto", "Corte Fino", "Publisher", "Creator"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_path(manifest_dir: Path, relative: str, project_root: Path) -> Path:
    path = (manifest_dir / relative).resolve()
    if project_root not in path.parents and path != project_root:
        raise ValidationFailure(f"Path escapes independent project root: {relative}")
    if not path.is_file():
        raise ValidationFailure(f"Required file is missing: {relative}")
    return path


def parse_time(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    sec, fraction = (seconds.split(".") + ["0"])[:2]
    return int(hours) * 3600 + int(minutes) * 60 + int(sec) + int(fraction) / (10 ** len(fraction))


def normalize_words(value: str) -> list[str]:
    """Normalize prose while preserving word order for transcript identity."""
    value = re.sub(r"\{[^}]*\}", "", value).replace(r"\N", " ").replace(r"\n", " ")
    value = unicodedata.normalize("NFKC", value).lower()
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value)


def caption_events(path: Path) -> list[tuple[float, float, str]]:
    events: list[tuple[float, float, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 8)
        if len(fields) != 9:
            raise ValidationFailure(f"Malformed ASS Dialogue event: {raw_line}")
        start = parse_time(fields[1])
        end = parse_time(fields[2])
        if end <= start:
            raise ValidationFailure(f"Invalid caption interval: {raw_line}")
        events.append((start, end, fields[8]))
    if not events:
        raise ValidationFailure("Caption file has no Dialogue events.")
    events.sort(key=lambda item: item[0])
    for previous, current in zip(events, events[1:]):
        if current[0] < previous[1] - 0.001:
            raise ValidationFailure("Caption events overlap.")
    return events


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return json.loads(result.stdout)


def mean_volume(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", result.stderr)
    if not match:
        raise ValidationFailure("Could not measure narration volume.")
    return float(match.group(1))


def ebur128(path: Path) -> tuple[float, float]:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    integrated = re.findall(r"\bI:\s*(-?[0-9.]+) LUFS", result.stderr)
    peaks = re.findall(r"\bPeak:\s*(-?[0-9.]+) dBFS", result.stderr)
    if not integrated or not peaks:
        raise ValidationFailure("Could not measure integrated loudness and true peak.")
    return float(integrated[-1]), float(peaks[-1])


def declared_hash(path: Path, value: str | None, label: str, failures: list[str], checks: dict[str, Any]) -> None:
    actual = sha256(path)
    checks[f"{label}_sha256"] = actual
    if value and value != actual:
        failures.append(f"{label} hash does not match the manifest.")


def validate(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest_dir = manifest_path.parent
    project_root = manifest_dir.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checks: dict[str, Any] = {}

    if manifest.get("schema_version") != "1.0":
        failures.append("Unsupported or missing manifest schema_version.")
    if set(manifest.get("protected_targets", [])) != PROTECTED_TARGETS:
        failures.append("Protected target list is incomplete or altered.")

    script = require_path(manifest_dir, manifest["script"]["path"], project_root)
    actual_script_hash = sha256(script)
    checks["script_sha256"] = actual_script_hash
    if actual_script_hash != manifest["script"].get("sha256"):
        failures.append("Script hash does not match the manifest.")
    if manifest["script"].get("transcript_sha256") != actual_script_hash:
        failures.append("Transcript hash is not bound to the canonical script.")

    claims = require_path(manifest_dir, manifest["script"]["claims_path"], project_root)
    claims_data = json.loads(claims.read_text(encoding="utf-8"))
    claim_items = claims_data.get("claims", [])
    checks["claims"] = {"count": len(claim_items), "facts_verified": 0, "editorial_inferences": 0}
    if not claim_items:
        failures.append("Claims register is empty.")
    claim_ids: set[str] = set()
    for item in claim_items:
        claim_id = item.get("id", "<missing id>")
        if claim_id in claim_ids or not item.get("id"):
            failures.append(f"Claim id is missing or duplicated: {claim_id}")
        claim_ids.add(claim_id)
        if not item.get("claim") or not item.get("sources"):
            failures.append(f"Claim lacks text or source: {claim_id}")
        kind = item.get("kind", "FACT")
        status = item.get("status")
        if kind == "FACT":
            if status != "VERIFIED":
                failures.append(f"Fact claim is not VERIFIED: {claim_id}")
            else:
                checks["claims"]["facts_verified"] += 1
        elif kind == "EDITORIAL_INFERENCE":
            if status not in {"EDITORIAL_INFERENCE", "VERIFIED"}:
                failures.append(f"Editorial inference has invalid status: {claim_id}")
            else:
                checks["claims"]["editorial_inferences"] += 1
        else:
            failures.append(f"Unknown claim kind: {claim_id}")

    audio = require_path(manifest_dir, manifest["audio"]["path"], project_root)
    provenance = require_path(manifest_dir, manifest["audio"]["provenance_path"], project_root)
    provenance_data = json.loads(provenance.read_text(encoding="utf-8"))
    checks["provenance"] = {
        "voice": provenance_data.get("voice"),
        "model": provenance_data.get("model"),
        "model_verified": provenance_data.get("model_verified", False),
        "audio_sha256": provenance_data.get("audio_sha256"),
        "script_binding_status": provenance_data.get("script_binding_status", "UNKNOWN"),
    }
    actual_audio_hash = sha256(audio)
    if provenance_data.get("audio_sha256") != actual_audio_hash:
        failures.append("Audio provenance hash does not match the WAV.")
    if provenance_data.get("script_sha256") != actual_script_hash:
        failures.append("Audio provenance is not bound to the canonical transcript hash.")
    with wave.open(str(audio), "rb") as wav_file:
        audio_duration = wav_file.getnframes() / wav_file.getframerate()
        checks["audio"] = {
            "duration_seconds": round(audio_duration, 3),
            "sample_rate": wav_file.getframerate(),
            "channels": wav_file.getnchannels(),
            "sample_width": wav_file.getsampwidth(),
            "frames": wav_file.getnframes(),
        }
        if wav_file.getnchannels() != 1 or wav_file.getframerate() != 24000 or wav_file.getsampwidth() != 2:
            failures.append("Narration must be 24 kHz mono 16-bit PCM.")
        if audio_duration <= 1:
            failures.append("Narration is implausibly short.")
    checks["audio_mean_volume_db"] = mean_volume(audio)
    if checks["audio_mean_volume_db"] <= -60:
        failures.append("Narration appears silent.")

    captions = require_path(manifest_dir, manifest["captions"]["path"], project_root)
    declared_hash(captions, manifest["captions"].get("sha256"), "captions", failures, checks)
    if manifest["captions"].get("source_transcript_sha256") != actual_script_hash:
        failures.append("Captions are not bound to the canonical transcript hash.")
    events = caption_events(captions)
    caption_text = " ".join(event[2] for event in events)
    script_words = normalize_words(script.read_text(encoding="utf-8"))
    caption_words = normalize_words(caption_text)
    checks["transcript"] = {
        "script_word_count": len(script_words),
        "caption_word_count": len(caption_words),
        "exact_normalized_match": script_words == caption_words,
    }
    if script_words != caption_words:
        failures.append("Caption text does not match the canonical transcript.")
    caption_start, caption_end = events[0][0], events[-1][1]
    checks["captions"] = {"start": caption_start, "end": caption_end, "events": len(events)}
    if caption_start < 0 or caption_end > audio_duration + 0.5:
        failures.append("Caption time range falls outside the narration tolerance.")
    if caption_end < audio_duration - 0.8:
        failures.append("Captions end too early for the narration.")

    visual = require_path(manifest_dir, manifest["visual"]["source_motion"], project_root)
    declared_hash(visual, manifest["visual"].get("source_motion_sha256"), "visual_source_motion", failures, checks)
    visual_meta = probe(visual)
    visual_stream = next((item for item in visual_meta.get("streams", []) if item.get("codec_type") == "video"), None)
    if not visual_stream:
        failures.append("Visual source has no video stream.")
    else:
        checks["visual"] = {
            "width": visual_stream.get("width"),
            "height": visual_stream.get("height"),
            "fps": visual_stream.get("avg_frame_rate"),
        }
        if (visual_stream.get("width"), visual_stream.get("height")) != (1080, 1920):
            failures.append("Visual source is not 1080x1920.")

    music = require_path(manifest_dir, manifest["mix"]["music_path"], project_root)
    declared_hash(music, manifest["mix"].get("music_sha256"), "music", failures, checks)

    output = require_path(manifest_dir, manifest["output"]["path"], project_root)
    metadata = probe(output)
    streams = metadata.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    sound = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video or not sound:
        failures.append("Output must contain both video and audio streams.")
    else:
        video_duration = float(video.get("duration") or 0)
        sound_duration = float(sound.get("duration") or 0)
        checks["output"] = {
            "duration_seconds": round(float(metadata["format"]["duration"]), 3),
            "video_duration": round(video_duration, 3),
            "audio_duration": round(sound_duration, 3),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": video.get("avg_frame_rate"),
            "video_codec": video.get("codec_name"),
            "audio_codec": sound.get("codec_name"),
        }
        if (video.get("width"), video.get("height")) != (1080, 1920):
            failures.append("Output is not 1080x1920 vertical video.")
        if video.get("codec_name") != "h264" or sound.get("codec_name") != "aac":
            failures.append("Output codecs do not match the release contract.")
        if abs(video_duration - sound_duration) > 0.5 or abs(sound_duration - audio_duration) > 0.5:
            failures.append("Output and narration durations diverge by more than 0.5 seconds.")

    output_hash = sha256(output)
    checks["output_sha256"] = output_hash
    if manifest.get("output", {}).get("sha256") and manifest["output"]["sha256"] != output_hash:
        failures.append("Output hash does not match the manifest; render version changed.")

    integrated_lufs, true_peak = ebur128(output)
    checks["mix"] = {"integrated_lufs": integrated_lufs, "true_peak_dbfs": true_peak}
    if not -23.0 <= integrated_lufs <= -14.0:
        failures.append("Integrated loudness is outside the -23 to -14 LUFS technical range.")
    if true_peak > -0.5:
        failures.append("True peak exceeds -0.5 dBFS.")

    if manifest.get("approval_status") == "APPROVED":
        approval = manifest.get("approval", {})
        if approval.get("output_sha256") != output_hash:
            failures.append("APPROVED manifest lacks approval for this exact output hash.")
        if not approval.get("reviewed_at_utc") or not approval.get("reviewer"):
            failures.append("APPROVED manifest lacks reviewer and review timestamp.")

    report = {
        "validator_version": "2.0",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "episode_id": manifest.get("episode_id"),
        "status": "FAILED" if failures else "TECH_VALIDATED",
        "checks": checks,
        "failures": failures,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one independent BECAUSE OF THIS episode.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.manifest)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValidationFailure) as exc:
        report = {"status": "FAILED", "failures": [str(exc)]}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "TECH_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
