#!/usr/bin/env python3
"""Cross-episode soundtrack reuse gate with append-only historical awareness.

Historical tracks remain consumed. A checked-in audio-memory ledger must have
well-formed track IDs and episode references. Fail closed if the ledger is
missing; do not infer copyright clearance from unique hashes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

class AudioReuseError(RuntimeError): pass

def identity_keys(track: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("track_id", "sha256", "drive_file_id"):
        value = str(track.get(field) or "").strip()
        if value and not value.startswith("PENDING-"):
            keys.add(field + ":" + value.lower())
    return keys

def audit(manifest_path: Path, repo_root: Path, registry_path: Path | None = None) -> dict[str, Any]:
    current = json.loads(manifest_path.read_text(encoding="utf-8"))
    current_id = str(current.get("video_id") or manifest_path.parent.name)
    current_music = current.get("music") or {}
    target_keys = identity_keys(current_music)
    errors: list[str] = []
    comparisons: dict[str, list[str]] = {}
    if registry_path is not None and not registry_path.is_file():
        raise AudioReuseError("AUDIO_MEMORY_UNAVAILABLE: registry file is missing")
    for path in sorted((repo_root / "episodes").glob("*/manifest.json")):
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise AudioReuseError(f"Unreadable music history: {path}")
        episode_id = str(value.get("video_id") or path.parent.name)
        music = value.get("music") or {}
        for key in identity_keys(music):
            comparisons.setdefault(key, []).append(episode_id)
    if registry_path:
        try: ledger = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise AudioReuseError("Invalid audio registry") from exc
        if not isinstance(ledger.get("tracks"), list):
            raise AudioReuseError("Audio registry tracks must be a list")
        for track in ledger["tracks"]:
            if not isinstance(track, dict) or not str(track.get("episode_id") or "").strip():
                raise AudioReuseError("Audio registry item requires episode_id")
            track_id = str(track["episode_id"])
            for key in identity_keys(track):
                comparisons.setdefault(key, []).append(track_id)
            if track_id == current_id and track.get("reuse_status") not in {None,"FRESH","APPROVED_REUSE"}:
                errors.append("Current registry track has invalid reuse_status")
    for key in sorted(target_keys):
        owners = sorted(set(comparisons.get(key, [])) - {current_id})
        if owners:
            errors.append(f"Soundtrack identity reused across episodes: {key} -> {owners}")
    report = current_music.get("similarity_review") or {}
    if report.get("status") not in {None, "PASS"}:
        errors.append("Current music similarity review is not PASS")
    return {
        "status":"PASS" if not errors else "BLOCKED",
        "video_id":current_id, "errors":errors,
        "checked_target_keys":sorted(target_keys),
        "historical_music_included":True,
        "policy":"full tracks never reused; effect reuse subject to separate three-video cooldown QA",
        "note":"Track/source identity, NOT acoustic similarity; no sound license or actual 3-episode SFX cooldown verified",
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--registry",type=Path)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    try:
        result=audit(a.manifest.resolve(),a.repo_root.resolve(),a.registry.resolve() if a.registry else None)
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False))
        return 0 if result["status"]=="PASS" else 1
    except (OSError,ValueError,TypeError,json.JSONDecodeError,AudioReuseError) as exc:
        print("AUDIO_REUSE_BLOCKED: "+str(exc));return 1

if __name__=="__main__":raise SystemExit(main())
