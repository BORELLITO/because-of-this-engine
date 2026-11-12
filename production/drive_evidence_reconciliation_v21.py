"""Reconcile Drive manifests with the canonical historical audio registry.

Drive manifests, QA receipts, and delivery flags are useful forensic context, but
they are not replayable mix receipts. This module records that distinction
explicitly and is intentionally fail-closed: contextual evidence can never
promote a historical master or certify audible source use.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from production.historical_receipt_recovery_v21 import _is_sha


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_map(evidence: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(evidence, dict) or not isinstance(evidence.get("artifacts"), list):
        raise ValueError("evidence must be an object with an artifacts list")
    result: dict[str, dict[str, Any]] = {}
    for item in evidence["artifacts"]:
        if not isinstance(item, dict):
            continue
        episode_id = str(item.get("episode_id") or "").strip()
        if episode_id:
            result[episode_id] = item
    return result


def _registry_map(master_registry: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(master_registry, dict):
        raise ValueError("master registry must be an object")
    masters = master_registry.get("rendered_masters")
    if not isinstance(masters, list) or not masters:
        raise ValueError("master registry must contain rendered_masters")
    result: dict[str, dict[str, Any]] = {}
    for item in masters:
        if isinstance(item, dict):
            episode_id = str(item.get("episode_id") or "").strip()
            if episode_id:
                result[episode_id] = item
    if not result:
        raise ValueError("master registry has no usable episode IDs")
    return result


def _row(master: dict[str, Any], artifact: dict[str, Any] | None) -> dict[str, Any]:
    episode_id = str(master.get("episode_id") or "").strip()
    canonical_music = master.get("music_asset") or {}
    if artifact is None:
        return {
            "episode_id": episode_id,
            "evidence_status": "NOT_LOCATED",
            "contextual_evidence_present": False,
            "strict_receipt_present": False,
            "strict_receipt_promotable": False,
            "promotion_status": "BLOCKED",
            "blocking_reasons": [
                "no targeted Drive manifest artifact was located",
                "contextual evidence cannot replace strict_mix_receipt",
            ],
        }

    reasons: list[str] = []
    manifest_status = str(artifact.get("manifest_status") or "").strip()
    qa_status = str(artifact.get("qa_status") or "").strip()
    delivery_status = str(artifact.get("delivery_status") or "").strip()
    scope = str(artifact.get("evidence_scope") or "").strip()
    if scope != "MANIFEST_CONTEXT_ONLY":
        reasons.append("evidence_scope must be MANIFEST_CONTEXT_ONLY")
    if artifact.get("strict_receipt_promotable") is not False:
        reasons.append("contextual artifact must explicitly set strict_receipt_promotable=false")
    if not manifest_status:
        reasons.append("manifest_status")
    if not qa_status:
        reasons.append("qa_status")
    if not delivery_status:
        reasons.append("delivery_status")

    declared_music = artifact.get("music_declaration") or {}
    declared_music_id = str(declared_music.get("drive_file_id") or "").strip()
    canonical_music_id = str(canonical_music.get("drive_file_id") or "").strip()
    if declared_music_id and canonical_music_id and declared_music_id != canonical_music_id:
        reasons.append("Drive manifest music declaration differs from canonical source ID")
    declared_music_sha = str(declared_music.get("sha256") or "").strip().lower()
    if declared_music_sha and not _is_sha(declared_music_sha):
        reasons.append("manifest music sha256 is invalid")

    return {
        "episode_id": episode_id,
        "evidence_status": "LOCATED" if not reasons else "INVALID_CONTEXT_RECORD",
        "contextual_evidence_present": True,
        "manifest_drive_file_id": str(artifact.get("manifest_drive_file_id") or "").strip(),
        "manifest_status": manifest_status,
        "qa_status": qa_status,
        "delivery_status": delivery_status,
        "narration_sha256": str(artifact.get("narration_sha256") or "").strip().lower(),
        "music_declaration": declared_music,
        "evidence_scope": scope,
        "strict_receipt_present": False,
        "strict_receipt_promotable": False,
        "promotion_status": "BLOCKED",
        "blocking_reasons": sorted(set(reasons + [
            "manifest/QA/delivery evidence is contextual only",
            "no replayable strict_mix_receipt supplied",
            "no independent SFX lineage evidence supplied",
        ])),
    }


def build_reconciliation_report(master_registry: Any, evidence: Any) -> dict[str, Any]:
    """Build a non-promoting Drive evidence reconciliation report."""
    registry = _registry_map(master_registry)
    artifacts = _evidence_map(evidence)
    rows = [_row(master, artifacts.get(episode_id)) for episode_id, master in registry.items()]
    return {
        "schema_version": "1.0",
        "gate": "AUDIO_HISTORY_DRIVE_EVIDENCE_RECONCILIATION",
        "status": "BLOCKED",
        "promotion_status": "BLOCKED",
        "master_count": len(rows),
        "contextual_evidence_count": sum(row["contextual_evidence_present"] for row in rows),
        "strict_receipt_count": 0,
        "rows": rows,
        "policy": (
            "Drive manifests, QA flags, delivery flags, narration fingerprints, "
            "and source declarations are contextual evidence only. They never "
            "promote a historical master or certify audible music/SFX use without "
            "a replayable strict V2.1 mix receipt."
        ),
        "next_required_evidence": [
            "per-master strict_mix_receipt",
            "mix_command_sha256",
            "mix_execution_log_sha256",
            "artifact_id",
            "music_sources",
            "sfx_sources",
            "sfx_usage_status",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-registry", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    report = build_reconciliation_report(
        _load_json(args.master_registry),
        _load_json(args.evidence),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
