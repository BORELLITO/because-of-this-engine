#!/usr/bin/env python3
"""Fail-closed multi-episode music/SFX audit, including preview snapshots.

Track labels are NOT proof that generated audio is fresh. Real checked SHA256,
case-sensitive Drive IDs and historical evidence are independent identities.
An archive may contain old duplication; it is never silently approved for
a NEW release. A reused SFX cannot pass on self-reported cooldown counts.
This audit is read-only and never generates, retires or modifies audio.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMA = "2.0"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_FINAL_OK = {"APPROVED"}
_ALLOWED_SNAPSHOT = ("manifest.json", "preview-manifest.json")


class AudioReuseError(RuntimeError):
    pass


def _string(v: Any) -> str:
    return str(v or "").strip()


def _sha(value: Any) -> str:
    v = _string(value).lower()
    return v if _SHA.fullmatch(v) else ""


def _item_url(value: Any) -> str:
    """Only an item-specific stock URL is an identity; category pages are not."""
    raw = _string(value)
    if not raw:
        return ""
    p = urlsplit(raw)
    host = (p.hostname or "").lower()
    path = p.path.rstrip("/")
    if not host or not path:
        return ""
    if "mixkit.co" in host and ("/free-stock-music/mood/" in path or path == "/free-stock-music"):
        return ""
    if "youtube.com" in host or "support.google.com" in host:
        return ""
    if "pixabay.com" in host and path in ("/music", "/sound-effects"):
        return ""
    return host + path.lower()


def identity_keys(track: dict[str, Any]) -> set[str]:
    """Keys for release identity; Drive IDs remain case-sensitive."""
    keys: set[str] = set()
    if not isinstance(track, dict):
        return keys
    track_id = _string(track.get("track_id") or track.get("effect_id"))
    if track_id and not track_id.upper().startswith(("PENDING-", "TBD")):
        keys.add("track_id:" + track_id.casefold())
    digest = _sha(track.get("sha256"))
    if digest:
        keys.add("sha256:" + digest)
    drive_id = _string(track.get("drive_file_id"))
    if drive_id:
        keys.add("drive_file_id:" + drive_id)
    item = _item_url(track.get("source_page_url") or track.get("source_url"))
    if item:
        keys.add("source_item:" + item)
    return keys


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AudioReuseError(f"Unreadable music history: {path}") from exc
    if not isinstance(value, dict):
        raise AudioReuseError(f"Invalid music history object: {path}")
    if not _string(value.get("video_id")):
        raise AudioReuseError(f"Historical manifest missing video_id: {path}")
    return value


def _snapshots(root: Path) -> list[Path]:
    ep = root / "episodes"
    if not ep.is_dir():
        raise AudioReuseError("AUDIO_EPISODE_HISTORY_MISSING")
    return sorted(path for n in _ALLOWED_SNAPSHOT for path in ep.glob(f"*/{n}") if path.is_file())


def _track_records(manifest: dict[str, Any], owner: str, episode_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    music = manifest.get("music")
    if isinstance(music, dict) and music:
        out.append({"kind": "music", "owner": owner, "episode_id": episode_id,
                    "track": music, "keys": identity_keys(music)})
    effects = manifest.get("effects") or []
    if not isinstance(effects, list):
        raise AudioReuseError(f"effects must be a list for {episode_id}")
    for effect in effects:
        if not isinstance(effect, dict):
            raise AudioReuseError(f"Malformed effect record for {episode_id}")
        out.append({"kind": "effect", "owner": owner, "episode_id": episode_id,
                    "track": effect, "keys": identity_keys(effect)})
    return out


def _ledger(root: Path, registry_path: Path | None) -> tuple[dict[str, Any], Path]:
    path = registry_path or root / "episodes" / "audio-memory-registry.json"
    if not path.is_file():
        raise AudioReuseError("AUDIO_MEMORY_UNAVAILABLE: checked-in registry file is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AudioReuseError("Invalid audio registry") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA:
        raise AudioReuseError("Audio registry must be schema 2.0")
    if not isinstance(value.get("tracks"), list):
        raise AudioReuseError("Audio registry tracks must be a list")
    if "effects" in value and not isinstance(value["effects"], list):
        raise AudioReuseError("Audio registry effects must be a list")
    for kind in ("tracks", "effects"):
        for entry in value.get(kind, []):
            if not isinstance(entry, dict) or not _string(entry.get("episode_id")):
                raise AudioReuseError(f"Audio registry {kind} item requires episode_id")
    return value, path


def _verified_historical_hashes(root: Path) -> dict[str, Any]:
    path = root / "audits" / "audio_verified_history_v11.json"
    if not path.is_file():
        return {"status": "EVIDENCE_NOT_PRESENT", "entries": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AudioReuseError("Verified historical audio ledger unreadable") from exc
    if (not isinstance(value, dict) or value.get("schema_version") != "1.1"
            or not isinstance(value.get("entries"), list)):
        raise AudioReuseError("Invalid verified historical audio evidence schema")
    for entry in value["entries"]:
        if not isinstance(entry, dict) or not _sha(entry.get("sha256")):
            raise AudioReuseError("Verified historical audio evidence contains invalid SHA-256")
        if not isinstance(entry.get("drive_file_ids"), list):
            raise AudioReuseError("Verified historical audio evidence missing Drive identities")
    return value


def _verify_bytes(manifest_path: Path, track: dict[str, Any], errors: list[str]) -> None:
    raw = _string(track.get("path"))
    if not raw:
        errors.append("music.path is missing")
        return
    root = manifest_path.parent.resolve()
    candidate = (root / raw).resolve()
    if root not in candidate.parents or not candidate.is_file():
        errors.append("music file missing or path escapes episode folder")
        return
    expected = _sha(track.get("sha256"))
    if not expected:
        errors.append("music.sha256 must be verified 64-character SHA-256")
        return
    h = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != expected:
        errors.append("music actual bytes do not match declared SHA-256")


def audit(
    manifest_path: Path,
    repo_root: Path,
    registry_path: Path | None = None,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Evaluate fresh allocation against all local snapshots and ledger.

    In strict final mode, require genuine byte proof and registry registration.
    Archive discrepancies are reported but cannot be rewritten by this tool.
    """
    root = repo_root.resolve()
    target = manifest_path.resolve()
    current = _read_manifest(target)
    current_id = _string(current["video_id"])
    music = current.get("music") or {}
    errors: list[str] = []
    notes: list[str] = []
    if not isinstance(music, dict):
        raise AudioReuseError("music must be an object")
    target_keys = identity_keys(music)
    if not target_keys:
        errors.append("music lacks a traceable track/source identity")
    if not _string(music.get("track_id")):
        errors.append("music.track_id is missing")
    target_owner = target.parent.resolve().as_posix()
    reg, path = _ledger(root, registry_path)
    snapshots = _snapshots(root)
    records: list[dict[str, Any]] = []
    for item in snapshots:
        m = _read_manifest(item)
        records.extend(_track_records(m, item.parent.resolve().as_posix(), _string(m["video_id"])))
    for kind in ("tracks", "effects"):
        for track in reg.get(kind, []):
            records.append({
                "kind": "music" if kind == "tracks" else "effect",
                "owner": "ledger:" + _string(track["episode_id"]),
                "episode_id": _string(track["episode_id"]),
                "track": track,
                "keys": identity_keys(track),
            })

    collisions: list[dict[str, Any]] = []
    for key in sorted(target_keys):
        for rec in records:
            if rec["kind"] != "music" or key not in rec["keys"]:
                continue
            is_same_folder = rec["owner"] == target_owner
            is_same_registry_episode = (rec["owner"].startswith("ledger:") and rec["episode_id"] == current_id)
            if not is_same_folder and not is_same_registry_episode:
                collisions.append({"key": key, "episode_id": rec["episode_id"]})
    collisions = sorted({(x["key"], x["episode_id"]) for x in collisions})
    if collisions:
        errors.append(f"complete music reused across episodes: {len(collisions)} identity collisions")

    observed = _verified_historical_hashes(root)
    observed_hits = []
    declared_digest = _sha(music.get("sha256"))
    if declared_digest:
        for entry in observed.get("entries", []):
            if declared_digest == _sha(entry.get("sha256")):
                observed_hits.append({"sha256": declared_digest, "drive_file_ids": entry.get("drive_file_ids", [])})
    if observed_hits:
        errors.append("actual SHA-256 matches verified music bytes used in historical episodes")

    effect_history: list[dict[str, Any]] = []
    for effect in current.get("effects") or []:
        keys = identity_keys(effect)
        if strict:
            if not _sha(effect.get("sha256")):
                errors.append("effect requires SHA-256 in final mode")
            if not _string(effect.get("license")):
                errors.append("effect license is missing")
        reused = []
        for key in keys:
            for rec in records:
                if rec["kind"] != "effect" or key not in rec["keys"]:
                    continue
                if rec["owner"] == target_owner:
                    continue
                if rec["owner"].startswith("ledger:") and rec["episode_id"] == current_id:
                    continue
                reused.append({"key": key, "episode_id": rec["episode_id"]})
        if reused:
            effect_history.extend(reused)
            errors.append("SFX reuse requires independent evidence of three published intervening videos")
        elif strict and not keys:
            errors.append("SFX effect must have traceable source identity")

    if strict:
        if not declared_digest:
            errors.append("music.sha256 is required; track_id alone cannot prove freshness")
        if music.get("commercial_use") is not True or _string(music.get("license_status")).upper() not in _FINAL_OK:
            errors.append("music requires approved commercial rights evidence for final mode")
        if music.get("preview_only") is True:
            errors.append("preview-only music cannot enter final release")
        if music.get("source") == "engine_generated":
            generation = music.get("generation") or {}
            if not isinstance(generation, dict) or not _string(generation.get("script")):
                errors.append("procedural music requires generator provenance")
        elif not _item_url(music.get("source_page_url") or music.get("source_url")):
            errors.append("stock music needs an item-specific source page, not a category/help page")
        if (music.get("similarity_review") or {}).get("status") != "PASS":
            errors.append("independently reviewed music similarity evidence must be PASS")
        registry_owners = [x for x in reg["tracks"] if _string(x.get("episode_id")) == current_id
                           and bool(target_keys & identity_keys(x))]
        if not registry_owners:
            errors.append("music absent from durable audio-memory registry for this final episode")
        _verify_bytes(target, music, errors)
    elif not declared_digest:
        notes.append("music bytes unverified: preview metadata cannot prove unique audio")

    unique_archive_music: dict[str, set[str]] = defaultdict(set)
    for rec in records:
        if rec["kind"] != "music":
            continue
        for key in rec["keys"]:
            if key.startswith(("sha256:", "drive_file_id:")):
                unique_archive_music[key].add(rec["owner"])
    historical_dup = sorted(k for k, owners in unique_archive_music.items() if len(owners) > 1)
    if not reg["tracks"]:
        notes.append("global registry contains zero registered tracks: historical memory incomplete")
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "video_id": current_id,
        "errors": list(dict.fromkeys(errors)), "notes": notes,
        "checked_target_keys": sorted(target_keys),
        "historical_music_included": True,
        "scanned_manifest_count": len(snapshots),
        "ledger_track_count": len(reg["tracks"]),
        "ledger_effect_count": len(reg.get("effects", [])),
        "verified_historical_bytes_evidence_count": len(observed.get("entries", [])),
        "actual_sha256_reuse_hits": observed_hits,
        "identity_collision_count": len(collisions),
        "collision_examples": [{"key": k, "episode_id": ep} for k, ep in collisions[:20]],
        "historical_duplicate_key_count": len(historical_dup),
        "historical_duplicate_key_examples": historical_dup[:12],
        "sfx_reuse_review_required_count": len(effect_history),
        "policy": "full soundtracks never reused; SFX reuse requires independent 3-published-video cooldown evidence",
        "provenance_status": "NOT_INDEPENDENTLY_LICENSE_VERIFIED",
        "scope": "local snapshots plus durable registry and verified historical byte evidence; not full Drive or Git branch history",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--registry", type=Path)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    try:
        result = audit(a.manifest.resolve(), a.repo_root.resolve(),
                       a.registry.resolve() if a.registry else None, strict=a.strict)
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError, AudioReuseError) as exc:
        print("AUDIO_REUSE_BLOCKED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
