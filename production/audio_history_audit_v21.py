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
            if (not isinstance(receipt, dict)
                    or receipt.get("verification_method") != MASTER_PROOF
                    or receipt.get("episode_id") != episode
                    or receipt.get("source_identity_verified_in_mix") is not True
                    or not SHA.fullmatch(str(receipt.get("master_video_sha256") or ""))
                    or not SHA.fullmatch(str(receipt.get("mixed_audio_sha256") or ""))
                    or not str(receipt.get("artifact_id") or "")
                    or not str(receipt.get("mix_execution_log_sha256") or "")):
                failures.append(f"{episode}: no independently verifiable master audio-mix receipt")
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
    if historical_collisions:
        failures.append("historical music source identity collision unresolved")
    if ledger.get("coverage_status") != "VERIFIED_COMPLETE":
        failures.append("audio history completeness has not been independently verified")
    if ledger.get("sfx_coverage_status") != "VERIFIED_COMPLETE":
        failures.append("historical SFX usage coverage has not been independently verified")
    if len(registry) != len(declarations):
        failures.append("historical manifest/registry entry count discrepancy")

    return {
        "gate": "AUDIO_HISTORY_COVERAGE",
        "status": "BLOCKED" if failures else "PASS",
        "failures": failures,
        "declarations": declarations,
        "manifest_music_count": len(declarations),
        "registry_track_count": len(registry),
        "historical_identity_collisions": historical_collisions,
        "verified_original_source_count": len({
            e.get("source_file_sha256") for e in registry
            if isinstance(e, dict) and e.get("source_verification") == "VERIFIED_FROM_ORIGINAL_DRIVE_MP3_BYTES_2026_11_07"
        }),
        "verified_master_audio_count": sum(1 for e in registry if isinstance(e,dict) and e.get("actual_master_audio_verified") is True),
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
