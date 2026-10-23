#!/usr/bin/env python3
"""Register a track downloaded by a producer from YouTube Studio Audio Library.

This tool never downloads from YouTube or infers track rights. The producer
supplies the Studio track details and confirms the source before it stages the
MP3 and updates the episode manifest and license register.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://support.google.com/youtube/answer/3376882"


def ingest(source: Path, metadata_path: Path, episode_dir: Path, manifest_path: Path,
           register_path: Path, confirm: bool) -> dict:
    if not confirm:
        raise ValueError("Confirm that this MP3 was downloaded from YouTube Studio Audio Library.")
    if not source.is_file() or source.suffix.lower() != ".mp3":
        raise ValueError("Source must be an existing MP3 downloaded from Audio Library.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for key in ("title", "artist", "attribution_required"):
        if key not in metadata:
            raise ValueError(f"Metadata is missing {key!r}.")
    title, artist = str(metadata["title"]).strip(), str(metadata["artist"]).strip()
    if not title or not artist:
        raise ValueError("Track title and artist must not be empty.")
    attribution_required = metadata["attribution_required"]
    if not isinstance(attribution_required, bool):
        raise ValueError("attribution_required must be true or false, copied from Studio.")
    attribution = str(metadata.get("attribution_text", "")).strip()
    if attribution_required and not attribution:
        raise ValueError("Studio attribution text is required for this track.")
    volume = metadata.get("volume", 0.08)
    if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not 0 <= volume <= 0.25:
        raise ValueError("volume must be between 0 and 0.25.")

    episode_dir = episode_dir.resolve()
    target = episode_dir / "assets" / "music" / "youtube-audio-library.mp3"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    relpath = target.relative_to(episode_dir).as_posix()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["music"] = {
        "path": relpath,
        "title": title,
        "artist": artist,
        "source_url": SOURCE_URL,
        "license": "youtube_audio_library",
        "commercial_use": True,
        "usage_scope": "YouTube videos; verify separately before off-platform use",
        "attribution_required": attribution_required,
        "attribution": attribution,
        "volume": float(volume),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    register = json.loads(register_path.read_text(encoding="utf-8")) if register_path.exists() else {
        "schema_version": "1.0", "episode_id": manifest.get("episode_id", ""),
        "status": "attached", "policy": "Tracks are registered from YouTube Studio Audio Library with their Studio license and attribution details.", "tracks": []
    }
    register["episode_id"] = manifest.get("episode_id", register.get("episode_id", ""))
    register["status"] = "attached"
    register["tracks"] = [track for track in register.get("tracks", []) if track.get("role") != "suspense_bed"]
    register["tracks"].append({
        "role": "suspense_bed", "path": relpath, "title": title, "artist": artist,
        "source_url": SOURCE_URL, "license": "youtube_audio_library", "commercial_use": True,
        "usage_scope": "YouTube videos", "attribution_required": attribution_required,
        "attribution_text": attribution, "content_id_risk": "downloaded_from_official_audio_library",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    register_path.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"track": title, "path": relpath, "attribution_required": attribution_required}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_mp3", type=Path, help="MP3 downloaded manually from YouTube Studio")
    parser.add_argument("metadata_json", type=Path, help="Track details copied from Studio")
    parser.add_argument("--episode-dir", type=Path, required=True, help="Episode root")
    parser.add_argument("--manifest", type=Path, required=True, help="Render manifest JSON")
    parser.add_argument("--register", type=Path, required=True, help="Music license register JSON")
    parser.add_argument("--confirm-audio-library-download", action="store_true", help="Confirm Studio Audio Library source")
    args = parser.parse_args()
    try:
        print(json.dumps(ingest(args.source_mp3, args.metadata_json, args.episode_dir,
                                args.manifest, args.register, args.confirm_audio_library_download), ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
