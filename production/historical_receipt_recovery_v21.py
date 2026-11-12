"""Fail-closed recovery inventory for historical V2.1 mix receipts.

This module does not infer audible use from a manifest, waveform similarity, or a
Drive file hash. It inventories canonical masters and evaluates only explicit
strict receipts supplied by an operator. Missing receipts remain BLOCKED.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from production.mix_receipt_v21 import validate_mix_receipt

SHA = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RECEIPT_FIELDS = (
    "master_video_sha256",
    "mixed_audio_sha256",
    "narration_sha256",
    "mix_command_sha256",
    "mix_execution_log_sha256",
    "artifact_id",
    "music_sources",
    "sfx_sources",
    "sfx_usage_status",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_sha(value: Any) -> bool:
    return bool(SHA.fullmatch(str(value or "").strip().lower()))


def _receipt_map(evidence: Any) -> dict[str, Any]:
    if evidence is None:
        return {}
    if isinstance(evidence, dict) and isinstance(evidence.get("receipts"), list):
        return {
            str(item.get("episode_id") or "").strip(): item
            for item in evidence["receipts"]
            if isinstance(item, dict) and str(item.get("episode_id") or "").strip()
        }
    if isinstance(evidence, dict) and isinstance(evidence.get("receipts"), dict):
        return {
            str(key).strip(): value
            for key, value in evidence["receipts"].items()
            if str(key).strip()
        }
    if isinstance(evidence, list):
        return {
            str(item.get("episode_id") or "").strip(): item
            for item in evidence
            if isinstance(item, dict) and str(item.get("episode_id") or "").strip()
        }
    raise ValueError("evidence must be a list or an object with receipts")


def _master_inventory_row(master: Any) -> dict[str, Any]:
    if not isinstance(master, dict):
        return {
            "episode_id": "",
            "status": "BLOCKED",
            "missing_evidence": ["master row must be an object"],
        }
    video = master.get("master_video") or {}
    music = master.get("music_asset") or {}
    episode_id = str(master.get("episode_id") or "").strip()
    missing: list[str] = []
    if not episode_id:
        missing.append("episode_id")
    if not _is_sha(video.get("sha256")):
        missing.append("master_video_sha256")
    if not _is_sha(video.get("mixed_audio_decoded_48k_mono_s16le_sha256")):
        missing.append("mixed_audio_sha256")
    if not _is_sha(music.get("sha256")):
        missing.append("music_source_sha256")
    return {
        "episode_id": episode_id,
        "master_drive_file_id": str(video.get("drive_file_id") or "").strip(),
        "master_video_sha256": str(video.get("sha256") or "").strip().lower(),
        "mixed_audio_sha256": str(
            video.get("mixed_audio_decoded_48k_mono_s16le_sha256") or ""
        ).strip().lower(),
        "music_source_drive_file_id": str(music.get("drive_file_id") or "").strip(),
        "music_source_sha256": str(music.get("sha256") or "").strip().lower(),
        "source_bytes_verified": music.get("verified_original_bytes") is True,
        "status": "BLOCKED" if missing else "CANDIDATE",
        "missing_evidence": missing,
    }


def build_recovery_report(
    master_registry: Any,
    evidence: Any = None,
) -> dict[str, Any]:
    """Evaluate strict receipts against the canonical completed-master registry."""
    if not isinstance(master_registry, dict):
        raise ValueError("master registry must be an object")
    masters = master_registry.get("rendered_masters")
    if not isinstance(masters, list) or not masters:
        raise ValueError("master registry must contain rendered_masters")
    receipts = _receipt_map(evidence)
    rows: list[dict[str, Any]] = []
    for master in masters:
        row = _master_inventory_row(master)
        episode_id = row["episode_id"]
        receipt = receipts.get(episode_id)
        failures = list(row["missing_evidence"])
        if receipt is None:
            failures.append("strict_mix_receipt")
        else:
            failures.extend(
                validate_mix_receipt(receipt, expected_episode_id=episode_id)
            )
            if receipt.get("master_video_sha256") != row["master_video_sha256"]:
                failures.append("receipt master_video_sha256 does not match registry")
            if receipt.get("mixed_audio_sha256") != row["mixed_audio_sha256"]:
                failures.append("receipt mixed_audio_sha256 does not match registry")
        row["receipt_present"] = receipt is not None
        row["receipt_failures"] = sorted(set(failures))
        row["status"] = "READY" if not row["receipt_failures"] else "BLOCKED"
        rows.append(row)
    ready = sum(row["status"] == "READY" for row in rows)
    return {
        "schema_version": "1.0",
        "gate": "AUDIO_HISTORY_RECEIPT_RECOVERY",
        "status": "PASS" if ready == len(rows) else "BLOCKED",
        "master_count": len(rows),
        "ready_count": ready,
        "blocked_count": len(rows) - ready,
        "rows": rows,
        "policy": (
            "Do not promote a historical master or mark audible music/SFX verified "
            "until its strict receipt passes and its hashes match this registry."
        ),
        "next_required_evidence": sorted({
            failure
            for row in rows
            for failure in row["receipt_failures"]
        }),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-registry", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    evidence = _load_json(args.evidence) if args.evidence else None
    report = build_recovery_report(_load_json(args.master_registry), evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
