"""Sequential, isolated adapters for the six Copilot analysis agents.

The adapters define the execution contract only. They do not call a model,
start the canonical engine, write project memory, render media, or publish.
A caller must inject an external executor and receives immutable envelopes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Iterable


ALLOWED_STATUSES = {"PASS", "EDIT", "BLOCKED", "FAIL"}
REQUIRED_FIELDS = {
    "agent_id",
    "input_revision",
    "source_artifacts",
    "evidence",
    "status",
    "blocking_reasons",
    "output_artifact",
    "output_sha256",
    "next_gate",
    "token_budget_used",
}
AGENT_ORDER = (
    "research_analyst",
    "factual_reviewer",
    "story_editorial_agent",
    "rights_provenance_agent",
    "visual_continuity_agent",
    "timeline_caption_agent",
)
AGENT_ARTIFACTS = {
    "research_analyst": ("research_card", "sources"),
    "factual_reviewer": ("factual_receipt", "factuality"),
    "story_editorial_agent": ("script_candidate", "editorial"),
    "rights_provenance_agent": ("rights_ledger", "rights"),
    "visual_continuity_agent": ("visual_map", "continuity"),
    "timeline_caption_agent": ("timeline_preflight", "timeline"),
}
TOKEN_BUDGETS = {
    "research_analyst": 1400,
    "factual_reviewer": 1200,
    "story_editorial_agent": 1400,
    "rights_provenance_agent": 1100,
    "visual_continuity_agent": 1100,
    "timeline_caption_agent": 1200,
}


class AnalysisContractError(ValueError):
    """Raised when an analysis task or result violates the contract."""


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    order: int
    artifact: str
    approval_domain: str
    token_budget: int


AGENT_SPECS = tuple(
    AgentSpec(agent_id, index, AGENT_ARTIFACTS[agent_id][0], AGENT_ARTIFACTS[agent_id][1], TOKEN_BUDGETS[agent_id])
    for index, agent_id in enumerate(AGENT_ORDER, start=1)
)


def agent_spec(agent_id: str) -> AgentSpec:
    for spec in AGENT_SPECS:
        if spec.agent_id == agent_id:
            return spec
    raise AnalysisContractError(f"unknown analysis agent: {agent_id}")


def build_task(
    agent_id: str,
    *,
    input_revision: str,
    source_artifacts: Iterable[str],
    evidence: Iterable[str],
) -> dict[str, Any]:
    spec = agent_spec(agent_id)
    if not input_revision:
        raise AnalysisContractError("input_revision is required")
    return {
        "agent_id": spec.agent_id,
        "order": spec.order,
        "approval_domain": spec.approval_domain,
        "input_revision": input_revision,
        "source_artifacts": list(source_artifacts),
        "evidence": list(evidence),
        "expected_artifact": spec.artifact,
        "token_budget": spec.token_budget,
        "can_start_engine": False,
        "parallel": False,
    }


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _non_empty_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AnalysisContractError(f"{field} must be a list of non-empty strings")
    return value


def validate_result(
    result: dict[str, Any],
    *,
    expected_agent_id: str | None = None,
    expected_input_revision: str | None = None,
    expected_source_artifacts: Iterable[str] | None = None,
    expected_evidence: Iterable[str] | None = None,
) -> None:
    if not isinstance(result, dict):
        raise AnalysisContractError("agent result must be an object")
    missing = sorted(REQUIRED_FIELDS - set(result))
    if missing:
        raise AnalysisContractError(f"agent result is missing fields: {','.join(missing)}")
    agent_id = result["agent_id"]
    spec = agent_spec(agent_id)
    if expected_agent_id is not None and agent_id != expected_agent_id:
        raise AnalysisContractError("agent result does not match the dispatched task")
    if expected_input_revision is not None and result.get("input_revision") != expected_input_revision:
        raise AnalysisContractError("agent result input revision does not match the dispatched task")
    if not isinstance(result.get("input_revision"), str) or not result["input_revision"].strip():
        raise AnalysisContractError("agent result input_revision is required")
    source_artifacts = _non_empty_string_list(result["source_artifacts"], "source_artifacts")
    evidence = _non_empty_string_list(result["evidence"], "evidence")
    if expected_source_artifacts is not None and source_artifacts != list(expected_source_artifacts):
        raise AnalysisContractError("agent result source_artifacts drifted from the dispatched task")
    if expected_evidence is not None:
        expected_items = list(expected_evidence)
        if any(item not in evidence for item in expected_items):
            raise AnalysisContractError("agent result dropped dispatched evidence")
    if result["status"] not in ALLOWED_STATUSES:
        raise AnalysisContractError("unknown agent status")
    if result.get("approval_domain") not in (None, spec.approval_domain):
        raise AnalysisContractError("agent cannot approve another domain")
    if result.get("can_start_engine") is not False or result.get("engine_action"):
        raise AnalysisContractError("analysis agent cannot start or control the engine")
    blocking_reasons = result["blocking_reasons"]
    if not isinstance(blocking_reasons, list) or any(not isinstance(reason, str) or not reason.strip() for reason in blocking_reasons):
        raise AnalysisContractError("blocking_reasons must be a list of non-empty strings")
    if result["status"] == "PASS" and blocking_reasons:
        raise AnalysisContractError("PASS result cannot contain blocking reasons")
    if result["status"] != "PASS" and not blocking_reasons:
        raise AnalysisContractError("non-PASS result must include blocking reasons")
    if not isinstance(result["next_gate"], str) or not result["next_gate"].strip():
        raise AnalysisContractError("next_gate is required")
    token_budget_used = result["token_budget_used"]
    if isinstance(token_budget_used, bool) or not isinstance(token_budget_used, int) or token_budget_used < 0:
        raise AnalysisContractError("token_budget_used must be a non-negative integer")
    if token_budget_used > spec.token_budget:
        raise AnalysisContractError("agent exceeded its token budget")
    artifact = result["output_artifact"]
    try:
        expected_hash = _canonical_hash(artifact)
    except (TypeError, ValueError) as exc:
        raise AnalysisContractError("output_artifact must be JSON-serializable") from exc
    if result["output_sha256"] != expected_hash:
        raise AnalysisContractError("output artifact hash mismatch")
    if result["status"] == "PASS" and result["next_gate"] not in {spec.approval_domain, "technical_gate"}:
        raise AnalysisContractError("PASS result points to an invalid next gate")


def dispatch_sequential(
    tasks: Iterable[dict[str, Any]],
    executor: Callable[[dict[str, Any]], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run injected analysis providers strictly in declared order.

    A non-PASS result stops the lane. No provider is called in parallel and no
    provider can activate production through this adapter.
    """
    task_list = list(tasks)
    expected_ids = list(AGENT_ORDER)
    if [task.get("agent_id") for task in task_list] != expected_ids:
        raise AnalysisContractError("analysis tasks must contain all six agents in canonical order")
    results: list[dict[str, Any]] = []
    for task in task_list:
        spec = agent_spec(task["agent_id"])
        if task.get("parallel") is not False or task.get("can_start_engine") is not False:
            raise AnalysisContractError("analysis task violates sequential production-disabled policy")
        result = executor(task)
        validate_result(
            result,
            expected_agent_id=spec.agent_id,
            expected_input_revision=task["input_revision"],
            expected_source_artifacts=task["source_artifacts"],
            expected_evidence=task["evidence"],
        )
        results.append(result)
        if result["status"] != "PASS":
            break
    return results
