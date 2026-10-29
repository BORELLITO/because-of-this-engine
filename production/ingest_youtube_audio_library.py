#!/usr/bin/env python3
"""Register one producer-confirmed YouTube Studio Audio Library track."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_URL = "https://support.google.com/youtube/answer/3376882"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest(source: Path, metadata_path: Path, episode_dir: Path, manifest_path: Path,
           register_path: Path, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise ValueError("Confirm that this MP3 was downloaded from YouTube Studio Audio Library.")
    if not source.is_file() or source.suffix.lower() != ".mp3":
        raise ValueError("Source must be an existing MP3 downloaded from Audio Library.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    required = ("title", "artist", "attribution_required", "similarity_review", "device_tests")
    for key in required:
        if key not in metadata:
            raise ValueError(f"Metadata is missing {key!r}.")
    title, artist = str(metadata["title"]).strip(), str(metadata["artist"]).strip()
    if not title or not artist:
        raise ValueError("Track title and artist must not be empty.")
    if not isinstance(metadata["attribution_required"], bool):
        raise ValueError("attribution_required must be true or false.")
    attribution = str(metadata.get("attribution_text", "")).strip()
    if metadata["attribution_required"] and not attribution:
        raise ValueError("Studio attribution text is required for this track.")
    if (metadata.get("similarity_review") or {}).get("status") != "PASS":
        raise ValueError("Similarity review must be PASS before the track is attached.")
    tests = metadata.get("device_tests") or {}
    if any(tests.get(device) != "PASS" for device in ("phone", "headphones", "low_volume")):
        raise ValueError("Phone, headphones and low-volume tests must all be PASS.")
    volume = metadata.get("volume", 0.08)
    if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not 0 <= volume <= 0.20:
        raise ValueError("volume must be between 0 and 0.20.")
    track_id = str(metadata.get("track_id") or f"youtube-audio-{title.lower().replace(' ', '-')}")
    episode_dir = episode_dir.resolve()
    target = episode_dir / "assets" / "music" / "youtube-audio-library.mp3"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    file_hash = sha256_file(target)
    relpath = target.relative_to(episode_dir).as_posix()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["music"] = {
        "path": relpath, "track_id": track_id, "title": title, "artist": artist,
        "source_url": SOURCE_URL, "license": "youtube_audio_library",
        "commercial_use": True, "usage_scope": "YouTube videos; verify separately before off-platform use",
        "attribution_required": metadata["attribution_required"], "attribution": attribution,
        "volume": float(volume), "sha256": file_hash, "reuse_status": "FRESH",
        "origin_recorded_at": datetime.now(timezone.utc).isoformat(),
        "similarity_review": metadata["similarity_review"],
        "device_tests": tests,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    register = json.loads(register_path.read_text(encoding="utf-8")) if register_path.exists() else {
        "schema_version": "2.0", "status": "attached",
        "policy": "Complete tracks are never reused between episodes; reusable SFX require a three-video cooldown.",
        "tracks": []
    }
    for existing in register.get("tracks", []):
        if existing.get("track_id") == track_id and existing.get("episode_id") != manifest.get("video_id"):
            raise ValueError(f"complete track {track_id!r} is already registered to another episode")
    register.setdefault("tracks", [])
    register["tracks"] = [track for track in register["tracks"] if track.get("episode_id") != manifest.get("video_id")]
    register["tracks"].append({
        "role": "suspense_bed", "track_id": track_id, "episode_id": manifest.get("video_id"),
        "path": relpath, "title": title, "artist": artist, "source_url": SOURCE_URL,
        "license": "youtube_audio_library", "commercial_use": True,
        "attribution_required": metadata["attribution_required"], "attribution_text": attribution,
        "sha256": file_hash, "similarity_review": metadata["similarity_review"],
        "device_tests": tests, "used_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    register_path.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"status": "AUDIO_REGISTERED", "track_id": track_id, "path": relpath, "sha256": file_hash}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_mp3", type=Path)
    parser.add_argument("metadata_json", type=Path)
    parser.add_argument("--episode-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--confirm-audio-library-download", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(ingest(args.source_mp3, args.metadata_json, args.episode_dir,
                                args.manifest, args.register, args.confirm_audio_library_download), ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
