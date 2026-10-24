#!/usr/bin/env python3
"""Verified Google Drive delivery for Because of This production outputs.

GitHub Actions is treated as ephemeral compute only. Useful outputs are uploaded
to Google Drive, verified by size + MD5, and never depend on Actions artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_MIME = "application/vnd.google-apps.folder"
DEFAULT_ROOT_FOLDER = "1GUOcSRo91xxypW-GgCchubhx9FaMGk5u"


class DeliveryError(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise DeliveryError(f"Missing required environment variable: {name}")
    return value


def credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=require_env("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=require_env("GOOGLE_CLIENT_ID"),
        client_secret=require_env("GOOGLE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    creds.refresh(Request())
    return creds


def service():
    return build("drive", "v3", credentials=credentials(), cache_discovery=False)


def normalize_folder_id(value: str | None) -> str:
    raw = (value or DEFAULT_ROOT_FOLDER).strip()
    if "/folders/" in raw:
        raw = raw.split("/folders/", 1)[1].split("?", 1)[0].split("/", 1)[0]
    if not raw:
        raise DeliveryError("Drive root folder ID is empty.")
    return raw


def validate_folder(drive, folder_id: str) -> dict:
    item = (
        drive.files()
        .get(
            fileId=folder_id,
            fields="id,name,mimeType,trashed,capabilities(canAddChildren)",
            supportsAllDrives=True,
        )
        .execute(num_retries=3)
    )
    if item.get("mimeType") != FOLDER_MIME:
        raise DeliveryError("Configured Drive destination is not a folder.")
    if item.get("trashed"):
        raise DeliveryError("Configured Drive destination is in trash.")
    if item.get("capabilities", {}).get("canAddChildren") is False:
        raise DeliveryError("Connected Google account cannot upload to the destination folder.")
    return item


def escape_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def child_by_name(drive, parent_id: str, name: str, mime_type: str | None = None) -> dict | None:
    query = [
        f"'{escape_query(parent_id)}' in parents",
        f"name = '{escape_query(name)}'",
        "trashed = false",
    ]
    if mime_type:
        query.append(f"mimeType = '{escape_query(mime_type)}'")
    response = (
        drive.files()
        .list(
            q=" and ".join(query),
            fields="files(id,name,mimeType,size,md5Checksum,webViewLink)",
            pageSize=10,
            spaces="drive",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute(num_retries=3)
    )
    files = response.get("files", [])
    return files[0] if files else None


def ensure_folder(drive, parent_id: str, name: str) -> str:
    existing = child_by_name(drive, parent_id, name, FOLDER_MIME)
    if existing:
        return existing["id"]
    created = (
        drive.files()
        .create(
            body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
            fields="id,name",
            supportsAllDrives=True,
        )
        .execute(num_retries=3)
    )
    return created["id"]


def safe_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value.strip())
    value = re.sub(r"\s+", " ", value)
    return value[:120] or "delivery"


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(paths: Iterable[Path]) -> list[tuple[Path, Path]]:
    results: list[tuple[Path, Path]] = []
    for original in paths:
        path = original.resolve()
        if not path.exists():
            raise DeliveryError(f"Delivery path does not exist: {original}")
        if path.is_file():
            results.append((path, Path(path.name)))
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file():
                results.append((child, Path(path.name) / child.relative_to(path)))
    if not results:
        raise DeliveryError("No files found for Drive delivery.")
    return results


def upload_verified(drive, parent_id: str, local: Path, remote_name: str) -> dict:
    local_size = local.stat().st_size
    local_md5 = md5(local)
    mime_type = mimetypes.guess_type(local.name)[0] or "application/octet-stream"

    existing = child_by_name(drive, parent_id, remote_name)
    media = MediaFileUpload(str(local), mimetype=mime_type, resumable=True)

    body = {
        "name": remote_name,
        "appProperties": {
            "engine": "because-of-this",
            "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        },
    }
    fields = "id,name,size,md5Checksum,webViewLink,parents"

    if existing:
        remote = (
            drive.files()
            .update(
                fileId=existing["id"],
                body=body,
                media_body=media,
                fields=fields,
                supportsAllDrives=True,
            )
            .execute(num_retries=3)
        )
    else:
        body["parents"] = [parent_id]
        remote = (
            drive.files()
            .create(
                body=body,
                media_body=media,
                fields=fields,
                supportsAllDrives=True,
            )
            .execute(num_retries=3)
        )

    remote_size = int(remote.get("size", -1))
    remote_md5 = (remote.get("md5Checksum") or "").lower()
    if remote_size != local_size:
        raise DeliveryError(
            f"Drive verification failed for {local.name}: size {remote_size} != {local_size}"
        )
    if remote_md5 and remote_md5 != local_md5:
        raise DeliveryError(
            f"Drive verification failed for {local.name}: checksum mismatch"
        )

    return {
        "id": remote["id"],
        "name": remote["name"],
        "size": remote_size,
        "md5": remote_md5 or local_md5,
        "webViewLink": remote.get("webViewLink"),
    }


def deliver(
    root_folder_id: str,
    collection: str,
    delivery_name: str,
    paths: list[Path],
) -> dict:
    drive = service()
    root = validate_folder(drive, root_folder_id)
    collection_id = ensure_folder(drive, root_folder_id, safe_name(collection))
    delivery_id = ensure_folder(drive, collection_id, safe_name(delivery_name))

    uploaded = []
    folder_cache: dict[Path, str] = {Path("."): delivery_id}
    for local, relative in iter_files(paths):
        parent_rel = relative.parent
        parent_id = delivery_id
        if parent_rel != Path("."):
            cursor = Path(".")
            for part in parent_rel.parts:
                cursor = cursor / part
                if cursor not in folder_cache:
                    folder_cache[cursor] = ensure_folder(drive, parent_id, safe_name(part))
                parent_id = folder_cache[cursor]
        uploaded.append(upload_verified(drive, parent_id, local, relative.name))

    return {
        "status": "DRIVE_VERIFIED",
        "root_folder": {"id": root["id"], "name": root.get("name")},
        "collection": collection,
        "delivery_name": delivery_name,
        "delivery_folder_id": delivery_id,
        "delivery_folder_url": f"https://drive.google.com/drive/folders/{delivery_id}",
        "file_count": len(uploaded),
        "files": uploaded,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload and verify production outputs in Google Drive.")
    parser.add_argument(
        "--root-folder-id",
        default=os.environ.get("BECAUSE_OF_THIS_DRIVE_FOLDER_ID", DEFAULT_ROOT_FOLDER),
    )
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--collection", default="PRODUCOES")
    parser.add_argument("--delivery-name", default=f"github-run-{os.environ.get('GITHUB_RUN_ID', 'local')}")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    try:
        root_folder_id = normalize_folder_id(args.root_folder_id)
        if args.preflight:
            drive = service()
            folder = validate_folder(drive, root_folder_id)
            print(json.dumps({
                "status": "DRIVE_PREFLIGHT_OK",
                "folder_id": folder["id"],
                "folder_name": folder.get("name"),
            }, ensure_ascii=False))
            return 0

        if not args.path:
            raise DeliveryError("At least one --path is required for delivery.")

        report = deliver(
            root_folder_id,
            args.collection,
            args.delivery_name,
            [Path(value) for value in args.path],
        )
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0
    except Exception as exc:
        print(f"DRIVE DELIVERY FAILED: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
