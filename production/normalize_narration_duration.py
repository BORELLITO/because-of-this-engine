#!/usr/bin/env python3
"""Normalize generated narration into the v2 Shorts duration contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

TARGET_MIN_SECONDS = 60.0
TARGET_MAX_SECONDS = 75.0
TARGET_NORMALIZED_SECONDS = 74.5


class NarrationDurationError(RuntimeError):
    """Raised when generated narration cannot satisfy the v2 duration contract."""


def _duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2 or handle.getframerate() != 24000:
                raise NarrationDurationError("Narration must be mono 24 kHz 16-bit PCM WAV.")
            return handle.getnframes() / handle.getframerate()
    except (OSError, wave.Error) as exc:
        raise NarrationDurationError(f"Could not validate narration WAV: {path}") from exc


def _write_sidecar(path: Path, duration: float, original: float, factor: float | None) -> None:
    sidecar_path = path.with_suffix(path.suffix + ".json")
    metadata: dict[str, Any] = {}
    if sidecar_path.exists():
        metadata = json.loads(sidecar_path.read_text(encoding="utf-8"))
    metadata["duration_seconds"] = round(duration, 3)
    metadata["duration_contract"] = "60-75 seconds"
    if factor is not None:
        metadata["duration_normalization"] = {
            "applied": True,
            "original_duration_seconds": round(original, 3),
            "target_duration_seconds": TARGET_NORMALIZED_SECONDS,
            "tempo_factor": round(factor, 6),
            "method": "ffmpeg atempo before forced caption alignment",
        }
    else:
        metadata["duration_normalization"] = {"applied": False}
    sidecar_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(manifest_path: Path, ffmpeg_bin: str = "ffmpeg") -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_path = (manifest_path.parent / manifest["audio"]["path"]).resolve()
    original = _duration(audio_path)
    if original < TARGET_MIN_SECONDS:
        raise NarrationDurationError(
            f"Generated narration is {original:.3f}s, below the 60-75s contract; rewrite is required."
        )
    if original <= TARGET_MAX_SECONDS:
        _write_sidecar(audio_path, original, original, None)
        return {"status": "NARRATION_DURATION_PASS", "duration_seconds": round(original, 3), "normalized": False}

    factor = original / TARGET_NORMALIZED_SECONDS
    if factor >= 1.12:
        raise NarrationDurationError(
            f"Generated narration is {original:.3f}s and would require an excessive tempo change."
        )

    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=audio_path.parent, prefix=f".{audio_path.stem}.normalized.", suffix=".wav", delete=False
        ) as handle:
            temp_name = handle.name
        subprocess.run(
            [
                ffmpeg_bin,
                "-nostdin",
                "-y",
                "-i",
                str(audio_path),
                "-filter:a",
                f"atempo={factor:.6f}",
                "-ar",
                "24000",
                "-ac",
                "1",
                temp_name,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        normalized = _duration(Path(temp_name))
        if not TARGET_MIN_SECONDS <= normalized <= TARGET_MAX_SECONDS:
            raise NarrationDurationError(
                f"FFmpeg normalization produced {normalized:.3f}s, outside the 60-75s contract."
            )
        os.replace(temp_name, audio_path)
        temp_name = None
    except (OSError, subprocess.CalledProcessError) as exc:
        raise NarrationDurationError("FFmpeg could not normalize the narration WAV.") from exc
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass

    final_duration = _duration(audio_path)
    _write_sidecar(audio_path, final_duration, original, factor)
    return {
        "status": "NARRATION_DURATION_NORMALIZED",
        "duration_seconds": round(final_duration, 3),
        "original_duration_seconds": round(original, 3),
        "tempo_factor": round(factor, 6),
        "normalized": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_BIN", "ffmpeg"))
    args = parser.parse_args()
    try:
        print(json.dumps(normalize(args.manifest, args.ffmpeg), ensure_ascii=False))
        return 0
    except (NarrationDurationError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"NARRATION DURATION BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
