"""Fail-closed readiness manifest for injected Copilot providers.

This module validates provider metadata before any executor is called. It does
not create providers, open network connections, spend money, start the engine,
or execute media work.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from production.copilot_analysis_agents_v1 import AGENT_ORDER, AnalysisContractError


ProviderExecutor = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ProviderDescriptor:
    agent_id: str
    provider_id: str
    configured: bool = True
    network_allowed: bool = False
    can_start_engine: bool = False
    parallel: bool = False
    estimated_cost_cents: int = 0


@dataclass(frozen=True)
class RegisteredProvider:
    descriptor: ProviderDescriptor
    execute: ProviderExecutor


def validate_provider_manifest(
    providers: Mapping[str, RegisteredProvider],
) -> dict[str, Any]:
    """Validate every registered provider before dispatching any provider."""
    unknown = sorted(set(providers) - set(AGENT_ORDER))
    if unknown:
        raise AnalysisContractError(
            f"provider manifest contains unknown agent ids: {','.join(unknown)}"
        )

    configured: list[str] = []
    missing = [agent_id for agent_id in AGENT_ORDER if agent_id not in providers]

    for agent_id, provider in providers.items():
        if not isinstance(provider, RegisteredProvider):
            raise AnalysisContractError(
                f"provider must use RegisteredProvider metadata: {agent_id}"
            )
        descriptor = provider.descriptor
        if descriptor.agent_id != agent_id:
            raise AnalysisContractError(
                f"provider descriptor agent mismatch: {agent_id}"
            )
        if not isinstance(descriptor.provider_id, str) or not descriptor.provider_id.strip():
            raise AnalysisContractError(
                f"provider id is required: {agent_id}"
            )
        if not descriptor.configured:
            missing.append(agent_id)
            continue
        if descriptor.network_allowed is not False:
            raise AnalysisContractError(
                f"provider network must remain disabled: {agent_id}"
            )
        if descriptor.can_start_engine is not False:
            raise AnalysisContractError(
                f"provider cannot start the engine: {agent_id}"
            )
        if descriptor.parallel is not False:
            raise AnalysisContractError(
                f"provider parallel mode is forbidden: {agent_id}"
            )
        if descriptor.estimated_cost_cents != 0:
            raise AnalysisContractError(
                f"provider cost must remain zero: {agent_id}"
            )
        if not callable(provider.execute):
            raise AnalysisContractError(
                f"provider executor is not callable: {agent_id}"
            )
        configured.append(agent_id)

    missing = sorted(set(missing) - set(configured), key=AGENT_ORDER.index)
    return {
        "status": "READY" if not missing else "BLOCKED",
        "configured": [agent_id for agent_id in AGENT_ORDER if agent_id in configured],
        "missing": missing,
        "parallel": False,
        "network_started": False,
        "can_start_engine": False,
        "estimated_cost_cents": 0,
    }
