#!/usr/bin/env python3
"""Check pinned Drive receipt metadata before skipping a previously completed render.

This is READ-ONLY Drive API metadata access. No creation, deletion, download,
upload, TTS, media render or production approval. File bytes were MD5-checked
at the successful original Drive delivery; immutable metadata is checked now.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

class ReceiptError(ValueError): pass

def validate_metadata(catalog: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    if catalog.get("reference_state")!="DRAFT_PREVIEW_ONLY":
        raise ReceiptError("Only recorded unapproved draft may be reused")
    supplied={x.get("id"):x for x in entries if isinstance(x,dict)}
    if not catalog.get("artifacts") or len(supplied)<len(catalog["artifacts"]):
        raise ReceiptError("Missing Drive receipt evidence")
    for artifact in catalog["artifacts"]:
        remote=supplied.get(artifact["drive_file_id"])
        if not remote or remote.get("trashed"):
            raise ReceiptError("Preview artifact missing or trashed")
        if remote.get("name")!=artifact["name"]:
            raise ReceiptError("Drive file name changed")
        if int(remote.get("size") or 0)!=artifact["bytes"]:
            raise ReceiptError("Drive artifact byte count changed")
        if str(remote.get("md5Checksum") or "").lower()!=artifact["md5"].lower():
            raise ReceiptError("Drive artifact hash changed")
        if artifact["kind"]=="preview_mp4" and not str(remote.get("mimeType") or "").startswith("video/"):
            raise ReceiptError("MP4 MIME type changed")
        if artifact["kind"]=="narration_wav" and not str(remote.get("mimeType") or "").startswith("audio/"):
            raise ReceiptError("WAV MIME type changed")
    return {"status":"RECORDED_PREVIEW_DRIVE_METADATA_VERIFIED","file_count":len(catalog["artifacts"]),
            "source_run_id":catalog["run_id"],"release_approved":False,
            "reused_same_episode_only":True,"media_bytes_redownloaded":False,
            "note":"Verified Google Drive metadata MD5/size relative to original delivery; not fresh local byte rehash."}

def verify(catalog_path: Path) -> dict[str, Any]:
    # Lazy import: unit tests and local planning don't require authenticated Drive.
    from production.google_drive_assets import service
    catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
    drive=service()
    entries=[]
    for artifact in catalog.get("artifacts",[]):
        item=drive.files().get(fileId=artifact["drive_file_id"],
             fields="id,name,size,mimeType,md5Checksum,trashed,parents",
             supportsAllDrives=True).execute(num_retries=3)
        entries.append(item)
    return validate_metadata(catalog,entries)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog",required=True,type=Path)
    a=p.parse_args()
    try:
        print(json.dumps(verify(a.catalog),ensure_ascii=False))
        return 0
    except (OSError,TypeError,KeyError,ValueError,ReceiptError,json.JSONDecodeError) as e:
        print("DRIVE_REUSE_RECEIPT_BLOCKED: "+str(e));return 1
if __name__=="__main__": raise SystemExit(main())
