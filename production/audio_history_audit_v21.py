"""Read-only historical audio inventory coverage audit for V2.1.

Historical manifest declarations are NOT proof of audible use or publication.
Never automatically mark the registry complete, or grant track reuse/licensing.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


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
    path = repo_root / "episodes" / "audio-memory-registry.json"
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(ledger, dict) or not isinstance(ledger.get("tracks"), list):
            raise ValueError("audio history registry has invalid structure")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        ledger = {"tracks": []}
        failures.append(f"audio history registry unavailable or invalid: {exc}")

    for manifest_path in sorted((repo_root / "episodes").glob("*/manifest.json")):
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(m, dict):
                raise ValueError("manifest is not an object")
            music = m.get("music") or {}
            if not isinstance(music, dict):
                raise ValueError("music is not an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"unreadable historical manifest {manifest_path.parent.name}: {exc}")
            continue
        if not music:
            continue
        episode_id = str(m.get("video_id") or manifest_path.parent.name)
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
    indexed: dict[str, set[str]] = defaultdict(set)
    for index, entry in enumerate(registry):
        if not isinstance(entry, dict) or not entry.get("episode_id"):
            failures.append(f"audio registry entry {index} is invalid")
            continue
        for key in _keys(entry):
            indexed[str(entry["episode_id"])].add(key)

    for item in declarations:
        episode = item["episode_id"]
        if not item["identity_keys"] or not indexed.get(episode, set()).intersection(item["identity_keys"]):
            failures.append(f"{episode}: no matching audio registry identity evidence")

    if ledger.get("coverage_status") != "VERIFIED_COMPLETE":
        failures.append("audio history completeness has not been independently verified")

    historical_collisions = [
        {"identity": k, "declared_by": sorted(set(v))}
        for k, v in sorted(by_key.items()) if len(set(v)) > 1
    ]
    return {
        "gate": "AUDIO_HISTORY_COVERAGE",
        "status": "BLOCKED" if failures else "PASS",
        "failures": failures,
        "declarations": declarations,
        "manifest_music_count": len(declarations),
        "registry_track_count": len(registry),
        "historical_identity_collisions": historical_collisions,
        "historical_use_verified": False,
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
