"""Fail-closed, single-claim queue contract for the canonical copilot.

This module does not start the engine, call TTS, render media, or publish.
It only validates and transitions an isolated queue snapshot. Integration with
the canonical Runflow remains a separate, explicitly gated change.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


QUEUE_SCHEMA_VERSION = 1
ALLOWED_STATUSES = {"IDLE", "ENGINE_QUEUE", "ENGINE_RUNNING", "BLOCKED", "FAIL_CLOSED"}


class QueueContractError(RuntimeError):
    """Raised when a queue transition would violate the canonical contract."""


def initial_state(*, memory_revision: str, engine_policy_sha256: str) -> dict[str, Any]:
    if not memory_revision or not engine_policy_sha256:
        raise QueueContractError("memory revision and engine policy hash are required")
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "state_version": 0,
        "status": "IDLE",
        "active_run_id": None,
        "active_request_id": None,
        "queued_request_ids": [],
        "memory_revision": memory_revision,
        "engine_policy_sha256": engine_policy_sha256,
        "blocked_reason": None,
    }


def validate_state(state: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "state_version",
        "status",
        "active_run_id",
        "active_request_id",
        "queued_request_ids",
        "memory_revision",
        "engine_policy_sha256",
        "blocked_reason",
    }
    missing = sorted(required - set(state))
    if missing:
        raise QueueContractError(f"queue state is missing fields: {','.join(missing)}")
    if state["schema_version"] != QUEUE_SCHEMA_VERSION:
        raise QueueContractError("unsupported queue schema version")
    if not isinstance(state["state_version"], int) or state["state_version"] < 0:
        raise QueueContractError("state_version must be a non-negative integer")
    if state["status"] not in ALLOWED_STATUSES:
        raise QueueContractError("unknown queue status")
    queue = state["queued_request_ids"]
    if not isinstance(queue, list) or any(not isinstance(item, str) or not item for item in queue):
        raise QueueContractError("queued_request_ids must contain non-empty strings")
    if len(queue) != len(set(queue)):
        raise QueueContractError("duplicate request in queue")
    running = state["status"] == "ENGINE_RUNNING"
    if running != bool(state["active_run_id"] and state["active_request_id"]):
        raise QueueContractError("running state must have exactly one active run and request")
    if state["active_request_id"] in queue:
        raise QueueContractError("active request cannot remain queued")
    if state["status"] == "ENGINE_QUEUE" and state["active_run_id"]:
        raise QueueContractError("queue state cannot hold an active run")


def _assert_context(state: dict[str, Any], *, memory_revision: str, engine_policy_sha256: str) -> None:
    validate_state(state)
    if state["memory_revision"] != memory_revision:
        raise QueueContractError("canonical memory revision is stale")
    if state["engine_policy_sha256"] != engine_policy_sha256:
        raise QueueContractError("active engine policy hash is stale")
    if state["status"] in {"BLOCKED", "FAIL_CLOSED"}:
        raise QueueContractError(f"queue is fail-closed: {state['status']}")


def enqueue(
    state: dict[str, Any],
    request_id: str,
    *,
    memory_revision: str,
    engine_policy_sha256: str,
) -> dict[str, Any]:
    """Add a request once; never creates a second active run."""
    if not request_id:
        raise QueueContractError("request_id is required")
    _assert_context(state, memory_revision=memory_revision, engine_policy_sha256=engine_policy_sha256)
    if state["active_request_id"] == request_id or request_id in state["queued_request_ids"]:
        return state
    state["queued_request_ids"].append(request_id)
    state["status"] = "ENGINE_QUEUE"
    state["state_version"] += 1
    return state


def claim_next(
    state: dict[str, Any],
    run_id: str,
    *,
    memory_revision: str,
    engine_policy_sha256: str,
) -> dict[str, Any]:
    """Claim exactly one queued request for the canonical engine lane."""
    if not run_id:
        raise QueueContractError("run_id is required")
    _assert_context(state, memory_revision=memory_revision, engine_policy_sha256=engine_policy_sha256)
    if state["active_run_id"]:
        raise QueueContractError("another canonical engine run is already active")
    if not state["queued_request_ids"]:
        raise QueueContractError("no queued request is available")
    state["active_request_id"] = state["queued_request_ids"].pop(0)
    state["active_run_id"] = run_id
    state["status"] = "ENGINE_RUNNING"
    state["state_version"] += 1
    return state


def complete(
    state: dict[str, Any],
    run_id: str,
    *,
    memory_revision: str,
    engine_policy_sha256: str,
    success: bool,
) -> dict[str, Any]:
    """Release the active lane and preserve queued work."""
    _assert_context(state, memory_revision=memory_revision, engine_policy_sha256=engine_policy_sha256)
    if state["status"] != "ENGINE_RUNNING" or state["active_run_id"] != run_id:
        raise QueueContractError("run does not own the active canonical lane")
    state["active_run_id"] = None
    state["active_request_id"] = None
    state["status"] = "ENGINE_QUEUE" if state["queued_request_ids"] else "IDLE"
    state["blocked_reason"] = None if success else "engine run failed; review required"
    if not success:
        state["status"] = "FAIL_CLOSED"
    state["state_version"] += 1
    return state


def fail_closed(state: dict[str, Any], reason: str) -> dict[str, Any]:
    """Stop future claims without deleting queued requests or evidence."""
    validate_state(state)
    if not reason:
        raise QueueContractError("fail-closed reason is required")
    state["active_run_id"] = None
    state["active_request_id"] = None
    state["status"] = "FAIL_CLOSED"
    state["blocked_reason"] = reason
    state["state_version"] += 1
    return state


def read_state(path: Path) -> dict[str, Any]:
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise QueueContractError("queue state must be a JSON object")
    validate_state(state)
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically persist the isolated queue snapshot."""
    validate_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

