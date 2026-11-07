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
from pathlib import Path
from typing import Any

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
        "ready_for_render":not issues,
        "publication_authorized":False,
        "note":"Exact file anti-reuse + declared acoustic QA; this gate does not perform full acoustic fingerprinting."
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
