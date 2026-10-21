#!/usr/bin/env python3
"""Fail-closed technical validator for the independent BECAUSE OF THIS engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ValidationFailure(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_path(manifest_root: Path, relative: str) -> Path:
    project_root = manifest_root.parent.resolve()
    path = (manifest_root / relative).resolve()
    if project_root not in path.parents and path != project_root:
        raise ValidationFailure(f"Path escapes episode root: {relative}")
    if not path.exists():
        raise ValidationFailure(f"Required file is missing: {relative}")
    return path


def parse_time(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    sec, fraction = (seconds.split(".") + ["0"])[:2]
    return int(hours) * 3600 + int(minutes) * 60 + int(sec) + int(fraction) / (10 ** len(fraction))


def caption_bounds(path: Path) -> tuple[float, float, int]:
    starts: list[float] = []
    ends: list[float] = []
    pattern = re.compile(r"^Dialogue:\s*\d+,([^,]+),([^,]+),")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        start = parse_time(match.group(1))
        end = parse_time(match.group(2))
        if end <= start:
            raise ValidationFailure(f"Invalid caption interval: {line}")
        starts.append(start)
        ends.append(end)
    if not starts:
        raise ValidationFailure("Caption file has no Dialogue events.")
    return min(starts), max(ends), len(starts)


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def mean_volume(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", result.stderr)
    if not match:
        raise ValidationFailure("Could not measure narration volume.")
    return float(match.group(1))


def validate(manifest_path: Path) -> dict[str, Any]:
    # The manifest lives in production/, while the approved script lives in
    # the sibling examples/ directory. Both stay inside the project root.
    root = manifest_path.parent.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checks: dict[str, Any] = {}

    if manifest.get("approval_status") == "APPROVED":
        failures.append("Manifest cannot claim APPROVED before human approval hash.")
    if len(manifest.get("protected_targets", [])) != 4:
        failures.append("Protected target list is incomplete.")

    script = require_path(root, manifest["script"]["path"])
    actual_script_hash = sha256(script)
    checks["script_sha256"] = actual_script_hash
    if actual_script_hash != manifest["script"]["sha256"]:
        failures.append("Script hash does not match the manifest.")

    claims = require_path(root, manifest["script"]["claims_path"])
    claims_data = json.loads(claims.read_text(encoding="utf-8"))
    claim_items = claims_data.get("claims", [])
    checks["claims"] = {"count": len(claim_items), "verified": 0}
    if not claim_items:
        failures.append("Claims register is empty.")
    for item in claim_items:
        if not item.get("id") or not item.get("claim") or not item.get("sources"):
            failures.append("Every claim must have id, text and at least one source.")
        if item.get("status") != "VERIFIED":
            failures.append(f"Claim is not VERIFIED: {item.get('id', '<missing id>')}")
        else:
            checks["claims"]["verified"] += 1

    audio = require_path(root, manifest["audio"]["path"])
    provenance = require_path(root, manifest["audio"]["provenance_path"])
    provenance_data = json.loads(provenance.read_text(encoding="utf-8"))
    checks["provenance"] = {
        "voice": provenance_data.get("voice"),
        "model": provenance_data.get("model"),
        "audio_sha256": provenance_data.get("audio_sha256"),
    }
    if provenance_data.get("audio_sha256") != sha256(audio):
        failures.append("Audio provenance hash does not match the WAV.")
    with wave.open(str(audio), "rb") as wav_file:
        audio_duration = wav_file.getnframes() / wav_file.getframerate()
        checks["audio"] = {
            "duration_seconds": round(audio_duration, 3),
            "sample_rate": wav_file.getframerate(),
            "channels": wav_file.getnchannels(),
            "frames": wav_file.getnframes(),
        }
        if wav_file.getnchannels() != 1 or wav_file.getframerate() != 24000:
            failures.append("Narration must be 24 kHz mono PCM.")
        if audio_duration <= 1:
            failures.append("Narration is implausibly short.")
    checks["audio_mean_volume_db"] = mean_volume(audio)
    if checks["audio_mean_volume_db"] <= -60:
        failures.append("Narration appears silent.")

    captions = require_path(root, manifest["captions"]["path"])
    caption_start, caption_end, caption_count = caption_bounds(captions)
    checks["captions"] = {"start": caption_start, "end": caption_end, "events": caption_count}
    if caption_start < 0 or caption_end > audio_duration + 0.5:
        failures.append("Caption time range falls outside the narration tolerance.")
    if caption_end < audio_duration - 0.8:
        failures.append("Captions end too early for the narration.")

    output = require_path(root, manifest["output"]["path"])
    metadata = probe(output)
    streams = metadata.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    sound = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video or not sound:
        failures.append("Output must contain both video and audio streams.")
    else:
        video_duration = float(video.get("duration", 0))
        sound_duration = float(sound.get("duration", 0))
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
        if abs(video_duration - audio_duration) > 0.5:
            failures.append("Video and audio durations diverge by more than 0.5 seconds.")

    checks["output_sha256"] = sha256(output)
    checks["manifest_output_sha256"] = manifest.get("output", {}).get("sha256")
    if checks["manifest_output_sha256"] and checks["output_sha256"] != checks["manifest_output_sha256"]:
        failures.append("Output hash does not match the manifest; render version changed.")
    if manifest.get("approval_status") == "APPROVED":
        if manifest.get("output", {}).get("approval_hash") != checks["output_sha256"]:
            failures.append("APPROVED manifest lacks an approval hash for this exact output.")

    report = {
        "validator_version": "1.0",
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
        report = validate(args.manifest.resolve())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError, ValidationFailure) as exc:
        report = {"status": "FAILED", "failures": [str(exc)]}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "TECH_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
