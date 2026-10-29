#!/usr/bin/env python3
"""Structured V7.1 production record, gate and lifecycle contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "3.0.0"
SCHEMA_ID = "because-of-this://schemas/production-record/3.0.0"
PROMPT_VERSION = "7.1"
GATE_ORDER = tuple(f"G{i}" for i in range(12))
GATE_NAMES = {
    "G0": "preflight",
    "G1": "story",
    "G2": "rights_originality_fiction",
    "G3": "visual_fidelity",
    "G4": "edge_tts_narration",
    "G5": "audio_mix",
    "G6": "captions_sync",
    "G7": "packaging",
    "G8": "preview",
    "G9": "render_technical",
    "G10": "human_approval",
    "G11": "post_publication",
}
GATE_STATES = {"pending", "running", "passed", "failed", "blocked", "overridden_creative"}
PRODUCTION_STATES = {
    "draft", "preflight", "in_production", "pending_validation", "human_review",
    "approved_for_publication", "manually_published", "blocked", "canceled",
    "rollback_required", "safe_mode",
}
COMPONENT_STATES = {
    "draft", "generated", "pending_validation", "approved", "needs_correction",
    "rejected", "reserved", "consumed", "archived", "corrupted", "legally_removed",
}
VERSION_STATES = {"candidate", "active", "stable", "rollback_eligible", "unstable", "archived"}


class ProductionRecordError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def idempotency_key(production_id: str, engine_version: str, component: str, config_hash: str, input_hash: str) -> str:
    payload = "|".join((production_id, engine_version, component, config_hash, input_hash)).encode("utf-8")
    return sha256_bytes(payload)


def _gate(gate_id: str, state: str = "pending", evidence: str = "awaiting execution") -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": GATE_NAMES[gate_id],
        "rule_version": PROMPT_VERSION,
        "state": state,
        "severity": "informational" if state == "pending" else "critical_blocking",
        "score": None,
        "evidence": evidence,
        "artifacts": [],
        "attempt_id": None,
        "corrections": [],
        "probable_cause": None,
        "next_action": "execute_gate",
        "started_at": None,
        "finished_at": None,
        "human_decision": None,
    }


def new_record(manifest: dict[str, Any], *, engine_bundle_id: str, engine_version: str = "7.1") -> dict[str, Any]:
    production_id = str(manifest.get("production_id") or manifest.get("video_id") or "").strip()
    story_id = str(manifest.get("story_id") or manifest.get("episode_id") or production_id).strip()
    if not production_id or not story_id:
        raise ProductionRecordError("manifest requires production_id/video_id and story_id/episode_id")
    scenes = manifest.get("scenes") if isinstance(manifest.get("scenes"), list) else []
    beats = manifest.get("visual_beats") if isinstance(manifest.get("visual_beats"), list) else []
    if not beats and isinstance(manifest.get("story"), dict):
        story_beats = manifest["story"].get("beats")
        if isinstance(story_beats, list):
            beats = story_beats
    if not beats and isinstance(manifest.get("beats"), list):
        beats = manifest["beats"]
    gates = {gate_id: _gate(gate_id) for gate_id in GATE_ORDER}
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_id": SCHEMA_ID,
        "record_id": f"record-{production_id}-{engine_version}",
        "project": {"project_id": "because-of-this", "name": "Because Of This", "language": "en-US"},
        "engine_bundle": {"engine_bundle_id": engine_bundle_id, "version": engine_version, "state": "candidate"},
        "production": {
            "production_id": production_id,
            "production_version": str(manifest.get("version") or "1.0.0"),
            "state": "draft",
            "created_at": now(),
            "updated_at": now(),
        },
        "story": {"story_id": story_id, "title": manifest.get("title", ""), "state": "draft"},
        "story_graph": manifest.get("story_graph") or {"version": "pending", "entities": [], "beats": []},
        "emotional_map": manifest.get("emotional_map") or {"beats": [], "status": "pending"},
        "reveal_map": manifest.get("reveal_map") or {"known": [], "hidden": [], "status": "pending"},
        "scenes": scenes,
        "visual_beats": beats,
        "narration": manifest.get("narration") or {"state": "draft", "provider": "microsoft_edge_tts"},
        "tts_request_records": [],
        "audio_assets": [],
        "captions": manifest.get("captions") or {"state": "draft"},
        "packaging": manifest.get("packaging") or {"state": "draft"},
        "preview": {"state": "draft", "hash": None},
        "render": {"state": "draft", "hash": None},
        "gates": gates,
        "incidents": [],
        "retries": [],
        "checkpoints": [],
        "artifacts": [],
        "rights_records": [],
        "asset_reservations": [],
        "drive_sync": {"state": "pending", "attempts": 0, "files": []},
        "human_decisions": [],
        "metrics_reference": {"state": "pending", "confidence": "none"},
        "ids": {
            "project_id": "because-of-this",
            "story_id": story_id,
            "engine_bundle_id": engine_bundle_id,
            "production_id": production_id,
            "scene_ids": [str(scene.get("scene_id")) for scene in scenes if isinstance(scene, dict) and scene.get("scene_id")],
            "beat_ids": [
                str(beat.get("beat_id") or beat.get("scene_id"))
                for beat in beats
                if isinstance(beat, dict) and (beat.get("beat_id") or beat.get("scene_id"))
            ],
        },
        "hashes": {},
        "next_action": "G0_PREFLIGHT",
    }


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ProductionRecordError("production record must be an object")
    required = (
        "schema_version", "schema_id", "project", "engine_bundle", "production", "story", "story_graph",
        "emotional_map", "reveal_map", "scenes", "visual_beats", "narration",
        "tts_request_records", "audio_assets", "captions", "packaging", "preview", "render",
        "gates", "incidents", "retries", "checkpoints", "artifacts", "rights_records",
        "asset_reservations", "drive_sync", "human_decisions", "metrics_reference", "next_action",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise ProductionRecordError(f"missing production record fields: {missing}")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("schema_id") != SCHEMA_ID:
        raise ProductionRecordError("production record is not schema 3.0.0")
    state = (record.get("production") or {}).get("state")
    if state not in PRODUCTION_STATES:
        raise ProductionRecordError(f"invalid production state: {state!r}")
    gates = record.get("gates")
    if not isinstance(gates, dict) or tuple(gates.keys()) != GATE_ORDER:
        raise ProductionRecordError("gates must contain G0 through G11 in canonical order")
    for gate_id in GATE_ORDER:
        value = gates[gate_id]
        if not isinstance(value, dict) or value.get("name") != GATE_NAMES[gate_id]:
            raise ProductionRecordError(f"{gate_id} has an invalid canonical name")
        if value.get("state") not in GATE_STATES:
            raise ProductionRecordError(f"{gate_id} has an invalid state")
        if not isinstance(value.get("evidence"), str) or not value["evidence"].strip():
            raise ProductionRecordError(f"{gate_id} must contain evidence")
    if state in {"approved_for_publication", "manually_published"}:
        if any(gates[f"G{i}"].get("state") != "passed" for i in range(11)):
            raise ProductionRecordError("publication-ready records require G0 through G10 to be passed")
    if state == "manually_published" and gates["G11"].get("state") != "passed":
        raise ProductionRecordError("manually_published records require G11 to be passed")
    for artifact in record.get("artifacts", []):
        if not isinstance(artifact, dict):
            raise ProductionRecordError("artifact records must be objects")
        for key in ("artifact_id", "kind", "sha256", "origin"):
            if not isinstance(artifact.get(key), str) or not artifact[key].strip():
                raise ProductionRecordError(f"artifact is missing {key}")
        if len(artifact["sha256"]) != 64:
            raise ProductionRecordError("artifact sha256 must be a 64-character digest")
    return {"status": "PRODUCTION_RECORD_V7_PASS", "schema_id": SCHEMA_ID, "gate_order": list(GATE_ORDER)}


def transition(record: dict[str, Any], new_state: str, *, evidence: str) -> dict[str, Any]:
    if new_state not in PRODUCTION_STATES:
        raise ProductionRecordError(f"invalid production state: {new_state}")
    current = (record.get("production") or {}).get("state")
    allowed = {
        "draft": {"preflight", "blocked", "canceled"},
        "preflight": {"in_production", "blocked", "safe_mode"},
        "in_production": {"pending_validation", "blocked", "rollback_required"},
        "pending_validation": {"human_review", "blocked", "rollback_required"},
        "human_review": {"approved_for_publication", "blocked", "canceled"},
        "approved_for_publication": {"manually_published", "blocked"},
        "manually_published": {"manually_published"},
        "blocked": {"preflight", "safe_mode", "rollback_required", "canceled"},
        "rollback_required": {"safe_mode", "preflight"},
        "safe_mode": {"preflight", "canceled"},
        "canceled": set(),
    }
    if current not in allowed or new_state not in allowed[current]:
        raise ProductionRecordError(f"invalid transition {current!r} -> {new_state!r}")
    record["production"]["state"] = new_state
    record["production"]["updated_at"] = now()
    record["next_action"] = evidence
    return record


def write_record(path: Path, record: dict[str, Any]) -> None:
    validate_record(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)

