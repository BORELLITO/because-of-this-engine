"""Fail-closed, persistent production states for the V2.1 canonical path."""
from __future__ import annotations
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATES = ("DRAFT", "PACKAGE_PENDING", "FACT_CHECK_PENDING", "STORY_PENDING", "ASSETS_PENDING", "RIGHTS_PENDING", "REUSE_PENDING", "VOICE_PENDING", "AUDIO_PENDING", "CAPTIONS_PENDING", "PREVIEW_PENDING", "THUMBNAIL_PENDING", "THUMBNAIL_QA", "HUMAN_REVIEW", "TECHNICAL_QA", "NEEDS_CORRECTION", "BLOCKED", "APPROVED_FOR_MANUAL_PUBLICATION", "MANUALLY_PUBLISHED", "METRICS_PENDING", "ARCHIVED")
TRANSITIONS = {
    "DRAFT": {"PACKAGE_PENDING", "BLOCKED"},
    "PACKAGE_PENDING": {"FACT_CHECK_PENDING", "BLOCKED"},
    "FACT_CHECK_PENDING": {"STORY_PENDING", "BLOCKED"},
    "STORY_PENDING": {"ASSETS_PENDING", "BLOCKED"},
    "ASSETS_PENDING": {"RIGHTS_PENDING", "BLOCKED"},
    "RIGHTS_PENDING": {"REUSE_PENDING", "BLOCKED"},
    "REUSE_PENDING": {"VOICE_PENDING", "BLOCKED"},
    "VOICE_PENDING": {"AUDIO_PENDING", "BLOCKED"},
    "AUDIO_PENDING": {"CAPTIONS_PENDING", "BLOCKED"},
    "CAPTIONS_PENDING": {"PREVIEW_PENDING", "BLOCKED"},
    "PREVIEW_PENDING": {"THUMBNAIL_PENDING", "BLOCKED"},
    "THUMBNAIL_PENDING": {"THUMBNAIL_QA", "BLOCKED"},
    "THUMBNAIL_QA": {"HUMAN_REVIEW", "NEEDS_CORRECTION", "BLOCKED"},
    "HUMAN_REVIEW": {"TECHNICAL_QA", "NEEDS_CORRECTION", "BLOCKED"},
    "TECHNICAL_QA": {"APPROVED_FOR_MANUAL_PUBLICATION", "NEEDS_CORRECTION", "BLOCKED"},
    "APPROVED_FOR_MANUAL_PUBLICATION": {"MANUALLY_PUBLISHED", "ARCHIVED", "BLOCKED"},
    "MANUALLY_PUBLISHED": {"METRICS_PENDING", "ARCHIVED"},
    "METRICS_PENDING": {"ARCHIVED"},
    "NEEDS_CORRECTION": {"PACKAGE_PENDING", "FACT_CHECK_PENDING", "STORY_PENDING", "ASSETS_PENDING", "RIGHTS_PENDING", "REUSE_PENDING", "VOICE_PENDING", "AUDIO_PENDING", "CAPTIONS_PENDING", "PREVIEW_PENDING", "THUMBNAIL_PENDING", "BLOCKED"},
    "BLOCKED": {"PACKAGE_PENDING", "ARCHIVED"},
    "ARCHIVED": set(),
}

class StateTransitionError(ValueError):
    pass

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def assert_transition(current: str, target: str) -> None:
    if current not in STATES or target not in STATES:
        raise StateTransitionError(f"unknown state: {current}->{target}")
    if target not in TRANSITIONS[current]:
        raise StateTransitionError(f"invalid transition: {current}->{target}")

def _validate_evidence(target: str, evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if target in {"BLOCKED", "NEEDS_CORRECTION"}:
        return dict(evidence or {})
    if not isinstance(evidence, Mapping):
        raise StateTransitionError("evidence is required for every non-blocking transition")
    required = ("gate", "status", "evidence_id")
    missing = [field for field in required if not evidence.get(field)]
    if missing:
        raise StateTransitionError("transition evidence missing:" + ",".join(missing))
    if evidence.get("status") not in {"PASS", "APPROVED", "VERIFIED"}:
        raise StateTransitionError("non-blocking transition evidence must be PASS, APPROVED or VERIFIED")
    return dict(evidence)

def advance(current: str, target: str, *, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    assert_transition(current, target)
    return {"previous_state": current, "state": target, "evidence": _validate_evidence(target, evidence)}

def new_state_record(*, episode_id: str, implementation_id: str) -> dict[str, Any]:
    return {"schema_version": "3.1.0", "episode_id": episode_id, "implementation_id": implementation_id, "state": "DRAFT", "pipeline_state": "DRAFT", "history": [], "production_enablement": False, "created_at": _now(), "updated_at": _now()}

def _state_path(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent / ".engine" / "production-record-3.1.0.state.json"

def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

def load_or_initialize(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("editorial_mode") != "factual_documentary" or "pipeline_state" not in manifest:
        raise StateTransitionError("V2.1 state requires a factual production record with pipeline_state")
    path = _state_path(manifest_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    record = new_state_record(episode_id=str(manifest.get("episode_id")), implementation_id=str(manifest.get("implementation_id")))
    _atomic_write(path, record)
    return record

def transition_manifest(manifest_path: Path, target: str, *, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    record = load_or_initialize(manifest_path)
    result = advance(str(record["state"]), target, evidence=evidence)
    record["state"] = result["state"]
    record["pipeline_state"] = result["state"]
    record.setdefault("history", []).append({"at": _now(), **result})
    record["updated_at"] = _now()
    _atomic_write(_state_path(manifest_path), record)
    return record
