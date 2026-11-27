"""Read-only bridge from the Copilot queue to the canonical Runflow.

The bridge verifies that a queued request has the current memory/policy
context, a passing crosswalk and eight passing canonical analysis receipts.
It returns a preparation handoff only. It never claims the queue, dispatches a
workflow, starts the engine, renders media, calls TTS or publishes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from production.brazil_files_canonical_crosswalk_v1 import (
    CANONICAL_AGENT_IDS,
    EXECUTION_MODE,
    validate_crosswalk,
)
from production.copilot_analysis_agents_v1 import AGENT_ORDER
from production.copilot_queue_v1 import QueueContractError, validate_state


HANDOFF_STATUS = "READY_FOR_RUNFLOW_PREPARATION_GATE"
DISPATCH_MODE = "MANUAL_OR_SEPARATE_AUTHORIZED_WORKFLOW"
PRODUCTION_STARTED = False
CAN_START_ENGINE = False
PARALLEL = False


def _receipt_failures(results: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(results) != len(AGENT_ORDER):
        errors.append(f"exactly {len(AGENT_ORDER)} canonical receipts are required")
    agent_ids = [result.get("agent_id") for result in results]
    if agent_ids != list(AGENT_ORDER):
        errors.append("canonical receipts must follow the eight-agent order")
    for result in results:
        agent_id = result.get("agent_id")
        if result.get("status") != "PASS":
            errors.append(f"{agent_id or 'unknown'} receipt is not PASS")
        if result.get("can_start_engine") is not False:
            errors.append(f"{agent_id or 'unknown'} may not start the engine")
        if not isinstance(result.get("output_sha256"), str) or not result["output_sha256"].strip():
            errors.append(f"{agent_id or 'unknown'} output hash is missing")
    return errors


def validate_runflow_handoff(
    queue_state: Mapping[str, Any],
    analysis_results: Sequence[Mapping[str, Any]],
    *,
    memory_revision: str,
    engine_policy_sha256: str,
    crosswalk_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed handoff report without dispatching Runflow."""

    errors: list[str] = []
    try:
        validate_state(dict(queue_state))
    except (QueueContractError, TypeError) as exc:
        errors.append(f"queue state invalid: {exc}")
    else:
        if queue_state.get("status") != "ENGINE_QUEUE":
            errors.append("queue must be ENGINE_QUEUE before Runflow preparation")
        if queue_state.get("active_run_id") or queue_state.get("active_request_id"):
            errors.append("Runflow handoff cannot contain an active run")
        if queue_state.get("memory_revision") != memory_revision:
            errors.append("canonical memory revision is stale")
        if queue_state.get("engine_policy_sha256") != engine_policy_sha256:
            errors.append("active engine policy hash is stale")

    errors.extend(_receipt_failures(analysis_results))

    crosswalk = crosswalk_report or validate_crosswalk()
    if crosswalk.get("status") != "PASS":
        errors.extend(f"crosswalk:{error}" for error in crosswalk.get("errors", ["crosswalk is blocked"]))
    if crosswalk.get("execution_mode") != EXECUTION_MODE:
        errors.append("crosswalk execution mode drifted")
    if crosswalk.get("parallel_allowed") is not False:
        errors.append("crosswalk parallelism must remain disabled")
    if crosswalk.get("secondary_engine_allowed") is not False:
        errors.append("crosswalk secondary engine must remain disabled")

    status = HANDOFF_STATUS if not errors else "RUNFLOW_HANDOFF_BLOCKED"
    return {
        "status": status,
        "queue_state_version": queue_state.get("state_version"),
        "request_id": queue_state.get("active_request_id") or (queue_state.get("queued_request_ids") or [None])[0],
        "canonical_agent_ids": list(CANONICAL_AGENT_IDS),
        "receipt_count": len(analysis_results),
        "dispatch_mode": DISPATCH_MODE,
        "production_started": PRODUCTION_STARTED,
        "can_start_engine": CAN_START_ENGINE,
        "parallel": PARALLEL,
        "errors": errors,
    }


def build_runflow_handoff(
    queue_state: Mapping[str, Any],
    analysis_results: Sequence[Mapping[str, Any]],
    *,
    memory_revision: str,
    engine_policy_sha256: str,
) -> dict[str, Any]:
    """Build the standard handoff report used by tests and future adapters."""

    return validate_runflow_handoff(
        queue_state,
        analysis_results,
        memory_revision=memory_revision,
        engine_policy_sha256=engine_policy_sha256,
    )


if __name__ == "__main__":
    import json

    print(json.dumps({
        "status": "READ_ONLY_RUNFLOW_HANDOFF_ADAPTER",
        "production_started": PRODUCTION_STARTED,
        "can_start_engine": CAN_START_ENGINE,
        "parallel": PARALLEL,
    }, ensure_ascii=False, indent=2))
