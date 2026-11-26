#!/usr/bin/env python3
"""Download and hash the human-approved Episode 005 V2.1 preview visuals.

Segmented archival sources are trimmed before entering the canonical cache.
The manifest stores both the source checksum and the exact trimmed checksum.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from production.active_visual_source_v21 import validate_scene_manifest

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl","--fail","--location","--retry","2","--retry-delay","2","--connect-timeout","20","--max-time","600","--max-filesize","200M",url,"--output",str(target)],check=True)

def _download_urls(url: str) -> list[str]:
    """Return bounded equivalent URLs for transient archival CDN drift.

    The checksum remains the authority. Query variants only force a fresh
    delivery path; they never change the approved source identity.
    """
    separator = "&" if "?" in url else "?"
    candidates = [url, f"{url}{separator}download=1", f"{url}{separator}cnt=0"]
    return list(dict.fromkeys(candidates))

def download_verified(url: str, target: Path, expected: str, candidate_id: str) -> None:
    """Download until the approved checksum matches, then promote atomically."""
    failures: list[str] = []
    for attempt, candidate_url in enumerate(_download_urls(url), start=1):
        attempt_path = target.with_name(f".{target.name}.attempt-{attempt}")
        attempt_path.unlink(missing_ok=True)
        try:
            download(candidate_url, attempt_path)
            actual = sha256_file(attempt_path)
            if actual == expected:
                attempt_path.replace(target)
                return
            failures.append(f"attempt {attempt}: {actual}")
        except (OSError, subprocess.CalledProcessError) as error:
            failures.append(f"attempt {attempt}: {type(error).__name__}")
        finally:
            attempt_path.unlink(missing_ok=True)
    detail = "; ".join(failures)
    raise SystemExit(
        f"SHA-256 mismatch for {candidate_id}: expected {expected}; {detail}"
    )

def trim_source(source: Path, target: Path, segment: dict[str, Any]) -> None:
    start=float(segment["start_seconds"]); end=float(segment["end_seconds"])
    if start < 0 or end <= start: raise SystemExit(f"Invalid source_segment: {segment}")
    target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{start:.3f}","-to",f"{end:.3f}","-i",str(source),"-map","0:v:0","-map","0:a?","-c","copy","-avoid_negative_ts","make_zero",str(target)],check=True)

def prepare_asset(asset: dict[str, Any], target: Path) -> str:
    segment=asset.get("source_segment"); source_url=str(asset.get("media_url","")).strip()
    candidate_id = str(asset.get("candidate_id", "")).strip()
    expected_asset = str(asset.get("sha256", "")).strip().lower()
    if not segment:
        download_verified(source_url, target, expected_asset, candidate_id)
        return "downloaded"
    with tempfile.TemporaryDirectory(prefix="v21-source-") as temporary:
        source=Path(temporary)/"source.mp4"
        expected=str(asset.get("source_sha256","")).strip().lower()
        if expected:
            download_verified(source_url, source, expected, f"{candidate_id} source")
        else:
            download(source_url, source)
        trim_source(source,target,segment)
    return "downloaded_segment"

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True); parser.add_argument("--output-root",type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding="utf-8"))
    gate=validate_scene_manifest(manifest,args.manifest,expected_episode_id=str(manifest.get("episode_id") or "episode-005"))
    if gate["status"] != "PASS": raise SystemExit("Active V2.1 visual source gate blocked intake: "+"; ".join(gate["failures"]))
    assets=manifest.get("assets")
    if not isinstance(assets,list) or len(assets)!=16: raise SystemExit("Episode 005 preview requires exactly 16 manifest assets.")
    downloaded=[]; seen_ids=set()
    for asset in assets:
        if not isinstance(asset,dict): raise SystemExit("Every preview asset must be an object.")
        cid=str(asset.get("candidate_id","")).strip(); url=str(asset.get("media_url","")).strip(); expected=str(asset.get("sha256","")).strip().lower()
        if not cid or cid in seen_ids: raise SystemExit(f"Invalid or duplicate candidate_id: {cid!r}")
        if not url.startswith("https://"): raise SystemExit(f"Preview media URL must be HTTPS: {cid}")
        if len(expected)!=64: raise SystemExit(f"Preview asset has no valid SHA-256: {cid}")
        seen_ids.add(cid); target=args.output_root/cid/"candidate.mp4"
        if target.is_file() and sha256_file(target)==expected: state="cached"
        else:
            if target.exists(): target.unlink()
            state=prepare_asset(asset,target)
            actual=sha256_file(target)
            if actual!=expected: raise SystemExit(f"SHA-256 mismatch for {cid}: expected {expected}, got {actual}")
        downloaded.append({"candidate_id":cid,"path":str(target),"sha256":expected,"state":state,"segmented":bool(asset.get("source_segment")),"source_segment":asset.get("source_segment")})
    report={"status":"V21_PREVIEW_VISUAL_INTAKE_PASS","episode_id":"episode-005","asset_count":len(downloaded),"assets":downloaded,"promotion":"PREVIEW_ONLY_NOT_PROMOTED","global_catalog_updated":False,"drive_written":False}
    report_path=args.output_root/"download-report.json"; report_path.parent.mkdir(parents=True,exist_ok=True); report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
