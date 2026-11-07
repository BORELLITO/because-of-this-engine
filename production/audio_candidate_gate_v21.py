"""V2.1 future music source anti-reuse guard, grounded in real local bytes.

Historical originals and VERIFIED completed masters are forbidden as new music.
Music uniqueness is necessary, NOT sufficient for composition/acoustic originality.
SFX requires separately evidenced 3-video cooldown.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from production.audio_acoustic_fingerprint_v21 import CATALOG_PATH, review_file

SHA = re.compile(r"^[0-9a-f]{64}$")
MASTER_REGISTRY = Path("episodes/audio-rendered-master-registry.json")
LEGACY_REGISTRY = Path("episodes/audio-memory-registry.json")


def _read(path: Path) -> dict[str, Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):raise ValueError("expected registry JSON object")
    return obj


def historical_identities(master: dict[str,Any], legacy: dict[str,Any]) -> dict[str,set[str]]:
    protected={"sha256":set(),"drive_file_id":set(),"track_id":set()}
    for item in legacy.get("tracks",[]):
        if not isinstance(item,dict):raise ValueError("malformed legacy entry")
        for key in protected:
            value=str(item.get(key) or item.get("source_file_sha256") if key=="sha256" else item.get(key) or "").strip().lower()
            if value and not value.startswith("pending"):protected[key].add(value)
    for item in master.get("rendered_masters",[]):
        if not isinstance(item,dict):raise ValueError("malformed master entry")
        song=item.get("music_asset") or {}
        for key in ("sha256","drive_file_id","track_id"):
            value=str(song.get(key) or "").strip().lower()
            if value:protected[key].add(value)
    return protected


def check_file(path:Path, candidate:dict[str,Any],*,root:Path)->dict[str,Any]:
    issues=[]
    if not path.is_file():return {"gate":"NEW_MUSIC_REUSE_V21","status":"BLOCKED","failures":["source audio bytes unavailable"],"ready_for_render":False}
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size<1024:issues.append("audio is too small to verify as full source")
    specified=str(candidate.get("sha256") or "").strip().lower()
    if specified != digest or not SHA.fullmatch(specified):issues.append("declared source SHA-256 does not match actual audio bytes")
    # Probe the actual bytes, not a caller-supplied file extension or flag.
    try:
        result=subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name",
             "-of","json",str(path)],capture_output=True,text=True,timeout=25,check=True)
        probe=json.loads(result.stdout)
        streams=probe.get("streams") or []
        duration=float((probe.get("format") or {}).get("duration") or 0)
        if duration<10 or not any(s.get("codec_type")=="audio" for s in streams):
            issues.append("source is not a decodable music-length audio file")
    except (OSError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired,json.JSONDecodeError):
        issues.append("source audio decoding/ffprobe failed")
    if candidate.get("kind") not in {"music_bed","sfx"}:issues.append("unsupported audio kind")
    if candidate.get("license_verified") is not True:
        issues.append("item-specific commercial license not independently verified")
    master=_read(root/MASTER_REGISTRY)
    legacy=_read(root/LEGACY_REGISTRY)
    protected=historical_identities(master,legacy)
    for key in protected:
        value=digest if key=="sha256" else str(candidate.get(key) or "").strip().lower()
        if value and value in protected[key]:
            issues.append(f"historical audio identity reused:{key}:{value}")
    acoustic = None
    if candidate.get("kind") == "music_bed":
        acoustic = review_file(path, root / CATALOG_PATH)
        if acoustic["status"] != "PASS":
            reasons = acoustic.get("failures") or [
                "Acoustic similarity to historical music is ambiguous or reused"
            ]
            issues.extend("acoustic:" + str(reason) for reason in reasons)
    if candidate.get("kind")=="sfx":
        # Counting checked-in video order from missing release logs is unsafe.
        issues.append("3-video SFX cooldown cannot be proved by existing historical record")
    if candidate.get("acoustic_uniqueness_qa") != "VERIFIED":
        issues.append("acoustic similarity/copyright review for new composition not verified")
    return {
        "gate":"NEW_MUSIC_REUSE_V21",
        "status":"PASS" if not issues else "BLOCKED",
        "failures":issues,
        "input_sha256":digest,
        "known_historical_source_count":len(protected["sha256"]),
        "acoustic_fingerprint_review":acoustic,
        "identity_check_pass":not issues,
        "ready_for_render":False,
        "publication_authorized":False,
        "scope":"IDENTITY_AND_DECODING_ONLY_NEXT_STAGE_REQUIRED",
        "note":"This validates exact identities and real Chromaprint similarity against the limited checked-in catalog; it does NOT establish full historical coverage, copyright clearance or publication rights."
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--candidate-json",type=Path,required=True)
    args=p.parse_args()
    root=args.repo_root.resolve()
    try:report=check_file(args.file.resolve(),_read(args.candidate_json.resolve()),root=root)
    except (OSError,ValueError,json.JSONDecodeError) as e:
        report={"gate":"NEW_MUSIC_REUSE_V21","status":"BLOCKED","failures":[str(e)],"ready_for_render":False}
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report["status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
