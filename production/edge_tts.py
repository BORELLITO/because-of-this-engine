#!/usr/bin/env python3
"""Canonical Microsoft Edge online TTS adapter for Because Of This V7.1."""
from __future__ import annotations
import argparse, asyncio, hashlib, io, json, os, re, shutil, subprocess, tempfile, wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from production.canonical_config import CanonicalConfigError, validate_canonical_manifest

PROVIDER = "microsoft_edge_tts"
DEFAULT_SAMPLE_RATE = 24000
MIN_NARRATION_SECONDS = 60.0
MAX_NARRATION_SECONDS = 75.0
MAX_ATTEMPTS = 2


class EdgeTTSError(RuntimeError):
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


def _load_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EdgeTTSError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise EdgeTTSError("manifest must be an object")
    return value


def _edge_module():
    try:
        import edge_tts
    except ImportError as exc:
        raise EdgeTTSError("edge-tts dependency is not installed") from exc
    return edge_tts


def edge_tts_available() -> bool:
    try:
        _edge_module()
        return True
    except EdgeTTSError:
        return False


def profile_from_manifest(manifest: dict) -> dict:
    try:
        validate_canonical_manifest(manifest, source_label="Edge TTS manifest")
    except CanonicalConfigError as exc:
        raise EdgeTTSError(str(exc)) from exc
    voice = manifest.get("voice") if isinstance(manifest.get("voice"), dict) else {}
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    for key in ("provider", "language", "language_code", "voice", "voice_name"):
        expected = voice.get("voice_name") if key == "voice" else voice.get(key)
        if key in narration and narration.get(key) != expected:
            raise EdgeTTSError(f"narration.{key} conflicts with the canonical voice profile")
    if voice.get("provider") != PROVIDER:
        raise EdgeTTSError("V7 narration provider must be microsoft_edge_tts; no silent fallback is allowed")
    name = str(voice.get("voice_name") or "").strip()
    language = str(voice.get("language_code") or "").strip()
    if not name or not language:
        raise EdgeTTSError("Edge TTS profile requires voice_name and language_code")
    rate = float(voice.get("speaking_rate", 1.0))
    pitch = float(voice.get("pitch", 0.0))
    volume = float(voice.get("volume_gain_db", 0.0))
    return {
        "provider": PROVIDER,
        "language_code": language,
        "voice_name": name,
        "sample_rate_hz": int(voice.get("sample_rate_hz", DEFAULT_SAMPLE_RATE)),
        "encoding": str(voice.get("encoding", "LINEAR16")),
        "speaking_rate": rate,
        "rate": f"{round((rate - 1) * 100):+d}%",
        "pitch": f"{pitch:+g}Hz",
        "volume_gain_db": volume,
        "volume": f"{volume:+g}dB",
        "style": str(voice.get("style", "")),
        "profile_version": "7.1",
    }


def build_text(text: str, *, break_before_ms: int = 0, substitutions: dict | None = None) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        raise EdgeTTSError("cannot synthesize empty text")
    for source, alias in (substitutions or {}).items():
        clean = clean.replace(str(source), str(alias))
    return clean


def _wav_info(audio: bytes):
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            width = wav_file.getsampwidth()
            frames = wav_file.getnframes()
            if rate <= 0 or channels != 1 or width != 2:
                raise EdgeTTSError("Edge TTS output must be mono 16-bit PCM")
            return rate, channels, width, frames / rate
    except (wave.Error, EOFError) as exc:
        raise EdgeTTSError("Edge TTS output is not a valid WAV") from exc


def _prepend_silence(audio: bytes, milliseconds: int, sample_rate: int) -> bytes:
    if milliseconds <= 0:
        return audio
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            if source.getframerate() != sample_rate or source.getnchannels() != 1 or source.getsampwidth() != 2:
                raise EdgeTTSError("Edge TTS output must be mono 16-bit PCM at 24 kHz")
            params = source.getparams()
            frames = source.readframes(source.getnframes())
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setparams(params)
            target.writeframes(b"\x00" * int(sample_rate * milliseconds / 1000) * 2)
            target.writeframes(frames)
        return output.getvalue()
    except (wave.Error, EOFError) as exc:
        raise EdgeTTSError("Edge TTS output is not a valid WAV") from exc


async def _save_mp3(text: str, profile: dict, destination: Path) -> None:
    edge_tts = _edge_module()
    communicator = edge_tts.Communicate(
        text,
        voice=profile["voice_name"],
        rate=profile["rate"],
        pitch=profile["pitch"],
        volume=profile["volume"],
    )
    await communicator.save(str(destination))


def _convert_mp3_to_wav(mp3_path: Path, wav_path: Path, sample_rate: int) -> None:
    if shutil.which("ffmpeg") is None:
        raise EdgeTTSError("ffmpeg is required to convert Edge TTS audio to canonical WAV")
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(mp3_path), "-ac", "1", "-ar", str(sample_rate),
        "-sample_fmt", "s16", str(wav_path),
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EdgeTTSError("ffmpeg conversion failed to start or timed out") from exc
    if result.returncode:
        detail = (result.stderr or "unknown ffmpeg error").strip().replace("\n", " ")
        raise EdgeTTSError(f"ffmpeg conversion failed: {detail[:300]}")


def synthesize_text(text: str, profile: dict, *, break_before_ms: int = 0):
    clean = build_text(text)
    last_error = None
    with tempfile.TemporaryDirectory(prefix="because-of-this-edge-tts-") as directory:
        mp3_path = Path(directory) / "chunk.mp3"
        wav_path = Path(directory) / "chunk.wav"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                asyncio.run(_save_mp3(clean, profile, mp3_path))
                last_error = None
                break
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise EdgeTTSError(f"Edge TTS synthesis failed after {MAX_ATTEMPTS} attempts") from last_error
        _convert_mp3_to_wav(mp3_path, wav_path, profile["sample_rate_hz"])
        audio = _prepend_silence(wav_path.read_bytes(), break_before_ms, profile["sample_rate_hz"])
    rate, channels, width, duration = _wav_info(audio)
    request_id = _sha256_bytes(json.dumps(
        {"text": clean, "break_before_ms": break_before_ms, "profile": profile},
        ensure_ascii=False, sort_keys=True,
    ).encode("utf-8"))
    return audio, {
        "request_id": request_id,
        "profile": profile,
        "text_sha256": _sha256_bytes(clean.encode("utf-8")),
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": width,
        "duration_seconds": round(duration, 3),
        "generated_at_utc": _now(),
    }


async def _list_voices():
    voices = await _edge_module().list_voices()
    return voices if isinstance(voices, list) else []


def preflight(manifest: dict) -> dict:
    profile = profile_from_manifest(manifest)
    chunks = chunks_from_manifest(manifest, "")
    estimated = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    limit = int(os.environ.get("EDGE_TTS_MAX_CHARACTERS", "5000"))
    if estimated > limit:
        raise EdgeTTSError(f"estimated TTS characters {estimated} exceed configured budget {limit}")
    try:
        voices = asyncio.run(_list_voices())
    except Exception as exc:
        raise EdgeTTSError("Edge TTS voice catalog is unavailable; retry later") from exc
    matches = [
        voice for voice in voices
        if isinstance(voice, dict)
        and str(voice.get("Name") or voice.get("name") or "").strip() == profile["voice_name"]
    ]
    if not matches:
        raise EdgeTTSError(f"approved Edge TTS voice is unavailable: {profile['voice_name']}")
    return {
        "status": "EDGE_TTS_PREFLIGHT_PASS",
        "provider": PROVIDER,
        "service": "Microsoft Edge online TTS",
        "voice_profile": profile,
        "voice_check": matches[0],
        "estimated_characters": estimated,
        "character_budget": limit,
        "credential_policy": "no_api_key_or_billing_account_required",
        "quota_policy": "fail_closed_on_service_unavailability",
        "checked_at_utc": _now(),
    }


def _combine_wavs(wavs: Iterable[bytes], sample_rate: int) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        for audio in wavs:
            with wave.open(io.BytesIO(audio), "rb") as source:
                if source.getframerate() != sample_rate or source.getnchannels() != 1 or source.getsampwidth() != 2:
                    raise EdgeTTSError("Edge TTS chunks do not share one audio format")
                target.writeframes(source.readframes(source.getnframes()))
    return output.getvalue()


def synthesize_chunks(chunks: list[dict], output_dir: Path, profile: dict, *, dry_run: bool = False) -> dict:
    if not chunks:
        raise EdgeTTSError("at least one narration beat is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    wavs = []
    for index, chunk in enumerate(chunks, start=1):
        beat_id = str(chunk.get("beat_id") or f"beat-{index:03d}")
        clean = build_text(str(chunk.get("text") or ""), substitutions=chunk.get("substitutions"))
        pause = int(chunk.get("break_before_ms", 0) or 0)
        request_key = _sha256_bytes(json.dumps(
            {"text": clean, "break_before_ms": pause, "profile": profile},
            ensure_ascii=False, sort_keys=True,
        ).encode("utf-8"))
        if dry_run:
            records.append({"beat_id": beat_id, "state": "pending_validation", "text": clean, "request_id": request_key})
            continue
        safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", beat_id).strip("-") or f"beat-{index:03d}"
        path = output_dir / f"{index:03d}-{safe_id}.wav"
        metadata_path = output_dir / f"{index:03d}-{safe_id}.json"
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
            raise EdgeTTSError(f"existing Edge TTS chunk does not match this request; refusing overwrite: {path.name}")
        else:
            audio, metadata = synthesize_text(clean, profile, break_before_ms=pause)
            path.write_bytes(audio)
            metadata.update({
                "beat_id": beat_id, "text": clean, "audio_path": str(path),
                "audio_sha256": _sha256_file(path), "state": "generated",
            })
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append(metadata)
        wavs.append(audio)
    if dry_run:
        combined = {"path": str(output_dir / "narration.wav"), "state": "pending_validation"}
    else:
        data = _combine_wavs(wavs, profile["sample_rate_hz"])
        combined_path = output_dir / "narration.wav"
        combined_path.write_bytes(data)
        duration = _wav_info(data)[3]
        if not MIN_NARRATION_SECONDS <= duration <= MAX_NARRATION_SECONDS:
            raise EdgeTTSError(f"combined narration duration {duration:.3f}s is outside the 60–75s contract")
        combined = {"path": str(combined_path), "sha256": _sha256_file(combined_path), "duration_seconds": round(duration, 3)}
    return {
        "status": "EDGE_TTS_DRY_RUN" if dry_run else "EDGE_TTS_GENERATED",
        "provider": PROVIDER, "profile": profile, "chunks": records, "combined": combined,
    }


def chunks_from_manifest(manifest: dict, script_text: str) -> list[dict]:
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    beats = narration.get("beats")
    if isinstance(beats, list) and beats:
        normalized = []
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
            raise EdgeTTSError("--input is required unless --preflight is used")
        source = args.input.read_text(encoding="utf-8").strip()
        if not source:
            raise EdgeTTSError("narration input is empty")
        profile = profile_from_manifest(manifest)
        output = (args.output_dir or args.manifest.parent / "audio").resolve()
        report = synthesize_chunks(chunks_from_manifest(manifest, source), output, profile, dry_run=args.dry_run)
        (output / "edge-tts-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, EdgeTTSError, json.JSONDecodeError) as exc:
        print(f"EDGE TTS BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
