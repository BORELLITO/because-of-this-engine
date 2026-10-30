#!/usr/bin/env python3
"""Hydrate approved Drive video assets into an ephemeral GitHub runner.

The browser approves an asset and records its Drive file ID in the episode
manifest.  This script is the explicit bridge between that approval session
and GitHub Actions; the renderer never depends on a temporary stock-site URL.
"""

from __future__ import annotations

import sys
import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.video_asset_contract import (
    FINGERPRINT_VERSION,
    VideoContractError,
    ffprobe,
    load_manifest,
    perceptual_hash,
    resolve_inside,
)


class AssetHydrationError(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AssetHydrationError(f"Missing required environment variable: {name}")
    return value


def service():
    creds = Credentials(
        token=None,
        refresh_token=require_env("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=require_env("GOOGLE_CLIENT_ID"),
        client_secret=require_env("GOOGLE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(drive, file_id: str, target: Path, expected_prefix: str) -> dict[str, Any]:
    metadata = drive.files().get(
        fileId=file_id,
        fields="id,name,mimeType,size,parents,trashed,modifiedTime",
        supportsAllDrives=True,
    ).execute(num_retries=3)
    if metadata.get("trashed"):
        raise AssetHydrationError(f"Drive asset is trashed: {file_id}")
    mime_type = str(metadata.get("mimeType", ""))
    if not mime_type.startswith(expected_prefix):
        raise AssetHydrationError(
            f"Drive asset MIME type mismatch for {metadata.get('name', file_id)}: "
            f"expected {expected_prefix}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    try:
        request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
        with partial.open("wb") as handle:
            downloader = MediaIoBaseDownload(handle, request, chunksize=8 * 1024 * 1024)
            done = False
            while not done:
                _, done = downloader.next_chunk(num_retries=3)
        size = partial.stat().st_size
        expected_size = int(metadata.get("size", 0) or 0)
        if expected_size and size != expected_size:
            raise AssetHydrationError(f"Drive asset size mismatch: {file_id}")
        os.replace(partial, target)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise
    return {
        "id": metadata["id"],
        "name": metadata.get("name"),
        "mimeType": mime_type,
        "size": target.stat().st_size,
        "sha256": sha256_file(target),
        "modifiedTime": metadata.get("modifiedTime"),
    }


def hydrate(manifest_path: Path, *, require_drive_assets: bool = False) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    assets = []
    fingerprint_refreshes: list[dict[str, Any]] = []
    seen_drive_ids: set[str] = set()
    for scene in manifest.get("scenes", []):
        asset = scene.get("asset", {})
        file_id = str(asset.get("drive_file_id", "")).strip()
        path = resolve_inside(manifest_path.parent, asset.get("path"), f"Asset {asset.get('asset_id', '?')} path")
        if file_id:
            if file_id in seen_drive_ids:
                raise AssetHydrationError(f"Drive asset is reused in this episode: {file_id}")
            seen_drive_ids.add(file_id)
            assets.append((file_id, path, asset, "video"))
        elif require_drive_assets:
            raise AssetHydrationError(f"Asset {asset.get('asset_id', '?')} is missing drive_file_id.")
        elif not path.is_file():
            raise AssetHydrationError(f"Asset {asset.get('asset_id', '?')} has no drive_file_id and is not present locally.")
    music = manifest.get("music")
    if isinstance(music, dict):
        music_id = str(music.get("drive_file_id", "")).strip()
        music_path = resolve_inside(manifest_path.parent, music.get("path"), "Music path")
        if music_id:
            if music_id in seen_drive_ids:
                raise AssetHydrationError(f"Drive asset is reused in this episode: {music_id}")
            seen_drive_ids.add(music_id)
            assets.append((music_id, music_path, music, "audio"))
        elif require_drive_assets and music.get("source") != "engine_generated":
            raise AssetHydrationError("Music is missing drive_file_id.")
        elif not music_path.is_file():
            raise AssetHydrationError("Music has no drive_file_id and is not present locally.")
    loop = manifest.get("loop")
    if isinstance(loop, dict) and loop.get("logo_enabled", False) is True:
        logo_id = str(loop.get("logo_drive_file_id", "")).strip()
        logo_path = resolve_inside(manifest_path.parent, loop.get("logo_path"), "Loop logo path")
        if logo_id:
            if logo_id in seen_drive_ids:
                raise AssetHydrationError(f"Drive asset is reused in this episode: {logo_id}")
            seen_drive_ids.add(logo_id)
            assets.append((logo_id, logo_path, loop, "image"))
        elif require_drive_assets:
            raise AssetHydrationError("Loop logo is missing logo_drive_file_id.")
        elif not logo_path.is_file():
            raise AssetHydrationError("Loop logo has no logo_drive_file_id and is not present locally.")
    if assets:
        drive = service()
        for file_id, path, record, kind in assets:
            result = download(drive, file_id, path, "video/" if kind == "video" else "audio/" if kind == "audio" else "image/")
            expected = str(record.get("sha256", "")).lower()
            if expected and result["sha256"].lower() != expected:
                raise AssetHydrationError(f"Drive asset {record.get('asset_id')} checksum mismatch after download.")
            # The SHA-256 is the immutable source identity.  The perceptual
            # fingerprint is a decoded-pixel evidence signal and can drift
            # when GitHub's FFmpeg major version changes.  Recompute it over
            # the bytes that this runner actually hydrated, while retaining
            # the manifest value for provenance and audit comparison.
            if kind == "video":
                metadata = ffprobe(path)
                runtime_phash = perceptual_hash(path, duration=float(metadata["duration"]))
                record["hydrated_perceptual_hash"] = runtime_phash
                fingerprint_refreshes.append({
                    "asset_id": record.get("asset_id"),
                    "sha256": result["sha256"],
                    "declared_perceptual_hash": record.get("perceptual_hash"),
                    "hydrated_perceptual_hash": runtime_phash,
                    "fingerprint_version": FINGERPRINT_VERSION,
                })
    if fingerprint_refreshes:
        manifest["runtime_asset_hydration"] = {
            "fingerprint_version": FINGERPRINT_VERSION,
            "fingerprint_scope": "downloaded_bytes",
            "ffmpeg_runtime_recalculated": True,
            "assets": fingerprint_refreshes,
        }
        temporary = manifest_path.with_name(manifest_path.name + ".hydrated.part")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, manifest_path)
    return {
        "status": "DRIVE_ASSETS_HYDRATED",
        "video_id": manifest.get("video_id"),
        "asset_count": len(manifest.get("scenes", [])),
        "downloaded": len(assets),
        "downloaded_videos": sum(1 for item in assets if item[3] == "video"),
        "downloaded_audio": sum(1 for item in assets if item[3] == "audio"),
        "runtime_fingerprint_refreshes": len(fingerprint_refreshes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--require-drive-assets", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(hydrate(args.manifest.resolve(), require_drive_assets=args.require_drive_assets), ensure_ascii=False))
        return 0
    except (AssetHydrationError, VideoContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"DRIVE ASSET HYDRATION BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


