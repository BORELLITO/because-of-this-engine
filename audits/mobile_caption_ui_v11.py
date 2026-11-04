"""Platform-side caption UI evidence guard (read-only).

Technical caption alignment and a locked ASS style DO NOT prove safe placement
in real TikTok and YouTube Shorts app interfaces. Final release requires
a human-reviewed capture for BOTH. A screenshot is evidence of what someone
saw, not mathematical proof across all devices or UI variations.

No account access, screenshot fabrication, render, TTS or publication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

PLATFORMS = ("tiktok", "youtube_shorts")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class MobileUIReviewError(ValueError):
    pass


def _resolved(base: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise MobileUIReviewError(f"{label} requires a relative evidence path")
    root = base.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise MobileUIReviewError(f"{label} missing or escapes episode folder")
    return path


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()


def _binary_image(path: Path) -> bool:
    with path.open("rb") as f:
        header=f.read(16)
    if not (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff")):
        return False
    # Decode actual screenshot dimensions. Reject a 1-pixel placeholder or
    # arbitrary bytes with PNG magic. This still does not establish provenance.
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "json", str(path)],
            capture_output=True, check=True, timeout=30,
        )
        streams = json.loads(proc.stdout).get("streams") or []
        if not streams:
            return False
        width, height = int(streams[0].get("width") or 0), int(streams[0].get("height") or 0)
        return (720 <= width <= 4000 and 1280 <= height <= 9000
                and 0.30 <= width / height <= 0.85)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return False


def inspect(manifest_path: Path, review_path: Path | None = None) -> dict[str, Any]:
    manifest_path=manifest_path.resolve()
    root=manifest_path.parent
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    video_id=str(manifest.get("video_id") or "")
    if not video_id:
        raise MobileUIReviewError("Manifest video_id is missing")
    captions=manifest.get("captions") or {}
    cap_path=_resolved(root,captions.get("path"),"ASS captions")
    expected_caption_sha=_sha(cap_path)
    receipt=review_path or root/"rendered"/"caption-platform-ui-review-v11.json"
    issues=[]
    evidence={}
    if not receipt.is_file():
        issues.append("Real-platform TikTok + Shorts device review receipt is absent")
        return {
            "schema_version":"1.1", "status":"MANUAL_UI_REVIEW_REQUIRED",
            "video_id":video_id, "platforms":{},
            "issues":issues, "caption_sha256":expected_caption_sha,
            "official_pixel_safe_zone_certified":False,
            "all_device_coverage_certified":False,
        }
    try:
        report=json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError,ValueError) as exc:
        raise MobileUIReviewError("UI review receipt is unreadable") from exc
    if not isinstance(report,dict) or report.get("schema_version")!="1.1":
        raise MobileUIReviewError("UI review receipt schema invalid")
    if report.get("video_id")!=video_id:
        issues.append("UI receipt video_id differs from manifest")
    if str(report.get("caption_sha256") or "").lower()!=expected_caption_sha:
        issues.append("ASS caption bytes differ from reviewed artifact")
    video=_resolved(root,report.get("video_path"),"Reviewed final video")
    actual_video_sha=_sha(video)
    if str(report.get("video_sha256") or "").lower()!=actual_video_sha:
        issues.append("Rendered video changed since UI review")
    platform_records=report.get("platforms")
    if not isinstance(platform_records,dict):
        raise MobileUIReviewError("platforms must be an object")
    for platform in PLATFORMS:
        p=platform_records.get(platform)
        if not isinstance(p,dict):
            issues.append(f"{platform}: no independent platform-specific review")
            continue
        if p.get("status")!="PASS":
            issues.append(f"{platform}: UI review status not PASS")
        if p.get("view_mode")!="real_platform_ui":
            issues.append(f"{platform}: screenshot must show real platform UI, not a safe-zone template")
        for field in ("reviewer", "captured_at_utc", "device_model"):
            if not isinstance(p.get(field),str) or not p[field].strip():
                issues.append(f"{platform}: {field} missing")
        try:
            snap=_resolved(root,p.get("screenshot_path"),f"{platform} screenshot")
            if not _binary_image(snap):
                issues.append(f"{platform}: screenshot is not PNG/JPEG")
            actual_snap_sha=_sha(snap)
            if str(p.get("screenshot_sha256") or "").lower()!=actual_snap_sha:
                issues.append(f"{platform}: screenshot SHA differs from reviewed file")
            evidence[platform]={"device":p.get("device_model"),"screenshot_sha256":actual_snap_sha}
        except MobileUIReviewError as exc:
            issues.append(f"{platform}: {exc}")
    if len(evidence) == len(PLATFORMS):
        if evidence["tiktok"]["screenshot_sha256"] == evidence["youtube_shorts"]["screenshot_sha256"]:
            issues.append("TikTok and YouTube Shorts must have distinct device/UI screenshots")
    return {
        "schema_version":"1.1","status":"UI_EVIDENCE_ATTESTED" if not issues else "MANUAL_UI_REVIEW_REQUIRED",
        "video_id":video_id,"issues":issues,"platforms":evidence,
        "video_sha256":actual_video_sha,"caption_sha256":expected_caption_sha,
        "official_pixel_safe_zone_certified":False,
        "all_device_coverage_certified":False,
        "interpretation":"Manual device capture attestation only; not independently verified by a cloud model",
        "approved_for_auto_publication":False,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--receipt",type=Path)
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    try:
        report=inspect(a.manifest,a.receipt)
        data=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
        if a.report:
            a.report.parent.mkdir(parents=True,exist_ok=True)
            a.report.write_text(data,encoding="utf-8")
        print(data)
        return 0 if report["status"]=="UI_EVIDENCE_ATTESTED" else 2
    except (OSError,ValueError,TypeError,MobileUIReviewError) as exc:
        print(f"MOBILE_UI_REVIEW_BLOCKED: {exc}")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
