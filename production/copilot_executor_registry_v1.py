"""Specialized executor registry for the canonical Copilot analysis lane.

This layer connects the six analysis adapters to real providers supplied by the
caller. It never creates a provider, opens a network connection, starts the
canonical engine, renders media, calls TTS, writes memory, or publishes.
Missing providers fail closed with an explicit BLOCKED receipt.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from production.copilot_analysis_agents_v1 import (
    AGENT_ORDER,
    AnalysisContractError,
    build_task,
    dispatch_sequential,
)


Executor = Callable[[dict[str, Any]], dict[str, Any]]


SPECIALIZED_ROLE_PROMPTS: dict[str, str] = {
    "research_analyst": "Find primary sources and candidate clip references; return only claims backed by cited evidence.",
    "factual_reviewer": "Check dates, names, numbers, quotations, and causal claims against the supplied evidence.",
    "story_editorial_agent": "Shape a concise hook, narrative progression, and payoff without adding unsupported claims.",
    "rights_provenance_agent": "Reconcile source URLs, license evidence, attribution, hashes, and reuse constraints.",
    "visual_continuity_agent": "Map each visual beat to the approved narrative, era, location, lighting, and motion continuity.",
    "timeline_caption_agent": "Validate duration, word timestamps, karaoke timing, safe-zone placement, and caption readability.",
}


def _artifact_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_specialized_tasks(
    *,
    input_revision: str,
    source_artifacts: Iterable[str],
    evidence: Iterable[str],
) -> list[dict[str, Any]]:
    """Build the canonical six-task lane with role-specific instructions."""
    tasks: list[dict[str, Any]] = []
    for agent_id in AGENT_ORDER:
        task = build_task(
            agent_id,
            input_revision=input_revision,
            source_artifacts=source_artifacts,
            evidence=evidence,
        )
        task.update(
            {
                "executor_role": agent_id,
                "role_prompt": SPECIALIZED_ROLE_PROMPTS[agent_id],
                "context_policy": "MINIMAL_REFERENCES_ONLY",
                "network_allowed": False,
            }
        )
        tasks.append(task)
    return tasks


def registry_status(executors: Mapping[str, Executor]) -> dict[str, Any]:
    """Return a non-sensitive readiness report for the six required roles."""
    configured = sorted(agent_id for agent_id in AGENT_ORDER if callable(executors.get(agent_id)))
    missing = [agent_id for agent_id in AGENT_ORDER if agent_id not in configured]
    return {
        "status": "READY" if not missing else "BLOCKED",
        "configured": configured,
        "missing": missing,
        "parallel": False,
        "can_start_engine": False,
        "network_started": False,
    }


def _blocked_result(task: dict[str, Any], reason: str) -> dict[str, Any]:
    artifact = {
        "agent": task["agent_id"],
        "status": "BLOCKED",
        "reason": reason,
        "executor": "unconfigured",
    }
    return {
        "agent_id": task["agent_id"],
        "input_revision": task["input_revision"],
        "source_artifacts": task["source_artifacts"],
        "evidence": task["evidence"],
        "status": "BLOCKED",
        "blocking_reasons": [reason],
        "output_artifact": artifact,
        "output_sha256": _artifact_hash(artifact),
        "next_gate": "executor_configuration",
        "token_budget_used": 0,
        "approval_domain": task["approval_domain"],
        "can_start_engine": False,
    }


def dispatch_registered(
    tasks: Iterable[dict[str, Any]],
    executors: Mapping[str, Executor],
) -> list[dict[str, Any]]:
    """Dispatch registered providers strictly in order and fail closed.

    The existing adapter remains the single sequencing authority. A provider
    is invoked only for its current role; a missing role returns a BLOCKED
    receipt and stops the lane. Provider output is validated by the adapter.
    """
    status = registry_status(executors)
    task_list = list(tasks)
    if [task.get("agent_id") for task in task_list] != list(AGENT_ORDER):
        raise AnalysisContractError("registered analysis tasks must use canonical order")

    def invoke(task: dict[str, Any]) -> dict[str, Any]:
        provider = executors.get(task["agent_id"])
        if not callable(provider):
            return _blocked_result(task, f"executor is not configured: {task['agent_id']}")
        return provider(task)

    results = dispatch_sequential(task_list, invoke)
    if status["status"] == "BLOCKED" and results and results[-1]["status"] == "PASS":
        raise AnalysisContractError("registry reported missing executors but lane passed")
    return results
