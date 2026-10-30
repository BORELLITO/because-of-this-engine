#!/usr/bin/env python3
"""Content-addressed narration cache with optional Google Drive persistence.

The cache is deliberately keyed by every input that can change the generated
voice: script, model, voice, language, style and duration-normalization version.
A cache hit is accepted only after WAV format, duration, sidecar and checksum
validation. A provider request is never skipped when any input differs.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import tempfile
import wave
from pathlib import Path
from typing import Any

try:
    from production.google_drive_delivery import (
        DEFAULT_ROOT_FOLDER,
    MediaFileUpload,
    child_by_name,
    ensure_folder,
    normalize_folder_id,
    service,
        validate_folder,
    )
except ModuleNotFoundError as exc:
    if exc.name != "production":
        raise
    from google_drive_delivery import (
        DEFAULT_ROOT_FOLDER,
        MediaFileUpload,
        child_by_name,
        ensure_folder,
        normalize_folder_id,
        service,
        validate_folder,
    )

CACHE_SCHEMA_VERSION = 1
NORMALIZATION_VERSION = "shorts-60-75-v1"
CACHE_COLLECTION = "NARRATION CACHE"
MIN_DURATION_SECONDS = 60.0
MAX_DURATION_SECONDS = 75.0


class NarrationCacheError(RuntimeError):
    """Raised when a cache entry is missing, stale or unsafe."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NarrationCacheError(f"Could not read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise NarrationCacheError(f"{label} must be an object: {path}")
    return value


def _script_text(manifest_path: Path, manifest: dict[str, Any]) -> str:
    script = manifest.get("script") or {}
    value = script.get("path")
    if not isinstance(value, str) or not value.strip():
        raise NarrationCacheError("Manifest script.path is missing.")
    path = (manifest_path.parent / value).resolve()
    base = manifest_path.parent.resolve()
    if path != base and base not in path.parents:
        raise NarrationCacheError("Script path escapes the episode directory.")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise NarrationCacheError(f"Could not read canonical script: {path}") from exc
    if not text:
        raise NarrationCacheError("Canonical script is empty.")
    return text


def _tts_script_text(manifest_path: Path, manifest: dict[str, Any], canonical_text: str) -> str:
    voice = manifest.get("voice") or {}
    value = voice.get("tts_script_path")
    if not isinstance(value, str) or not value.strip():
        return canonical_text
    path = (manifest_path.parent / value).resolve()
    base = manifest_path.parent.resolve()
    if path == base or base not in path.parents:
        raise NarrationCacheError("voice.tts_script_path must stay inside the episode directory.")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise NarrationCacheError(f"Could not read TTS pronunciation script: {path}") from exc
    if not text:
        raise NarrationCacheError("TTS pronunciation script is empty.")
    return text


def cache_key(
    script_text: str,
    *,
    model: str,
    voice: str,
    language: str,
    style: str,
    tts_script_text: str | None = None,
    normalization_version: str = NORMALIZATION_VERSION,
    generation_context: dict[str, Any] | None = None,
) -> str:
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "script_sha256": hashlib.sha256(script_text.encode("utf-8")).hexdigest(),
        "model": str(model).strip(),
        "voice": str(voice).strip(),
        "language": str(language).strip(),
        "style": str(style).strip(),
        "normalization_version": str(normalization_version).strip(),
    }
    if generation_context is not None:
        payload["generation_context_sha256"] = hashlib.sha256(
            json.dumps(generation_context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    if tts_script_text is not None and tts_script_text != script_text:
        payload["tts_script_sha256"] = hashlib.sha256(
            tts_script_text.encode("utf-8")
        ).hexdigest()
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def manifest_cache_spec(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _read_json(manifest_path, "manifest")
    voice = manifest.get("voice")
    if not isinstance(voice, dict):
        raise NarrationCacheError("Manifest voice profile is missing.")
    provider = str(voice.get("provider", "")).strip()
    if provider != "gemini_tts":
        raise NarrationCacheError(f"Unsupported narration provider for active V7.2 cache: {provider}")
    model = voice.get("model") or voice.get("model_or_voice_type") or provider
    voice_name = voice.get("voice_name") or voice.get("voice")
    language = voice.get("language_code") or voice.get("language")
    style = voice.get("style")
    if not all(isinstance(v, str) and v.strip() for v in (model, voice_name, language, style)):
        raise NarrationCacheError("Manifest cache voice identity is incomplete")
    text = _script_text(manifest_path, manifest)
    tts_text = _tts_script_text(manifest_path, manifest, text)
    # Cloud synthesis has no local model bytes. The complete canonical
    # voice/prosody configuration and beat chunking remain part of the key.
    generation_context = {
        "provider": provider,
        "voice": voice,
        "narration_beats": (manifest.get("narration") or {}).get("beats", []),
        "cloud_tts_cache_contract": 1,
    }
    key = cache_key(
        text,
        model=str(model),
        voice=str(voice_name),
        language=str(language),
        style=str(style),
        tts_script_text=tts_text,
        generation_context=generation_context,
    )
    audio = manifest.get("audio") or {}
    audio_value = audio.get("path")
    if not isinstance(audio_value, str) or not audio_value.strip():
        raise NarrationCacheError("Manifest audio.path is missing.")
    audio_path = (manifest_path.parent / audio_value).resolve()
    base = manifest_path.parent.resolve()
    if audio_path != base and base not in audio_path.parents:
        raise NarrationCacheError("Audio path escapes the episode directory.")
    return {
        "manifest": manifest,
        "script_text": text,
        "tts_script_text": tts_text,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "tts_script_sha256": (hashlib.sha256(tts_text.encode("utf-8")).hexdigest() if tts_text != text else None),
        "model": str(model),
        "voice": str(voice_name),
        "language": str(language),
        "style": str(style),
        "generation_context_sha256": (
            hashlib.sha256(json.dumps(generation_context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
            if generation_context is not None else None
        ),
        "normalization_version": NORMALIZATION_VERSION,
        "cache_key": key,
        "audio_path": audio_path,
        "sidecar_path": audio_path.with_suffix(audio_path.suffix + ".json"),
        "audio_name": f"narration-{key}.wav",
        "sidecar_name": f"narration-{key}.json",
    }


def _wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2 or handle.getframerate() != 24000:
                raise NarrationCacheError("Cached narration must be mono 24 kHz 16-bit PCM WAV.")
            duration = handle.getnframes() / handle.getframerate()
    except (OSError, wave.Error) as exc:
        raise NarrationCacheError(f"Could not validate cached WAV: {path}") from exc
    if not MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS:
        raise NarrationCacheError(f"Cached narration duration {duration:.3f}s is outside 60–75s.")
    return duration


def validate_entry(spec: dict[str, Any], audio_path: Path, sidecar_path: Path) -> dict[str, Any]:
    metadata = _read_json(sidecar_path, "narration cache sidecar")
    expected = {
        "cache_key": spec["cache_key"],
        "script_sha256": spec["script_sha256"],
        "tts_script_sha256": spec["tts_script_sha256"],
        "model": spec["model"],
        "voice": spec["voice"],
        "language": spec["language"],
        "style": spec["style"],
        "normalization_version": spec["normalization_version"],
        "cache_schema_version": CACHE_SCHEMA_VERSION,
    }
    if spec.get("generation_context_sha256"):
        expected["generation_context_sha256"] = spec["generation_context_sha256"]
    if spec.get("tts_script_sha256"):
        expected["tts_script_sha256"] = spec["tts_script_sha256"]
    mismatches = [
        key for key, value in expected.items()
        if metadata.get(key) != value
    ]
    if mismatches:
        raise NarrationCacheError("Narration cache sidecar mismatch: " + ", ".join(mismatches))
    if not audio_path.is_file():
        raise NarrationCacheError(f"Cached narration WAV is missing: {audio_path}")
    duration = _wav_duration(audio_path)
    actual_sha = sha256_file(audio_path)
    if metadata.get("sha256") != actual_sha:
        raise NarrationCacheError("Narration cache checksum does not match the WAV.")
    if round(float(metadata.get("duration_seconds", -1)), 3) != round(duration, 3):
        raise NarrationCacheError("Narration cache duration sidecar does not match the WAV.")
    return {
        "status": "NARRATION_CACHE_HIT",
        "cache_key": spec["cache_key"],
        "duration_seconds": round(duration, 3),
        "sha256": actual_sha,
        "audio_path": str(audio_path),
        "sidecar_path": str(sidecar_path),
    }


def annotate_local(spec: dict[str, Any]) -> dict[str, Any]:
    audio_path = spec["audio_path"]
    duration = _wav_duration(audio_path)
    metadata: dict[str, Any] = {}
    if spec["sidecar_path"].is_file():
        metadata = _read_json(spec["sidecar_path"], "narration sidecar")
    metadata.update({
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "cache_key": spec["cache_key"],
        "script_sha256": spec["script_sha256"],
        "tts_script_sha256": spec["tts_script_sha256"],
        "model": spec["model"],
        "voice": spec["voice"],
        "language": spec["language"],
        "style": spec["style"],
        "normalization_version": spec["normalization_version"],
        "duration_seconds": round(duration, 3),
        "sha256": sha256_file(audio_path),
        "cache_status": "VERIFIED",
    })
    if spec.get("generation_context_sha256"):
        metadata["generation_context_sha256"] = spec["generation_context_sha256"]
    if spec.get("tts_script_sha256"):
        metadata["tts_script_sha256"] = spec["tts_script_sha256"]
    spec["sidecar_path"].parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=spec["sidecar_path"].parent,
            prefix=f".{spec['sidecar_path'].name}.",
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(metadata, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, spec["sidecar_path"])
    except OSError as exc:
        raise NarrationCacheError(f"Could not write narration cache sidecar: {spec['sidecar_path']}") from exc
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
    return validate_entry(spec, audio_path, spec["sidecar_path"])


def local_hit(spec: dict[str, Any]) -> dict[str, Any] | None:
    if not spec["audio_path"].is_file() or not spec["sidecar_path"].is_file():
        return None
    try:
        return validate_entry(spec, spec["audio_path"], spec["sidecar_path"])
    except NarrationCacheError:
        return None


def _download_bytes(drive: Any, file_id: str) -> bytes:
    try:
        from googleapiclient.http import MediaIoBaseDownload
        request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk(num_retries=3)
        return buffer.getvalue()
    except Exception as exc:
        raise NarrationCacheError(f"Could not download Drive narration cache file: {file_id}") from exc


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temp_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except OSError as exc:
        raise NarrationCacheError(f"Could not restore narration cache file: {path}") from exc
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def restore_from_drive(spec: dict[str, Any], root_folder_id: str | None = None) -> dict[str, Any]:
    local = local_hit(spec)
    if local:
        return {**local, "source": "local"}
    drive = service()
    root_id = normalize_folder_id(root_folder_id or os.environ.get("BECAUSE_OF_THIS_DRIVE_FOLDER_ID", DEFAULT_ROOT_FOLDER))
    validate_folder(drive, root_id)
    collection_id = ensure_folder(drive, root_id, CACHE_COLLECTION)
    audio_remote = child_by_name(drive, collection_id, spec["audio_name"])
    sidecar_remote = child_by_name(drive, collection_id, spec["sidecar_name"])
    if not audio_remote or not sidecar_remote:
        return {"status": "NARRATION_CACHE_MISS", "cache_key": spec["cache_key"], "source": "drive"}
    audio_bytes = _download_bytes(drive, audio_remote["id"])
    sidecar_bytes = _download_bytes(drive, sidecar_remote["id"])
    _atomic_bytes(spec["audio_path"], audio_bytes)
    _atomic_bytes(spec["sidecar_path"], sidecar_bytes)
    try:
        result = validate_entry(spec, spec["audio_path"], spec["sidecar_path"])
    except NarrationCacheError:
        spec["audio_path"].unlink(missing_ok=True)
        spec["sidecar_path"].unlink(missing_ok=True)
        raise
    return {**result, "source": "drive", "drive_file_id": audio_remote["id"]}


def store_to_drive(spec: dict[str, Any], root_folder_id: str | None = None) -> dict[str, Any]:
    local = annotate_local(spec)
    drive = service()
    root_id = normalize_folder_id(root_folder_id or os.environ.get("BECAUSE_OF_THIS_DRIVE_FOLDER_ID", DEFAULT_ROOT_FOLDER))
    validate_folder(drive, root_id)
    collection_id = ensure_folder(drive, root_id, CACHE_COLLECTION)
    uploaded: list[dict[str, Any]] = []
    for path, name, mime_type in (
        (spec["audio_path"], spec["audio_name"], "audio/wav"),
        (spec["sidecar_path"], spec["sidecar_name"], "application/json"),
    ):
        existing = child_by_name(drive, collection_id, name)
        if existing:
            if int(existing.get("size", -1)) != path.stat().st_size:
                raise NarrationCacheError(f"Refusing to overwrite a different cache entry: {name}")
            # A same-sized corrupted object must not be treated as an exact cache
            # match. This is an immutable content-addressed record, not a name.
            expected_md5 = __import__("hashlib").md5(path.read_bytes()).hexdigest()
            if str(existing.get("md5Checksum") or "").lower() != expected_md5:
                raise NarrationCacheError(f"Drive cache MD5 mismatch: {name}")
            uploaded.append({"id": existing["id"], "name": name, "status": "EXISTS_VERIFIED"})
            continue
        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)
        remote = drive.files().create(
            body={
                "name": name,
                "parents": [collection_id],
                "appProperties": {
                    "engine": "because-of-this",
                    "cache_type": "narration",
                    "cache_key": spec["cache_key"],
                    "normalization_version": NORMALIZATION_VERSION,
                },
            },
            media_body=media,
            fields="id,name,size,md5Checksum,webViewLink",
            supportsAllDrives=True,
        ).execute(num_retries=3)
        if int(remote.get("size", -1)) != path.stat().st_size:
            raise NarrationCacheError(f"Drive cache verification failed for {name}.")
        uploaded.append({"id": remote["id"], "name": name, "status": "UPLOADED"})
    return {**local, "status": "NARRATION_CACHE_STORED", "uploaded": uploaded}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--store", action="store_true")
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--status-file", type=Path)
    args = parser.parse_args()
    if sum(bool(item) for item in (args.restore, args.store, args.annotate)) != 1:
        parser.error("Choose exactly one of --restore, --store or --annotate.")
    try:
        spec = manifest_cache_spec(args.manifest)
        if args.restore:
            result = restore_from_drive(spec)
        elif args.store:
            result = store_to_drive(spec)
        else:
            result = annotate_local(spec)
        if args.status_file:
            args.status_file.resolve().parent.mkdir(parents=True, exist_ok=True)
            args.status_file.resolve().write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (NarrationCacheError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"NARRATION CACHE BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
