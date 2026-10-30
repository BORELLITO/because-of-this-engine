#!/usr/bin/env python3
"""Read-only experimental final-audio gate for the MAIN conversation's TTS.

Works with the main branch's canonical declared provider (including Piper).
It neither generates a voice nor changes a manifest, audio, subtitles or V7
production gate. A passing technical WAV is not proof of narration correctness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path
from typing import Any


class AudioBoundaryError(ValueError):
    pass


def inspect_final_audio(
    wav_path: Path, manifest: dict[str, Any], active_policy: dict[str, Any]
) -> dict[str, Any]:
    voice = manifest.get("voice") if isinstance(manifest.get("voice"), dict) else {}
    provider = str(voice.get("provider") or "")
    active_provider = str(active_policy.get("voice_provider") or "")
    if not active_provider or not provider or provider != active_provider:
        raise AudioBoundaryError("narration provider does not match the canonical active provider")
    narrator = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    if narrator.get("provider") and narrator["provider"] != active_provider:
        raise AudioBoundaryError("narration beat provider differs from canonical active provider")
    if not wav_path.is_file():
        raise AudioBoundaryError("final audio WAV is missing")
    try:
        with wave.open(str(wav_path), "rb") as source:
            if source.getnchannels() != 1 or source.getsampwidth() != 2 or source.getframerate() != 24000:
                raise AudioBoundaryError("WAV must be mono, 16-bit PCM at 24000 Hz")
            duration = source.getnframes() / source.getframerate()
            if source.getcomptype() != "NONE":
                raise AudioBoundaryError("WAV must be uncompressed PCM")
    except (wave.Error, EOFError, OSError) as exc:
        raise AudioBoundaryError("invalid or unreadable final WAV") from exc
    limits = active_policy.get("render_contract") or {}
    lower = float(limits.get("duration_min_seconds", 60))
    upper = float(limits.get("duration_max_seconds", 75))
    if not 60 <= lower <= upper <= 75:
        raise AudioBoundaryError("canonical duration limits must remain within 60-75 seconds")
    if not lower <= duration <= upper:
        raise AudioBoundaryError(f"narration duration {duration:.3f}s is outside {lower:.0f}-{upper:.0f}s")
    digest = hashlib.sha256()
    with wav_path.open("rb") as handle:
        for buffer in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(buffer)
    return {
        "status": "TECHNICAL_AUDIO_PASS_ONLY",
        "active_provider": active_provider,
        "duration_seconds": round(duration, 3),
        "sample_rate_hz": 24000,
        "channels": 1,
        "sha256": digest.hexdigest(),
        "speech_content_verified": False,
        "captions_verified": False,
        "source_provenance_verified": False,
        "canonical_v7_gate_still_required": True,
        "no_tts_generated": True,
        "no_manifest_or_audio_modified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        result = inspect_final_audio(args.wav, manifest, policy)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("V72_TECHNICAL_AUDIO_PASS_ONLY")
        return 0
    except (OSError, json.JSONDecodeError, TypeError, AudioBoundaryError) as exc:
        print("V72_AUDIO_BOUNDARY_BLOCKED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
