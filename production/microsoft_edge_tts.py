#!/usr/bin/env python3
"""Microsoft Edge online TTS adapter for the Because Of This V2.1 candidate."""
from __future__ import annotations
import argparse, asyncio, hashlib, io, json, os, re, shutil, subprocess, tempfile, wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PROVIDER = "microsoft_edge_tts"
DEFAULT_SAMPLE_RATE = 24000
MIN_NARRATION_SECONDS = 60.0
MAX_NARRATION_SECONDS = 80.0
MAX_ATTEMPTS = 1  # one synthesis submission; no automatic retry or duplicate request
V21_MODEL = "edge_neural"
V21_VOICE_NAME = "en-US-ChristopherNeural"
V21_PROFILE_VERSION = "2.1"


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
    """Read the active V2.1 narration profile from a story or production record."""
    narration = manifest.get("narration") if isinstance(manifest.get("narration"), dict) else {}
    contract = manifest.get("tts_contract") if isinstance(manifest.get("tts_contract"), dict) else {}
    provider = narration.get("voice_provider") or narration.get("provider") or contract.get("provider")
    name = narration.get("voice_name") or narration.get("voice") or contract.get("voice_name")
    language = narration.get("language_code") or narration.get("language") or contract.get("language_code") or "en-US"
    if provider != PROVIDER:
        raise EdgeTTSError("V2.1 narration provider must be microsoft_edge_tts; no silent fallback is allowed")
    if name != V21_VOICE_NAME:
        raise EdgeTTSError(f"V2.1 voice must be {V21_VOICE_NAME}")
    return {
        "provider": PROVIDER,
        "language_code": str(language),
        "voice_name": str(name),
        "sample_rate_hz": int(narration.get("sample_rate_hz", 24000)),
        "encoding": str(narration.get("encoding", "LINEAR16")),
        "speaking_rate": float(narration.get("speaking_rate", 0.94)),
        "rate": str(narration.get("rate", "-6%")),
        "pitch": str(narration.get("pitch", "-1Hz")),
        "volume_gain_db": float(narration.get("volume_gain_db", 0.0)),
        "volume": str(narration.get("volume", "+0%")),
        "style": str(narration.get("style", "low, controlled, authoritative American English suspense narration")),
        "profile_version": V21_PROFILE_VERSION,
        "model": V21_MODEL,
    }


def profile_from_v21_contract(contract: dict, policy: dict) -> dict:
    """Validate the active V2.1 Edge profile without making a network request."""
    voice_policy = policy.get("voice_policy") if isinstance(policy.get("voice_policy"), dict) else {}
    if not isinstance(contract, dict):
        raise EdgeTTSError("V2.1 TTS contract must be an object")
    expected = {
        "provider": policy.get("voice_provider", PROVIDER),
        "voice_name": voice_policy.get("voice_name", V21_VOICE_NAME),
        "language_code": voice_policy.get("language_code", "en-US"),
        "model": voice_policy.get("model", V21_MODEL),
        "provider_fallback": voice_policy.get("provider_fallback", "forbidden"),
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise EdgeTTSError(f"V2.1 TTS contract.{field} must equal {value}")
    if expected["provider"] != PROVIDER or expected["voice_name"] != V21_VOICE_NAME:
        raise EdgeTTSError(f"V2.1 Edge voice must be {V21_VOICE_NAME}")
    return {
        "provider": PROVIDER,
        "language_code": expected["language_code"],
        "voice_name": expected["voice_name"],
        "model": expected["model"],
        "sample_rate_hz": int(voice_policy.get("sample_rate_hz", 24000)),
        "encoding": str(voice_policy.get("encoding", "LINEAR16")),
        "speaking_rate": float(voice_policy.get("speaking_rate", 0.94)),
        "rate": str(voice_policy.get("rate", "-6%")),
        "pitch": str(voice_policy.get("pitch", "-1Hz")),
        "volume_gain_db": float(voice_policy.get("volume_gain_db", 0.0)),
        "volume": str(voice_policy.get("volume", "+0%")),
        "style": str(voice_policy.get("style", "low, controlled, authoritative American English suspense narration")),
        "profile_version": V21_PROFILE_VERSION,
    }

def build_text(text: str, *, substitutions: dict | None = None) -> str:
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
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            raise EdgeTTSError("ffmpeg or imageio-ffmpeg is required to convert Edge TTS audio to canonical WAV") from exc
    command = [
        ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
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
            detail = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown error"
            raise EdgeTTSError(
                f"Edge TTS synthesis failed after {MAX_ATTEMPTS} attempts; {detail[:500]}"
            ) from last_error
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
    """Validate the pinned profile locally; synthesis is the authoritative voice check."""
    profile = profile_from_manifest(manifest)
    chunks = chunks_from_manifest(manifest, "")
    estimated = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    limit = int(os.environ.get("EDGE_TTS_MAX_CHARACTERS", "5000"))
    if estimated > limit:
        raise EdgeTTSError(f"estimated TTS characters {estimated} exceed configured budget {limit}")
    if not edge_tts_available():
        raise EdgeTTSError("edge-tts dependency is not installed")
    return {
        "status": "EDGE_TTS_PREFLIGHT_PASS",
        "provider": PROVIDER,
        "service": "Microsoft Edge online TTS",
        "voice_profile": profile,
        "voice_check": {
            "voice_name": profile["voice_name"],
            "validation": "pinned_profile; authoritative check occurs during synthesis",
        },
        "estimated_characters": estimated,
        "character_budget": limit,
        "credential_policy": "no_api_key_or_billing_account_required",
        "quota_policy": "fail_closed_on_synthesis_service_unavailability",
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