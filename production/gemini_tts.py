#!/usr/bin/env python3
"""Gemini TTS Charon adapter for the Because Of This V7.2 engine.

Uses the Gemini generateContent TTS REST contract with the repository's
GEMINI_API_KEY. The active voice is the prebuilt Charon voice; there is no
provider fallback.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production.canonical_config import CanonicalConfigError, validate_canonical_manifest

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
PROVIDER = "gemini_tts"
VOICE_NAME = "Charon"
DEFAULT_MODEL = "gemini-3.8-flash-tts"
DEFAULT_SAMPLE_RATE = 24000
# One provider request per workflow run: retries can consume daily Gemini quota.
MAX_ATTEMPTS = 1
TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}
MIN_NARRATION_SECONDS = 60.0
MAX_NARRATION_SECONDS = 75.0


class GeminiTTSError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GeminiTTSError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise GeminiTTSError("manifest must be an object")
    return value


def profile_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_canonical_manifest(manifest, source_label="Gemini TTS manifest")
    except CanonicalConfigError as exc:
        raise GeminiTTSError(str(exc)) from exc
    voice = manifest.get("voice") if isinstance(manifest.get("voice"), dict) else {}
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    for key in ("provider", "language", "language_code", "voice", "voice_name"):
        expected = voice.get("voice_name") if key == "voice" else voice.get(key)
        if key in narration and narration.get(key) != expected:
            raise GeminiTTSError(f"narration.{key} conflicts with the canonical voice profile")
    if voice.get("provider") != PROVIDER:
        raise GeminiTTSError("V7.2 narration provider must be gemini_tts; no silent fallback is allowed")
    name = str(voice.get("voice_name") or "").strip()
    language_code = str(voice.get("language_code") or "").strip()
    model = str(voice.get("model") or voice.get("model_or_voice_type") or DEFAULT_MODEL).strip()
    if name != VOICE_NAME or not language_code or not model:
        raise GeminiTTSError("Gemini TTS profile requires voice_name=Charon, language_code and model")
    return {
        "provider": PROVIDER,
        "language_code": language_code,
        "voice_name": name,
        "model": model,
        "sample_rate_hz": int(voice.get("sample_rate_hz", DEFAULT_SAMPLE_RATE)),
        "encoding": str(voice.get("encoding", "AUDIO_WAV")),
        "speaking_rate": float(voice.get("speaking_rate", 1.0)),
        "pitch": float(voice.get("pitch", 0.0)),
        "volume_gain_db": float(voice.get("volume_gain_db", 0.0)),
        "style": str(voice.get("style", "")),
        "profile_version": "7.2",
    }


def gemini_credentials_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _api_key() -> str:
    value = os.environ.get("GEMINI_API_KEY", "").strip()
    if not value:
        raise GeminiTTSError("GEMINI_API_KEY is not configured")
    return value


def _request_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=raw,
        method="POST",
        headers={
            "x-goog-api-key": _api_key(),
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise GeminiTTSError("Gemini returned a non-object JSON response")
            return payload
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            last_error = GeminiTTSError(f"Gemini TTS HTTP {exc.code}: {detail[:600]} (automatic retry disabled to protect provider quota)")
            if exc.code not in TRANSIENT_HTTP or attempt == MAX_ATTEMPTS:
                raise last_error from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = GeminiTTSError(f"Gemini TTS request failed (single-attempt policy): {exc}")
            if attempt == MAX_ATTEMPTS:
                raise last_error from exc
        time.sleep(2 ** (attempt - 1))
    raise last_error or GeminiTTSError("Gemini TTS request failed without a diagnostic")


def preflight(manifest: dict[str, Any]) -> dict[str, Any]:
    profile = profile_from_manifest(manifest)
    chunks = chunks_from_manifest(manifest, "")
    estimated_characters = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    configured_limit = int(os.environ.get("GEMINI_TTS_MAX_CHARACTERS", "10000"))
    if estimated_characters > configured_limit:
        raise GeminiTTSError(
            f"estimated TTS characters {estimated_characters} exceed configured budget {configured_limit}"
        )
    return {
        "status": "GEMINI_TTS_PREFLIGHT_PASS",
        "provider": PROVIDER,
        "model": profile["model"],
        "voice": profile["voice_name"],
        "estimated_characters": estimated_characters,
        "character_budget": configured_limit,
        "checked_at_utc": _now(),
    }


def build_ssml(text: str, *, break_before_ms: int = 0, substitutions: dict[str, str] | None = None) -> str:
    """Compatibility name used by the orchestrator; returns canonical TTS text."""
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        raise GeminiTTSError("cannot synthesize empty text")
    substitutions = substitutions or {}
    for source, alias in substitutions.items():
        clean = clean.replace(str(source), str(alias))
    return clean


def _wav_info(audio: bytes) -> tuple[int, int, int, float]:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            width = wav_file.getsampwidth()
            frames = wav_file.getnframes()
            if rate <= 0 or channels != 1 or width != 2:
                raise GeminiTTSError("Gemini TTS output must be mono 16-bit PCM")
            return rate, channels, width, frames / rate
    except (wave.Error, EOFError) as exc:
        raise GeminiTTSError("Gemini TTS output is not a valid WAV") from exc


def _extract_audio(response: dict[str, Any]) -> bytes:
    candidates = response.get("candidates")
    if not isinstance(candidates, list):
        raise GeminiTTSError("Gemini response did not contain candidates")
    for candidate in candidates:
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData") or part.get("inline_data")
            if isinstance(inline, dict) and isinstance(inline.get("data"), str):
                try:
                    return base64.b64decode(inline["data"], validate=True)
                except (ValueError, TypeError) as exc:
                    raise GeminiTTSError("Gemini audio payload was not valid base64") from exc
    raise GeminiTTSError("Gemini response did not contain inline audio data")


def synthesize_text(text: str, profile: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    style = profile.get("style") or "controlled, clear, restrained cinematic suspense"
    request_body = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": text,
                "speech_metadata": {"style": style},
            }],
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "responseFormat": {
                "audio": {
                    "mimeType": "AUDIO_WAV",
                    "sampleRate": profile["sample_rate_hz"],
                }
            },
            "speechConfig": {
                "voiceConfig": {"voice": profile["voice_name"]}
            },
        },
    }
    url = f"{API_ROOT}/models/{profile['model']}:generateContent"
    response = _request_json(url, request_body)
    audio = _extract_audio(response)
    rate, channels, width, duration = _wav_info(audio)
    request_id = _sha256_bytes(json.dumps({"text": text, "profile": profile}, sort_keys=True).encode("utf-8"))
    return audio, {
        "request_id": request_id,
        "provider_request_id": None,
        "profile": profile,
        "text_sha256": _sha256_bytes(text.encode("utf-8")),
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": width,
        "duration_seconds": round(duration, 3),
        "generated_at_utc": _now(),
    }


def _silence(sample_rate: int, milliseconds: int) -> bytes:
    frames = max(0, int(sample_rate * milliseconds / 1000))
    return b"\x00\x00" * frames


def _combine_wavs(items: list[tuple[bytes, int]], sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for audio, break_before_ms in items:
            if break_before_ms:
                output.writeframes(_silence(sample_rate, break_before_ms))
            with wave.open(io.BytesIO(audio), "rb") as source:
                if source.getframerate() != sample_rate or source.getnchannels() != 1 or source.getsampwidth() != 2:
                    raise GeminiTTSError("Gemini TTS chunks do not share one audio format")
                output.writeframes(source.readframes(source.getnframes()))
    return buffer.getvalue()


def synthesize_chunks(chunks: list[dict[str, Any]], output_dir: Path, profile: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    """Synthesize one full-script request to respect Gemini Free Tier rate limits.

    Beat boundaries remain in the manifest for alignment and editorial coverage,
    while the provider receives one exact narration transcript. This avoids
    eight near-simultaneous API calls and makes the operation idempotent.
    """
    if not chunks:
        raise GeminiTTSError("at least one narration beat is required")
    request_budget = os.environ.get("GEMINI_TTS_REQUEST_BUDGET", "1").strip()
    if request_budget != "1":
        raise GeminiTTSError(
            "GEMINI_TTS_REQUEST_BUDGET must be exactly 1; refusing to issue multiple provider requests"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        beat_id = str(chunk.get("beat_id") or f"beat-{index:03d}")
        text = build_ssml(str(chunk.get("text") or ""), substitutions=chunk.get("substitutions"))
        normalized.append({"beat_id": beat_id, "text": text, "break_before_ms": int(chunk.get("break_before_ms", 0) or 0)})
    full_text = " ".join(item["text"] for item in normalized)
    if dry_run:
        return {
            "status": "GEMINI_TTS_DRY_RUN",
            "provider": PROVIDER,
            "profile": profile,
            "request_count": 1,
            "chunks": [
                {"beat_id": item["beat_id"], "state": "pending_validation", "text": item["text"], "text_sha256": _sha256_bytes(item["text"].encode("utf-8"))}
                for item in normalized
            ],
            "combined": {"path": str(output_dir / "narration.wav"), "state": "pending_validation"},
        }
    combined_path = output_dir / "narration.wav"
    metadata_path = output_dir / "narration.json"
    request_key = _sha256_bytes(json.dumps({"text": full_text, "profile": profile}, sort_keys=True).encode("utf-8"))
    cached = None
    if combined_path.is_file() and metadata_path.is_file():
        try:
            cached = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            cached = None
    if cached and cached.get("request_id") == request_key and cached.get("audio_sha256") == _sha256_file(combined_path):
        audio = combined_path.read_bytes()
        metadata = {**cached, "state": "cached", "audio_path": str(combined_path)}
    elif combined_path.exists() or metadata_path.exists():
        raise GeminiTTSError("existing Gemini TTS narration does not match this request; refusing overwrite")
    else:
        audio, metadata = synthesize_text(full_text, profile)
        combined_path.write_bytes(audio)
        metadata.update({
            "beat_ids": [item["beat_id"] for item in normalized],
            "text": full_text,
            "audio_path": str(combined_path),
            "audio_sha256": _sha256_file(combined_path),
            "state": "generated",
            "request_count": 1,
        })
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    duration = _wav_info(audio)[3]
    if not MIN_NARRATION_SECONDS <= duration <= MAX_NARRATION_SECONDS:
        raise GeminiTTSError(f"combined narration duration {duration:.3f}s is outside the 60–75s contract")
    return {
        "status": "GEMINI_TTS_GENERATED",
        "provider": PROVIDER,
        "profile": profile,
        "request_count": 1,
        "chunks": [{"beat_id": item["beat_id"], "state": metadata.get("state"), "text": item["text"]} for item in normalized],
        "combined": {"path": str(combined_path), "sha256": _sha256_file(combined_path), "duration_seconds": duration},
    }

def chunks_from_manifest(manifest: dict[str, Any], script_text: str) -> list[dict[str, Any]]:
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    beats = narration.get("beats")
    if isinstance(beats, list) and beats:
        normalized: list[dict[str, Any]] = []
        for index, beat in enumerate(beats):
            item = dict(beat)
            if index > 0 and "break_before_ms" not in item:
                item["break_before_ms"] = 220
            normalized.append(item)
        return normalized
    return [{"beat_id": "narration-001", "text": script_text}]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        manifest = _load_manifest(args.manifest.resolve())
        if args.preflight:
            print(json.dumps(preflight(manifest), ensure_ascii=False))
            return 0
        profile = profile_from_manifest(manifest)
        script_text = args.input.read_text(encoding="utf-8") if args.input and args.input.is_file() else ""
        chunks = chunks_from_manifest(manifest, script_text)
        output_dir = args.output_dir or args.manifest.parent / "audio"
        print(json.dumps(synthesize_chunks(chunks, output_dir.resolve(), profile, dry_run=args.dry_run), ensure_ascii=False))
        return 0
    except (GeminiTTSError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"GEMINI TTS BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
