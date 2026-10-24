#!/usr/bin/env python3
"""Hydrate approved Drive video assets into an ephemeral GitHub runner.

The browser approves an asset and records its Drive file ID in the episode
manifest.  This script is the explicit bridge between that approval session
and GitHub Actions; the renderer never depends on a temporary stock-site URL.
"""

from __future__ import annotations

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

from production.video_asset_contract import VideoContractError, load_manifest, resolve_inside


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
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(drive, file_id: str, target: Path) -> dict[str, Any]:
    metadata = drive.files().get(fileId=file_id, fields="id,name,mimeType,size,parents,trashed", supportsAllDrives=True).execute(num_retries=3)
    if metadata.get("trashed"):
        raise AssetHydrationError(f"Drive asset is trashed: {file_id}")
    if not str(metadata.get("mimeType", "")).startswith("video/"):
        raise AssetHydrationError(f"Drive asset is not a video: {metadata.get('name', file_id)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
    with target.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request, chunksize=8 * 1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk(num_retries=3)
    return {"id": metadata["id"], "name": metadata.get("name"), "mimeType": metadata.get("mimeType"), "size": target.stat().st_size, "sha256": sha256_file(target)}


def hydrate(manifest_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    assets = []
    for scene in manifest.get("scenes", []):
        asset = scene.get("asset", {})
        file_id = str(asset.get("drive_file_id", "")).strip()
        path = resolve_inside(manifest_path.parent, asset.get("path"), f"Asset {asset.get('asset_id', '?')} path")
        if file_id:
            assets.append((file_id, path, asset))
        elif not path.is_file():
            raise AssetHydrationError(f"Asset {asset.get('asset_id', '?')} has no drive_file_id and is not present locally.")
    if assets:
        drive = service()
        for file_id, path, record in assets:
            result = download(drive, file_id, path)
            expected = str(record.get("sha256", "")).lower()
            if expected and result["sha256"].lower() != expected:
                raise AssetHydrationError(f"Drive asset {record.get('asset_id')} checksum mismatch after download.")
    return {"status": "DRIVE_ASSETS_HYDRATED", "video_id": manifest.get("video_id"), "asset_count": len(manifest.get("scenes", [])), "downloaded": len(assets)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(hydrate(args.manifest.resolve()), ensure_ascii=False))
        return 0
    except (AssetHydrationError, VideoContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"DRIVE ASSET HYDRATION BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


