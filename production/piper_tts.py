#!/usr/bin/env python3
"""Canonical local Piper neural TTS adapter for Because Of This V7.1."""
from __future__ import annotations
import argparse, hashlib, io, json, os, re, shutil, subprocess, tempfile, wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from production.canonical_config import CanonicalConfigError, validate_canonical_manifest

PROVIDER = "piper_tts_local"
DEFAULT_SAMPLE_RATE = 24000
MIN_NARRATION_SECONDS = 60.0
MAX_NARRATION_SECONDS = 75.0
MAX_ATTEMPTS = 2


class PiperTTSError(RuntimeError):
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
        raise PiperTTSError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise PiperTTSError("manifest must be an object")
    return value


def _piper_voice_class():
    try:
        from piper.voice import PiperVoice
    except ImportError as exc:
        raise PiperTTSError("piper-tts dependency is not installed") from exc
    return PiperVoice


def _synthesis_config(profile: dict):
    try:
        from piper.config import SynthesisConfig
    except ImportError as exc:
        raise PiperTTSError("piper-tts SynthesisConfig is unavailable") from exc
    speaking_rate = float(profile.get("speaking_rate", 1.0))
    if not 0.5 <= speaking_rate <= 2.0:
        raise PiperTTSError("speaking_rate must be between 0.5 and 2.0")
    volume_gain_db = float(profile.get("volume_gain_db", 0.0))
    return SynthesisConfig(
        length_scale=1.0 / speaking_rate,
        volume=10 ** (volume_gain_db / 20.0),
    )


def _model_dir() -> Path:
    value = os.environ.get("PIPER_MODEL_DIR", "").strip()
    if not value:
        raise PiperTTSError("PIPER_MODEL_DIR is required for the local voice model")
    return Path(value).resolve()


def _model_paths(profile: dict) -> tuple[Path, Path]:
    root = _model_dir()
    model = root / f"{profile['voice_name']}.onnx"
    config = root / f"{profile['voice_name']}.onnx.json"
    if not model.is_file() or not config.is_file():
        raise PiperTTSError(f"Piper voice model is missing: {model.name} and {config.name}")
    return model, config


def piper_tts_available() -> bool:
    try:
        _piper_voice_class()
        return True
    except PiperTTSError:
        return False


def profile_from_manifest(manifest: dict) -> dict:
    try:
        validate_canonical_manifest(manifest, source_label="Piper TTS manifest")
    except CanonicalConfigError as exc:
        raise PiperTTSError(str(exc)) from exc
    voice = manifest.get("voice") if isinstance(manifest.get("voice"), dict) else {}
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    for key in ("provider", "language", "language_code", "voice", "voice_name"):
        expected = voice.get("voice_name") if key == "voice" else voice.get(key)
        if key in narration and narration.get(key) != expected:
            raise PiperTTSError(f"narration.{key} conflicts with the canonical voice profile")
    if voice.get("provider") != PROVIDER:
        raise PiperTTSError("V7 narration provider must be piper_tts_local; no silent fallback is allowed")
    name = str(voice.get("voice_name") or "").strip()
    language = str(voice.get("language_code") or "").strip()
    if not name or not language:
        raise PiperTTSError("Piper TTS profile requires voice_name and language_code")
    return {
        "provider": PROVIDER,
        "language_code": language,
        "voice_name": name,
        "sample_rate_hz": int(voice.get("sample_rate_hz", DEFAULT_SAMPLE_RATE)),
        "encoding": str(voice.get("encoding", "LINEAR16")),
        "speaking_rate": float(voice.get("speaking_rate", 1.0)),
        "pitch": float(voice.get("pitch", 0.0)),
        "volume_gain_db": float(voice.get("volume_gain_db", 0.0)),
        "style": str(voice.get("style", "")),
        "profile_version": "7.1",
    }


def build_text(text: str, *, break_before_ms: int = 0, substitutions: dict | None = None) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        raise PiperTTSError("cannot synthesize empty text")
    for source, alias in (substitutions or {}).items():
        clean = clean.replace(str(source), str(alias))
    return clean


def _load_voice(profile: dict):
    model, config = _model_paths(profile)
    try:
        return _piper_voice_class().load(model, config_path=config)
    except Exception as exc:
        raise PiperTTSError(f"could not load Piper voice model {model.name}") from exc


def _wav_info(audio: bytes):
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            width = wav_file.getsampwidth()
            frames = wav_file.getnframes()
            if rate <= 0 or channels != 1 or width != 2:
                raise PiperTTSError("Piper output must be mono 16-bit PCM")
            return rate, channels, width, frames / rate
    except (wave.Error, EOFError) as exc:
        raise PiperTTSError("Piper output is not a valid WAV") from exc


def _prepend_silence(audio: bytes, milliseconds: int, sample_rate: int) -> bytes:
    if milliseconds <= 0:
        return audio
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            if source.getnchannels() != 1 or source.getsampwidth() != 2:
                raise PiperTTSError("Piper output must be mono 16-bit PCM")
            params = source.getparams()
            frames = source.readframes(source.getnframes())
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setparams(params)
            target.writeframes(b"\x00" * int(params.framerate * milliseconds / 1000) * 2)
            target.writeframes(frames)
        return output.getvalue()
    except (wave.Error, EOFError) as exc:
        raise PiperTTSError("Piper output is not a valid WAV") from exc


def _convert_to_canonical(source_path: Path, destination: Path, sample_rate: int) -> None:
    if shutil.which("ffmpeg") is None:
        raise PiperTTSError("ffmpeg is required to convert Piper audio to canonical WAV")
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source_path), "-ac", "1", "-ar", str(sample_rate),
        "-sample_fmt", "s16", str(destination),
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PiperTTSError("ffmpeg conversion failed to start or timed out") from exc
    if result.returncode:
        detail = (result.stderr or "unknown ffmpeg error").strip().replace("\n", " ")
        raise PiperTTSError(f"ffmpeg conversion failed: {detail[:300]}")


def synthesize_text(text: str, profile: dict, piper_voice, *, break_before_ms: int = 0):
    clean = build_text(text)
    syn_config = _synthesis_config(profile)
    last_error = None
    with tempfile.TemporaryDirectory(prefix="because-of-this-piper-") as directory:
        source_path = Path(directory) / "source.wav"
        canonical_path = Path(directory) / "canonical.wav"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with wave.open(str(source_path), "wb") as output:
                    piper_voice.synthesize_wav(clean, output, syn_config=syn_config)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise PiperTTSError(f"Piper synthesis failed after {MAX_ATTEMPTS} attempts") from last_error
        _convert_to_canonical(source_path, canonical_path, profile["sample_rate_hz"])
        audio = _prepend_silence(canonical_path.read_bytes(), break_before_ms, profile["sample_rate_hz"])
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


def preflight(manifest: dict) -> dict:
    profile = profile_from_manifest(manifest)
    model, config = _model_paths(profile)
    if shutil.which("ffmpeg") is None:
        raise PiperTTSError("ffmpeg is required for canonical 24 kHz WAV normalization")
    try:
        json.loads(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PiperTTSError(f"Piper voice configuration is unreadable: {config.name}") from exc
    voice = _load_voice(profile)
    del voice
    chunks = chunks_from_manifest(manifest, "")
    estimated = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    return {
        "status": "PIPER_TTS_PREFLIGHT_PASS",
        "provider": PROVIDER,
        "service": "local Piper neural TTS",
        "voice_profile": profile,
        "model_path": str(model),
        "model_config_path": str(config),
        "model_bytes": model.stat().st_size,
        "estimated_characters": estimated,
        "credential_policy": "no_api_key_or_billing_account_required",
        "network_policy": "model_download_is_explicit; synthesis_is_local",
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
                    raise PiperTTSError("Piper chunks do not share one audio format")
                target.writeframes(source.readframes(source.getnframes()))
    return output.getvalue()


def synthesize_chunks(chunks: list[dict], output_dir: Path, profile: dict, *, dry_run: bool = False) -> dict:
    if not chunks:
        raise PiperTTSError("at least one narration beat is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    wavs = []
    piper_voice = None if dry_run else _load_voice(profile)
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
            raise PiperTTSError(f"existing Piper chunk does not match this request; refusing overwrite: {path.name}")
        else:
            audio, metadata = synthesize_text(clean, profile, piper_voice, break_before_ms=pause)
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
            raise PiperTTSError(f"combined narration duration {duration:.3f}s is outside the 60–75s contract")
        combined = {"path": str(combined_path), "sha256": _sha256_file(combined_path), "duration_seconds": round(duration, 3)}
    return {
        "status": "PIPER_TTS_DRY_RUN" if dry_run else "PIPER_TTS_GENERATED",
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
            raise PiperTTSError("--input is required unless --preflight is used")
        source = args.input.read_text(encoding="utf-8").strip()
        if not source:
            raise PiperTTSError("narration input is empty")
        profile = profile_from_manifest(manifest)
        output = (args.output_dir or args.manifest.parent / "audio").resolve()
        report = synthesize_chunks(chunks_from_manifest(manifest, source), output, profile, dry_run=args.dry_run)
        (output / "piper-tts-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, PiperTTSError, json.JSONDecodeError) as exc:
        print(f"PIPER TTS BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
