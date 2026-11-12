"""Evidence-first historical music/SFX coverage audit for V2.1.

Downloaded music source bytes are distinct from audible use in delivered masters.
No source hash, declared licence, manifest entry or placeholder can establish
historical master usage or safe reuse. A forged 'VERIFIED_COMPLETE' flag never
removes the release hold without per-master receipts and SFX evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SHA = re.compile(r"^[0-9a-f]{64}$")
MASTER_PROOF = "VERIFIED_MASTER_AUDIO_MIX_AND_SOURCE_IDENTITY"
VALID_KIND = {"music_bed", "procedural_music", "sfx"}


def _keys(music: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for key in ("track_id", "drive_file_id", "sha256"):
        value = str(music.get(key) or "").strip().lower()
        if value and not value.startswith("pending"):
            keys.add(key + ":" + value)
    return keys


def audit(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    failures: list[str] = []
    declarations: list[dict[str, Any]] = []
    by_key: dict[str, list[str]] = defaultdict(list)
    ledger_path = repo_root / "episodes" / "audio-memory-registry.json"
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if not isinstance(ledger, dict) or not isinstance(ledger.get("tracks"), list):
            raise ValueError("audio history registry has invalid structure")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        ledger = {"tracks": []}
        failures.append(f"audio history registry unavailable or invalid: {exc}")

    for manifest_path in sorted((repo_root / "episodes").glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("manifest is not an object")
            music = manifest.get("music") or {}
            if not isinstance(music, dict):
                raise ValueError("music must be an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"unreadable historical manifest {manifest_path.parent.name}: {exc}")
            continue
        if not music:
            continue
        episode_id = str(manifest.get("video_id") or manifest_path.parent.name)
        keys = _keys(music)
        if not keys:
            failures.append(f"{episode_id}: historical soundtrack has no stable identity")
        for key in keys:
            by_key[key].append(episode_id)
        declarations.append({
            "episode_id": episode_id,
            "source_manifest": str(manifest_path.relative_to(repo_root)),
            "identity_keys": sorted(keys),
            "evidence_level": "DECLARED_IN_MANIFEST_NOT_PROVEN_USED",
        })

    registry = ledger.get("tracks") or []
    indexed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    distinct_episodes: set[str] = set()
    for index, entry in enumerate(registry):
        if not isinstance(entry, dict):
            failures.append(f"audio registry entry {index} is invalid")
            continue
        episode = str(entry.get("episode_id") or "")
        if not episode or entry.get("kind", "music_bed") not in VALID_KIND:
            failures.append(f"audio registry entry {index}: missing episode or unsupported kind")
            continue
        indexed[episode].append(entry)
        distinct_episodes.add(episode)
        keys = _keys(entry)
        if entry.get("kind") != "sfx" and not keys:
            failures.append(f"{episode}: registered music without source identity")
        if entry.get("source_file_sha256") and not SHA.fullmatch(str(entry["source_file_sha256"])):
            failures.append(f"{episode}: invalid source SHA-256")
        if entry.get("actual_master_audio_verified") is not True:
            failures.append(f"{episode}: master audio usage is not verified")
        else:
            # The master receipt must prove that THIS source is present in THIS
            # master. Merely hashing the input file or rendered MP4 is not enough.
            receipt = entry.get("master_release_evidence")
            receipt_failures = validate_mix_receipt(receipt, expected_episode_id=episode)
            if receipt_failures:
                failures.append(
                    f"{episode}: no independently verifiable master audio-mix receipt:"
                    + ";".join(receipt_failures)
                )
        if entry.get("published_use_verified") is True and entry.get("actual_master_audio_verified") is not True:
            failures.append(f"{episode}: publication assertion without master proof")

    for item in declarations:
        episode = item["episode_id"]
        tracks = indexed.get(episode, [])
        matches = [t for t in tracks if _keys(t) & set(item["identity_keys"])]
        if len(matches) != 1:
            failures.append(f"{episode}: expected exactly one matching registry music identity; found {len(matches)}")
        elif matches[0].get("historical_manifest") not in {item["source_manifest"], None}:
            failures.append(f"{episode}: registry points to wrong historical manifest")
    unknown = sorted(distinct_episodes - {x["episode_id"] for x in declarations})
    if unknown:
        failures.append("audio registry contains episodes with no historical manifest: " + ",".join(unknown))

    historical_collisions = [
        {"identity": k, "declared_by": sorted(set(v))}
        for k, v in sorted(by_key.items()) if len(set(v)) > 1
    ]
    # A duplicate declaration is not silently accepted, but it is no longer
    # an "unresolved" diagnostic when the registry explicitly records the
    # identity conflict and keeps it quarantined. Actual audible use is still
    # unproven below, so coverage remains blocked until master receipts exist.
    documented_conflicts = ledger.get("known_identity_conflicts") or []
    quarantined_collisions: list[dict[str, Any]] = []
    unresolved_collisions: list[dict[str, Any]] = []
    for collision in historical_collisions:
        identity = collision["identity"]
        value = identity.split(":", 1)[1] if ":" in identity else identity
        documented = any(
            isinstance(item, dict)
            and value in {
                str(item.get("drive_file_id") or "").strip().lower(),
                str(item.get("sha256") or "").strip().lower(),
            }
            for item in documented_conflicts
        )
        (quarantined_collisions if documented else unresolved_collisions).append(collision)
    if unresolved_collisions:
        failures.append("historical music source identity collision unresolved")
    if ledger.get("coverage_status") != "VERIFIED_COMPLETE":
        failures.append("audio history completeness has not been independently verified")
    if ledger.get("sfx_coverage_status") != "VERIFIED_COMPLETE":
        failures.append("historical SFX usage coverage has not been independently verified")
    if len(registry) != len(declarations):
        failures.append("historical manifest/registry entry count discrepancy")

    # Additional REAL completed-master inventory is independent of archival
    # manifest declarations. It must not retroactively mark legacy rows as used.
    master_path = repo_root / "episodes" / "audio-rendered-master-registry.json"
    master_rows: list[dict[str, Any]] = []
    full_track_collisions: list[dict[str, Any]] = []
    try:
        master_data=json.loads(master_path.read_text(encoding="utf-8"))
        master_rows=master_data.get("rendered_masters", [])
        full_track_collisions=master_data.get("verified_full_track_collisions", [])
        if not isinstance(master_rows,list) or not isinstance(full_track_collisions,list):
            raise ValueError("master registry arrays required")
        if len(master_rows) != 4 or len({x["episode_id"] for x in master_rows}) != len(master_rows):
            failures.append("four unique historical final masters are not evidenced")
        master_shas = [x.get("master_video",{}).get("sha256") for x in master_rows]
        if any(not SHA.fullmatch(str(x or "")) for x in master_shas):
            failures.append("a historical final master SHA-256 is invalid")
        by_music:dict[str,set[str]]=defaultdict(set)
        for x in master_rows:
            music=x.get("music_asset",{})
            sh=str(music.get("sha256") or "")
            if not SHA.fullmatch(sh):
                failures.append("master music identity is not a verified SHA-256")
                continue
            if music.get("verified_original_bytes") is not True:
                failures.append("master music original bytes not independently verified")
            by_music[sh].add(str(x.get("episode_id") or ""))
        actual=[{"sha256":sha,"episodes":sorted(owners)}
                for sha,owners in sorted(by_music.items()) if len(owners)>1]
        if {x.get("track_sha256") for x in full_track_collisions} != {x["sha256"] for x in actual}:
            failures.append("full soundtrack reuse collision not accounted for in report")
        if actual:
            failures.append("verified completed-master music source reused across historical episodes")
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        failures.append(f"completed-master evidence registry unavailable or invalid:{exc}")
        master_rows=[]
        full_track_collisions=[]

    return {
        "gate": "AUDIO_HISTORY_COVERAGE",
        "status": "BLOCKED" if failures else "PASS",
        "failures": failures,
        "declarations": declarations,
        "manifest_music_count": len(declarations),
        "registry_track_count": len(registry),
        "historical_identity_collisions": historical_collisions,
        "quarantined_historical_identity_collisions": quarantined_collisions,
        "unresolved_historical_identity_collisions": unresolved_collisions,
        "verified_original_source_count": len({
            e.get("source_file_sha256") for e in registry
            if isinstance(e, dict) and e.get("source_verification") == "VERIFIED_FROM_ORIGINAL_DRIVE_MP3_BYTES_2026_11_07"
        }),
        "verified_master_audio_count": sum(1 for e in registry if isinstance(e,dict) and e.get("actual_master_audio_verified") is True),
        "verified_delivered_master_file_count": len(master_rows),
        "delivered_music_collision_count": len(full_track_collisions),
        "delivered_master_evidence_is_not_legacy_manifest_proof": True,
        "historical_use_verified": not failures,
        "render": "NOT_RUN",
        "publication": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = audit(args.repo_root)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

