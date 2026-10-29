#!/usr/bin/env python3
"""Google Cloud Text-to-Speech adapter for the Because Of This V7.1 engine.

The adapter deliberately uses the documented REST `text:synthesize` contract
with SSML and Application Default Credentials/OAuth.  Gemini, ElevenLabs and
other providers are not accepted by this module.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from production.canonical_config import CANONICAL_PROFILE, CanonicalConfigError, validate_canonical_manifest

API_ROOT = "https://texttospeech.googleapis.com/v1"
PROVIDER = "google_cloud_tts"
DEFAULT_SAMPLE_RATE = 24000
MAX_ATTEMPTS = 2
TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}
MIN_NARRATION_SECONDS = 60.0
MAX_NARRATION_SECONDS = 75.0


class CloudTTSError(RuntimeError):
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
        raise CloudTTSError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise CloudTTSError("manifest must be an object")
    return value


def profile_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_canonical_manifest(manifest, source_label="Cloud TTS manifest")
    except CanonicalConfigError as exc:
        raise CloudTTSError(str(exc)) from exc
    voice = manifest.get("voice") if isinstance(manifest.get("voice"), dict) else {}
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    for key in ("provider", "language_code", "voice_name"):
        if key in narration and narration.get(key) != voice.get(key):
            raise CloudTTSError(f"narration.{key} conflicts with the canonical voice profile")
    if voice.get("provider") != PROVIDER:
        raise CloudTTSError("V7 narration provider must be google_cloud_tts; no silent fallback is allowed")
    name = str(voice.get("voice_name") or "").strip()
    language_code = str(voice.get("language_code") or "").strip()
    if not name or not language_code:
        raise CloudTTSError("Cloud TTS profile requires voice_name and language_code")
    return {
        "provider": PROVIDER,
        "language_code": language_code,
        "voice_name": name,
        "ssml_gender": str(voice.get("ssml_gender", "MALE")),
        "sample_rate_hz": int(voice.get("sample_rate_hz", DEFAULT_SAMPLE_RATE)),
        "encoding": str(voice.get("encoding", "LINEAR16")),
        "speaking_rate": float(voice.get("speaking_rate", 1.0)),
        "pitch": float(voice.get("pitch", 0.0)),
        "volume_gain_db": float(voice.get("volume_gain_db", 0.0)),
        "style": str(voice.get("style", "")),
        "profile_version": "7.1",
    }


def _access_token() -> str:
    direct = os.environ.get("GOOGLE_TTS_ACCESS_TOKEN", "").strip()
    if direct:
        return direct
    try:
        import google.auth
        from google.auth.transport.requests import Request
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not credentials.valid or credentials.expired:
            credentials.refresh(Request())
        token = str(credentials.token or "").strip()
    except Exception as exc:  # google-auth has several concrete credential errors
        raise CloudTTSError("Google Cloud authentication unavailable; configure ADC/OAuth securely") from exc
    if not token:
        raise CloudTTSError("Google Cloud authentication produced no access token")
    return token


def _project_id() -> str:
    value = (os.environ.get("GOOGLE_TTS_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not value:
        raise CloudTTSError("GOOGLE_TTS_PROJECT_ID or GOOGLE_CLOUD_PROJECT is required")
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", value):
        raise CloudTTSError("Google Cloud project id has an invalid shape")
    return value


def _request_json(method: str, url: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _access_token()
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=raw,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "x-goog-user-project": _project_id(),
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            value = json.loads(payload.decode("utf-8"))
            if not isinstance(value, dict):
                raise CloudTTSError("Google Cloud returned a non-object JSON response")
            return value
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            last_error = CloudTTSError(f"Google Cloud HTTP {exc.code}: {detail[:400]}")
            if exc.code not in TRANSIENT_HTTP or attempt == MAX_ATTEMPTS:
                raise last_error from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = CloudTTSError(f"Google Cloud request failed: {exc}")
            if attempt == MAX_ATTEMPTS:
                raise last_error from exc
        time.sleep(2 ** (attempt - 1))
    raise last_error or CloudTTSError("Google Cloud request failed without a diagnostic")


def list_voices(profile: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"languageCode": profile["language_code"]})
    result = _request_json("GET", f"{API_ROOT}/voices?{query}")
    voices = result.get("voices") if isinstance(result.get("voices"), list) else []
    matches = [
        voice for voice in voices
        if isinstance(voice, dict) and profile["voice_name"] in (voice.get("name"), "")
    ]
    if not matches:
        raise CloudTTSError(
            f"approved Cloud TTS voice is unavailable: {profile['voice_name']} ({profile['language_code']})"
        )
    return {"status": "CLOUD_TTS_VOICE_PASS", "voice": profile["voice_name"], "language_code": profile["language_code"], "available": matches[0]}


def preflight(manifest: dict[str, Any]) -> dict[str, Any]:
    profile = profile_from_manifest(manifest)
    project = _project_id()
    chunks = chunks_from_manifest(manifest, "")
    estimated_characters = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    configured_limit = int(os.environ.get("GOOGLE_TTS_MAX_CHARACTERS", "5000"))
    if estimated_characters > configured_limit:
        raise CloudTTSError(
            f"estimated TTS characters {estimated_characters} exceed configured budget {configured_limit}"
        )
    voices = list_voices(profile)
    return {
        "status": "CLOUD_TTS_PREFLIGHT_PASS",
        "provider": PROVIDER,
        "project_id": project,
        "voice_profile": profile,
        "voice_check": voices,
        "estimated_characters": estimated_characters,
        "character_budget": configured_limit,
        "quota_policy": "fail_closed_before_synthesis",
        "checked_at_utc": _now(),
    }


def build_ssml(text: str, *, break_before_ms: int = 0, substitutions: dict[str, str] | None = None) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        raise CloudTTSError("cannot synthesize empty text")
    substitutions = substitutions or {}
    escaped = html.escape(clean, quote=False)
    for source, alias in substitutions.items():
        escaped = escaped.replace(html.escape(source, quote=False), f'<sub alias="{html.escape(alias, quote=True)}">{html.escape(source, quote=False)}</sub>')
    prefix = f'<break time="{int(break_before_ms)}ms"/>' if break_before_ms else ""
    return f"<speak>{prefix}{escaped}</speak>"


def _to_wav(audio: bytes, sample_rate: int) -> bytes:
    if audio.startswith(b"RIFF") and audio[8:12] == b"WAVE":
        return audio
    if len(audio) % 2:
        raise CloudTTSError("Cloud TTS returned an incomplete LINEAR16 payload")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(audio)
    return buffer.getvalue()


def _wav_info(audio: bytes) -> tuple[int, int, int, float]:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            width = wav_file.getsampwidth()
            frames = wav_file.getnframes()
            if rate <= 0 or channels != 1 or width != 2:
                raise CloudTTSError("Cloud TTS output must be mono 16-bit PCM")
            return rate, channels, width, frames / rate
    except (wave.Error, EOFError) as exc:
        raise CloudTTSError("Cloud TTS output is not a valid WAV") from exc


def synthesize_ssml(ssml: str, profile: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    request_body = {
        "input": {"ssml": ssml},
        "voice": {
            "languageCode": profile["language_code"],
            "name": profile["voice_name"],
            "ssmlGender": profile["ssml_gender"],
        },
        "audioConfig": {
            "audioEncoding": profile["encoding"],
            "sampleRateHertz": profile["sample_rate_hz"],
            "speakingRate": profile["speaking_rate"],
            "pitch": profile["pitch"],
            "volumeGainDb": profile["volume_gain_db"],
        },
    }
    response = _request_json("POST", f"{API_ROOT}/text:synthesize", body=request_body)
    encoded = response.get("audioContent")
    if not isinstance(encoded, str) or not encoded:
        raise CloudTTSError("Cloud TTS response did not contain audioContent")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise CloudTTSError("Cloud TTS audioContent was not valid base64") from exc
    audio = _to_wav(raw, profile["sample_rate_hz"])
    rate, channels, width, duration = _wav_info(audio)
    request_id = _sha256_bytes(json.dumps({"ssml": ssml, "profile": profile}, sort_keys=True).encode("utf-8"))
    return audio, {
        "request_id": request_id,
        "provider_request_id": None,
        "profile": profile,
        "ssml_sha256": _sha256_bytes(ssml.encode("utf-8")),
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": width,
        "duration_seconds": round(duration, 3),
        "generated_at_utc": _now(),
    }


def _combine_wavs(wavs: Iterable[bytes], sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for audio in wavs:
            with wave.open(io.BytesIO(audio), "rb") as source:
                if source.getframerate() != sample_rate or source.getnchannels() != 1 or source.getsampwidth() != 2:
                    raise CloudTTSError("Cloud TTS chunks do not share one audio format")
                output.writeframes(source.readframes(source.getnframes()))
    return buffer.getvalue()


def synthesize_chunks(chunks: list[dict[str, Any]], output_dir: Path, profile: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    if not chunks:
        raise CloudTTSError("at least one narration beat is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    wavs: list[bytes] = []
    for index, chunk in enumerate(chunks, start=1):
        beat_id = str(chunk.get("beat_id") or f"beat-{index:03d}")
        text = str(chunk.get("text") or "").strip()
        if not text:
            raise CloudTTSError(f"narration beat {beat_id} has empty text")
        ssml = build_ssml(text, break_before_ms=int(chunk.get("break_before_ms", 0) or 0), substitutions=chunk.get("substitutions"))
        if dry_run:
            records.append({"beat_id": beat_id, "state": "pending_validation", "ssml": ssml, "ssml_sha256": _sha256_bytes(ssml.encode("utf-8"))})
            continue
        path_safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", beat_id).strip("-") or f"beat-{index:03d}"
        path = output_dir / f"{index:03d}-{path_safe_id}.wav"
        metadata_path = output_dir / f"{index:03d}-{path_safe_id}.json"
        request_key = _sha256_bytes(json.dumps({"ssml": ssml, "profile": profile}, sort_keys=True).encode("utf-8"))
        cached = None
        if path.is_file() and metadata_path.is_file():
            try:
                cached = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                cached = None
        if cached and cached.get("request_id") == request_key and cached.get("audio_sha256") == _sha256_file(path):
            audio = path.read_bytes()
            metadata = {**cached, "state": "cached", "audio_path": str(path)}
        elif path.exists() or metadata_path.exists():
            raise CloudTTSError(f"existing Cloud TTS chunk does not match this request; refusing overwrite: {path.name}")
        else:
            audio, metadata = synthesize_ssml(ssml, profile)
            path.write_bytes(audio)
            metadata.update({"beat_id": beat_id, "text": text, "audio_path": str(path), "audio_sha256": _sha256_file(path), "state": "generated"})
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append(metadata)
        wavs.append(audio)
    combined = None
    if not dry_run:
        combined = _combine_wavs(wavs, profile["sample_rate_hz"])
        combined_path = output_dir / "narration.wav"
        combined_path.write_bytes(combined)
        combined_duration = _wav_info(combined)[3]
        if not MIN_NARRATION_SECONDS <= combined_duration <= MAX_NARRATION_SECONDS:
            raise CloudTTSError(
                f"combined narration duration {combined_duration:.3f}s is outside the 60–75s contract"
            )
        combined_info = {"path": str(combined_path), "sha256": _sha256_file(combined_path), "duration_seconds": combined_duration}
    else:
        combined_info = {"path": str(output_dir / "narration.wav"), "state": "pending_validation"}
    return {"status": "CLOUD_TTS_DRY_RUN" if dry_run else "CLOUD_TTS_GENERATED", "provider": PROVIDER, "profile": profile, "chunks": records, "combined": combined_info}


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
            print(json.dumps(preflight(manifest), ensure_ascii=False, indent=2))
            return 0
        if not args.input:
            raise CloudTTSError("--input is required unless --preflight is used")
        text = args.input.read_text(encoding="utf-8").strip()
        if not text:
            raise CloudTTSError("narration input is empty")
        profile = profile_from_manifest(manifest)
        output_dir = (args.output_dir or args.manifest.parent / "audio").resolve()
        report = synthesize_chunks(chunks_from_manifest(manifest, text), output_dir, profile, dry_run=args.dry_run)
        (output_dir / "cloud-tts-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, CloudTTSError, json.JSONDecodeError) as exc:
        print(f"CLOUD TTS BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
