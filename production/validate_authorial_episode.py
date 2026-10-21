#!/usr/bin/env python3
"""Release validator for the generic authorial episode pipeline.

This validator is intentionally independent from the legacy Mars validator.
It proves that a rendered output is complete, not merely that FFmpeg exited 0.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

SIZES = {"preview": (1080, 1920), "final": (2160, 3840)}


class ReleaseValidationError(RuntimeError):
    """Raised when an authorial release gate fails."""


def resolve_inside(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ReleaseValidationError("Manifest paths must be non-empty strings.")
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ReleaseValidationError(f"Path escapes episode directory: {relative}")
    return path


def require_file(base: Path, relative: str, label: str) -> Path:
    path = resolve_inside(base, relative)
    if not path.is_file():
        raise ReleaseValidationError(f"{label} is missing: {relative}")
    return path


def parse_ass_time(value: str) -> float:
    try:
        hours, minutes, seconds = value.strip().split(":")
        whole, fraction = (seconds.split(".") + ["0"])[:2]
        return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(fraction[:2].ljust(2, "0")) / 100
    except (ValueError, TypeError) as exc:
        raise ReleaseValidationError(f"Invalid ASS timestamp: {value}") from exc


def normalize_words(value: str) -> list[str]:
    value = re.sub(r"\{[^}]*\}", "", value)
    value = value.replace(r"\N", " ").replace(r"\n", " ")
    value = value.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value)


def caption_events(path: Path) -> list[tuple[float, float, str]]:
    events: list[tuple[float, float, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        if len(fields) < 10:
            raise ReleaseValidationError(f"Malformed ASS Dialogue line: {raw}")
        start = parse_ass_time(fields[1])
        end = parse_ass_time(fields[2])
        if end <= start:
            raise ReleaseValidationError(f"Caption interval is not positive: {raw}")
        events.append((start, end, fields[9]))
    if not events:
        raise ReleaseValidationError("Caption file has no Dialogue events.")
    events.sort(key=lambda item: item[0])
    for previous, current in zip(events, events[1:]):
        if current[0] < previous[1] - 0.001:
            raise ReleaseValidationError("Caption events overlap.")
    return events


def audio_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2 or handle.getframerate() != 24000:
                raise ReleaseValidationError("Audio must be mono 24 kHz 16-bit PCM WAV.")
            if handle.getnframes() <= 0:
                raise ReleaseValidationError("Audio is empty.")
            return handle.getnframes() / handle.getframerate()
    except (OSError, wave.Error) as exc:
        raise ReleaseValidationError(f"Audio could not be read: {path}") from exc


def validate_image(path: Path, minimum: int = 512) -> dict[str, Any]:
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            if width < minimum or height < minimum:
                raise ReleaseValidationError(f"Image is below {minimum}px: {path}")
            return {"width": width, "height": height, "format": image.format}
    except ReleaseValidationError:
        raise
    except Exception as exc:
        raise ReleaseValidationError(f"Image is unreadable: {path}") from exc


def ffprobe(path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=120,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError(f"Could not inspect rendered output: {path}") from exc


def validate(manifest_path: Path, mode: str) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    episode_dir = manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError("Could not read render manifest.") from exc

    if manifest.get("schema_version") != "1.1":
        raise ReleaseValidationError("Authorial release manifests must use schema_version 1.1.")
    video_id = manifest.get("video_id")
    if not isinstance(video_id, str) or not video_id.strip():
        raise ReleaseValidationError("Manifest requires video_id.")

    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ReleaseValidationError("Manifest requires at least one scene.")
    scene_ids: set[str] = set()
    scene_report: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ReleaseValidationError(f"Scene {index} is not an object.")
        scene_id = scene.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id.strip() or scene_id in scene_ids:
            raise ReleaseValidationError(f"Scene {index} has a missing or duplicate scene_id.")
        scene_ids.add(scene_id)
        image = require_file(episode_dir, scene.get("image"), f"Image {scene_id}")
        image_info = validate_image(image)
        sidecar = image.with_suffix(image.suffix + ".json")
        if manifest.get("require_provenance", True) and not sidecar.is_file():
            raise ReleaseValidationError(f"Image provenance sidecar is missing: {sidecar}")
        duration = scene.get("duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ReleaseValidationError(f"Scene {scene_id} has an invalid duration.")
        scene_report.append({"scene_id": scene_id, "image": str(image), "duration": float(duration), **image_info})

    audio = require_file(episode_dir, manifest.get("audio", {}).get("path"), "Audio")
    audio_seconds = audio_duration(audio)

    captions = manifest.get("captions")
    if not isinstance(captions, dict):
        raise ReleaseValidationError("External captions are mandatory for release.")
    caption_file = require_file(episode_dir, captions.get("path"), "Captions")
    events = caption_events(caption_file)
    if events[0][0] < 0 or events[-1][1] > audio_seconds + 0.5:
        raise ReleaseValidationError("Caption timing falls outside the narration.")
    if events[-1][1] < audio_seconds - 0.8:
        raise ReleaseValidationError("Captions end too early.")
    script = manifest.get("script")
    if script:
        script_file = require_file(episode_dir, script.get("path"), "Script")
        script_words = normalize_words(script_file.read_text(encoding="utf-8"))
        caption_words = normalize_words(" ".join(event[2] for event in events))
        if script_words != caption_words:
            raise ReleaseValidationError("Caption text does not match the canonical script.")

    output_spec = manifest.get("output")
    if not isinstance(output_spec, dict) or not output_spec.get("path"):
        raise ReleaseValidationError("Manifest requires output.path.")
    output_relative = str(output_spec["path"]).format(mode=mode)
    output = require_file(episode_dir, output_relative, "Rendered output")
    metadata = ffprobe(output)
    streams = metadata.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    sound = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or not sound:
        raise ReleaseValidationError("Rendered output must contain video and audio streams.")
    expected_width, expected_height = SIZES[mode]
    if (video.get("width"), video.get("height")) != (expected_width, expected_height):
        raise ReleaseValidationError(f"Output must be {expected_width}x{expected_height}.")
    if video.get("codec_name") != "h264" or sound.get("codec_name") != "aac":
        raise ReleaseValidationError("Output codecs must be H.264 video and AAC audio.")
    video_seconds = float(video.get("duration") or 0)
    sound_seconds = float(sound.get("duration") or 0)
    if video_seconds <= 0 or sound_seconds <= 0 or abs(sound_seconds - audio_seconds) > 0.6 or abs(video_seconds - sound_seconds) > 0.6:
        raise ReleaseValidationError("Rendered duration does not match narration.")
    return {
        "status": "FINAL_VALIDATED" if mode == "final" else "PREVIEW_VALIDATED",
        "video_id": video_id,
        "mode": mode,
        "scene_count": len(scene_report),
        "audio_duration_seconds": round(audio_seconds, 3),
        "caption_events": len(events),
        "output": str(output),
        "output_duration_seconds": round(sound_seconds, 3),
        "resolution": [expected_width, expected_height],
        "scenes": scene_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a rendered authorial episode.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=sorted(SIZES), required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.manifest, args.mode)
    except ReleaseValidationError as exc:
        print(f"RELEASE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
