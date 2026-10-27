#!/usr/bin/env python3
"""Small, durable state machine for one Because of This v2 production job."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.canonical_config import (
    CANONICAL_PROFILE_FINGERPRINT,
    CANONICAL_PROFILE_ID,
    CanonicalConfigError,
    validate_canonical_manifest,
)

STATES = (
    "CREATED",
    "RESEARCHED",
    "SCRIPT_APPROVED",
    "VOICE_READY",
    "VISUAL_PLAN_READY",
    "ASSETS_APPROVED",
    "TIMELINE_READY",
    "RENDERED",
    "QA_PASSED",
    "DELIVERED",
    "DELIVERY_VERIFIED",
    "CLEANED",
    "COMPLETE",
    "BLOCKED_AUTH",
    "BLOCKED_DRIVE_PREFLIGHT",
    "BLOCKED_ASSET",
    "FAILED_RENDER",
    "FAILED_QA",
    "FAILED_DELIVERY",
    "QUARANTINED",
)
TERMINAL = {"COMPLETE", "QUARANTINED"}
TRANSITIONS = {
    "CREATED": {"RESEARCHED", "SCRIPT_APPROVED", "VOICE_READY", "VISUAL_PLAN_READY", "ASSETS_APPROVED", "BLOCKED_AUTH", "BLOCKED_DRIVE_PREFLIGHT", "BLOCKED_ASSET", "QUARANTINED"},
    "RESEARCHED": {"SCRIPT_APPROVED", "BLOCKED_ASSET", "QUARANTINED"},
    "SCRIPT_APPROVED": {"VOICE_READY", "BLOCKED_ASSET", "QUARANTINED"},
    "VOICE_READY": {"VISUAL_PLAN_READY", "BLOCKED_ASSET", "QUARANTINED"},
    "VISUAL_PLAN_READY": {"ASSETS_APPROVED", "BLOCKED_ASSET", "QUARANTINED"},
    "ASSETS_APPROVED": {"TIMELINE_READY", "FAILED_RENDER", "BLOCKED_ASSET", "QUARANTINED"},
    "TIMELINE_READY": {"RENDERED", "FAILED_RENDER", "QUARANTINED"},
    "RENDERED": {"QA_PASSED", "FAILED_QA", "QUARANTINED"},
    "QA_PASSED": {"DELIVERED", "FAILED_DELIVERY", "QUARANTINED"},
    "DELIVERED": {"DELIVERY_VERIFIED", "FAILED_DELIVERY", "QUARANTINED"},
    "DELIVERY_VERIFIED": {"CLEANED", "FAILED_DELIVERY", "QUARANTINED"},
    "CLEANED": {"COMPLETE", "QUARANTINED"},
}
SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,119}$")


class PipelineStateError(RuntimeError):
    """Raised when a job state would become ambiguous or unsafe."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def job_id_from_manifest(manifest: dict[str, Any]) -> str:
    explicit = manifest.get("job_id")
    if not explicit and isinstance(manifest.get("job"), dict):
        explicit = manifest["job"].get("job_id")
    if explicit:
        value = str(explicit).strip()
        if not SAFE_JOB_ID.fullmatch(value):
            raise PipelineStateError("job_id must contain only letters, numbers, dot, underscore or hyphen.")
        return value
    video_id = str(manifest.get("video_id", "")).strip()
    if not video_id or not SAFE_JOB_ID.fullmatch(video_id):
        raise PipelineStateError("video_id is required to derive a safe job_id.")
    return f"{video_id}-{canonical_hash(manifest)[:12]}"


def state_path(manifest_path: Path, job_id: str) -> Path:
    if not SAFE_JOB_ID.fullmatch(job_id):
        raise PipelineStateError("Unsafe job_id cannot be used for state storage.")
    root = manifest_path.resolve().parent / ".engine" / "jobs"
    return root / f"{job_id}.state.json"


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_or_initialize(manifest_path: Path, *, enforce_canonical: bool = False) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical_report = None
    if enforce_canonical:
        try:
            canonical_report = validate_canonical_manifest(manifest, source_label=str(manifest_path))
        except CanonicalConfigError as exc:
            raise PipelineStateError(str(exc)) from exc
    job_id = job_id_from_manifest(manifest)
    path = state_path(manifest_path, job_id)
    manifest_sha = sha256_file(manifest_path)
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("job_id") != job_id or state.get("manifest_sha256") != manifest_sha:
            raise PipelineStateError("Existing job state does not belong to this manifest fingerprint.")
        if enforce_canonical and (
            state.get("engine_profile") != CANONICAL_PROFILE_ID
            or state.get("config_fingerprint") != CANONICAL_PROFILE_FINGERPRINT
        ):
            raise PipelineStateError("Existing job state does not carry the locked canonical engine profile.")
        return state
    state = {
        "job_id": job_id,
        "video_id": manifest.get("video_id"),
        "engine_version": "2.0",
        "engine_profile": (
            canonical_report.get("profile_id")
            if canonical_report
            else manifest.get("engine_profile")
        ),
        "config_fingerprint": (
            canonical_report.get("profile_fingerprint")
            if canonical_report
            else None
        ),
        "schema_version": manifest.get("schema_version"),
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "state": "CREATED",
        "stages": {},
        "created_at": now(),
        "updated_at": now(),
    }
    _atomic_write(path, state)
    return state


def transition(manifest_path: Path, target: str, stage: str, details: dict[str, Any] | None = None, *, enforce_canonical: bool = False) -> dict[str, Any]:
    if target not in STATES:
        raise PipelineStateError(f"Unknown pipeline state: {target}")
    state = load_or_initialize(manifest_path, enforce_canonical=enforce_canonical)
    current = state["state"]
    if current in TERMINAL:
        if current == target:
            return state
        raise PipelineStateError(f"Job {state['job_id']} is already terminal at {current}.")
    if target != current and target not in TRANSITIONS.get(current, set()):
        raise PipelineStateError(f"Invalid transition {current} -> {target}.")
    state["state"] = target
    state["updated_at"] = now()
    state.setdefault("stages", {})[stage] = {
        "state": target,
        "completed_at": state["updated_at"],
        "details": details or {},
    }
    _atomic_write(state_path(manifest_path.resolve(), state["job_id"]), state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize or advance the v2 production state machine.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--transition", choices=STATES)
    parser.add_argument("--stage", default="pipeline")
    parser.add_argument("--allow-noncanonical", action="store_true", help="Only for isolated local fixtures; production CLI remains locked.")
    args = parser.parse_args()
    try:
        if args.initialize:
            state = load_or_initialize(args.manifest, enforce_canonical=not args.allow_noncanonical)
        elif args.transition:
            state = transition(args.manifest, args.transition, args.stage, enforce_canonical=not args.allow_noncanonical)
        else:
            parser.error("Choose --initialize or --transition.")
        print(json.dumps({"status": "PIPELINE_STATE_OK", **state}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, PipelineStateError) as exc:
        print(f"PIPELINE STATE BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
