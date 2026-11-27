"""Canonical crosswalk for the Brazil Files editorial checkpoints.

Brazil Files keeps its 11 editorial blocks and 22 analyst/reviewer checkpoints
for traceability. This module maps those checkpoints onto the eight canonical
Copilot roles. It does not create a second engine, provider, queue, or runtime.
Every mapped role is dispatched through the single sequential Copilot lane.
"""

from __future__ import annotations

from typing import Any, Mapping


CANONICAL_AGENT_IDS = (
    "research_analyst",
    "factual_reviewer",
    "story_editorial_agent",
    "rights_provenance_agent",
    "visual_continuity_agent",
    "timeline_caption_agent",
    "qa_release_reviewer",
    "delivery_agent",
)

EXECUTION_MODE = "SEQUENTIAL_REUSE_CANONICAL_AGENT"
SECONDARY_ENGINE_ALLOWED = False
PARALLEL_ALLOWED = False

# The source names are the 22 Brazil Files checkpoints in their existing
# editorial order. Reusing one canonical role for several checkpoints is
# intentional: the checkpoint boundary remains visible, while execution stays
# on one engine and one queue.
BRAZIL_FILES_ROLE_CROSSWALK = (
    {
        "order": 1,
        "source_role": "CASE_RESEARCH",
        "block_id": "01_CASE_RESEARCH",
        "kind": "analyst",
        "canonical_agent": "research_analyst",
        "approval_domain": "source_discovery_and_case_dossier",
    },
    {
        "order": 2,
        "source_role": "CASE_RESEARCH_REVIEW",
        "block_id": "01_CASE_RESEARCH",
        "kind": "reviewer",
        "canonical_agent": "factual_reviewer",
        "approval_domain": "source_and_timeline_verification",
    },
    {
        "order": 3,
        "source_role": "CLAIM_CALIBRATION",
        "block_id": "02_CLAIM_CALIBRATION",
        "kind": "analyst",
        "canonical_agent": "factual_reviewer",
        "approval_domain": "fact_legend_hypothesis_separation",
    },
    {
        "order": 4,
        "source_role": "CLAIM_CALIBRATION_REVIEW",
        "block_id": "02_CLAIM_CALIBRATION",
        "kind": "reviewer",
        "canonical_agent": "factual_reviewer",
        "approval_domain": "claim_calibration_review",
    },
    {
        "order": 5,
        "source_role": "BRAZILIAN_CONTEXT",
        "block_id": "03_BRAZILIAN_CONTEXT",
        "kind": "analyst",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "brazilian_context_and_cultural_value",
    },
    {
        "order": 6,
        "source_role": "BRAZILIAN_CONTEXT_REVIEW",
        "block_id": "03_BRAZILIAN_CONTEXT",
        "kind": "reviewer",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "respectful_context_regression_review",
    },
    {
        "order": 7,
        "source_role": "NARRATIVE_ARCHITECT",
        "block_id": "04_NARRATIVE_ARCHITECTURE",
        "kind": "analyst",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "causal_arc_and_payoff",
    },
    {
        "order": 8,
        "source_role": "NARRATIVE_ARCHITECTURE_REVIEW",
        "block_id": "04_NARRATIVE_ARCHITECTURE",
        "kind": "reviewer",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "narrative_structure_review",
    },
    {
        "order": 9,
        "source_role": "RETENTION_ARCHITECT",
        "block_id": "05_RETENTION_ENGINEERING",
        "kind": "analyst",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "hook_escalation_emotion_and_cta",
    },
    {
        "order": 10,
        "source_role": "RETENTION_REVIEW",
        "block_id": "05_RETENTION_ENGINEERING",
        "kind": "reviewer",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "retention_regression_review",
    },
    {
        "order": 11,
        "source_role": "ENGLISH_LOCALIZATION",
        "block_id": "06_ENGLISH_LOCALIZATION",
        "kind": "analyst",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "natural_en_us_localization",
    },
    {
        "order": 12,
        "source_role": "ENGLISH_LOCALIZATION_REVIEW",
        "block_id": "06_ENGLISH_LOCALIZATION",
        "kind": "reviewer",
        "canonical_agent": "story_editorial_agent",
        "approval_domain": "meaning_preservation_review",
    },
    {
        "order": 13,
        "source_role": "VISUAL_MATCH",
        "block_id": "07_VISUAL_MATCH",
        "kind": "analyst",
        "canonical_agent": "visual_continuity_agent",
        "approval_domain": "direct_visual_anchor",
    },
    {
        "order": 14,
        "source_role": "VISUAL_MATCH_REVIEW",
        "block_id": "07_VISUAL_MATCH",
        "kind": "reviewer",
        "canonical_agent": "visual_continuity_agent",
        "approval_domain": "semantic_visual_match_review",
    },
    {
        "order": 15,
        "source_role": "VISUAL_CLIP_DIRECTOR",
        "block_id": "08_VISUAL_CLIP_DIRECTION",
        "kind": "analyst",
        "canonical_agent": "visual_continuity_agent",
        "approval_domain": "clip_selection_and_continuity",
    },
    {
        "order": 16,
        "source_role": "VISUAL_CONTINUITY_REVIEW",
        "block_id": "08_VISUAL_CLIP_DIRECTION",
        "kind": "reviewer",
        "canonical_agent": "visual_continuity_agent",
        "approval_domain": "rights_aware_visual_continuity_review",
    },
    {
        "order": 17,
        "source_role": "RIGHTS_AND_CITATION",
        "block_id": "09_RIGHTS_AND_CITATION",
        "kind": "analyst",
        "canonical_agent": "rights_provenance_agent",
        "approval_domain": "source_license_and_provenance",
    },
    {
        "order": 18,
        "source_role": "RIGHTS_REVIEW",
        "block_id": "09_RIGHTS_AND_CITATION",
        "kind": "reviewer",
        "canonical_agent": "rights_provenance_agent",
        "approval_domain": "rights_and_citation_review",
    },
    {
        "order": 19,
        "source_role": "BRAND_CONTINUITY",
        "block_id": "10_BRAND_CONTINUITY",
        "kind": "analyst",
        "canonical_agent": "timeline_caption_agent",
        "approval_domain": "voice_logo_caption_and_outro_lock",
    },
    {
        "order": 20,
        "source_role": "BRAND_REGRESSION_REVIEW",
        "block_id": "10_BRAND_CONTINUITY",
        "kind": "reviewer",
        "canonical_agent": "qa_release_reviewer",
        "approval_domain": "brand_regression_review",
    },
    {
        "order": 21,
        "source_role": "SCRIPT_QA",
        "block_id": "11_FINAL_QA",
        "kind": "analyst",
        "canonical_agent": "qa_release_reviewer",
        "approval_domain": "editorial_and_production_trap_detection",
    },
    {
        "order": 22,
        "source_role": "RED_TEAM_REVIEW",
        "block_id": "11_FINAL_QA",
        "kind": "reviewer",
        "canonical_agent": "qa_release_reviewer",
        "approval_domain": "adversarial_final_review",
    },
)

TERMINAL_HANDOFF = {
    "canonical_agent": "delivery_agent",
    "after_order": 22,
    "requires": "ALL_BRAZIL_FILES_CHECKPOINTS_PASS",
    "approval_domain": "verified_delivery_package_without_publication",
}


class BrazilFilesCrosswalkError(ValueError):
    """Raised when the editorial-to-canonical crosswalk drifts."""


def validate_crosswalk(
    crosswalk: tuple[Mapping[str, Any], ...] = BRAZIL_FILES_ROLE_CROSSWALK,
    terminal_handoff: Mapping[str, Any] = TERMINAL_HANDOFF,
) -> dict[str, Any]:
    """Validate the 22-to-8 mapping and its single-engine constraints."""

    errors: list[str] = []
    rows = tuple(crosswalk)
    if len(rows) != 22:
        errors.append("crosswalk must contain exactly 22 Brazil Files checkpoints")

    expected_orders = list(range(1, len(rows) + 1))
    actual_orders = [row.get("order") for row in rows if isinstance(row, Mapping)]
    if actual_orders != expected_orders:
        errors.append("crosswalk orders must be contiguous from 1 to 22")

    source_roles = [row.get("source_role") for row in rows if isinstance(row, Mapping)]
    if len(set(source_roles)) != len(source_roles):
        errors.append("source roles must be unique")

    invalid_agents = [
        row.get("canonical_agent")
        for row in rows
        if isinstance(row, Mapping) and row.get("canonical_agent") not in CANONICAL_AGENT_IDS
    ]
    if invalid_agents:
        errors.append("every checkpoint must map to a canonical agent")

    blocks = {row.get("block_id") for row in rows if isinstance(row, Mapping)}
    if len(blocks) != 11:
        errors.append("crosswalk must preserve the 11 Brazil Files blocks")

    if not isinstance(terminal_handoff, Mapping):
        errors.append("terminal handoff must be an object")
    else:
        if terminal_handoff.get("canonical_agent") != "delivery_agent":
            errors.append("delivery_agent must remain the terminal handoff")
        if terminal_handoff.get("after_order") != 22:
            errors.append("delivery handoff must occur after checkpoint 22")
        if terminal_handoff.get("requires") != "ALL_BRAZIL_FILES_CHECKPOINTS_PASS":
            errors.append("delivery must require all checkpoint receipts")

    mapped_agents = {row.get("canonical_agent") for row in rows if isinstance(row, Mapping)}
    if "delivery_agent" in mapped_agents:
        errors.append("delivery_agent must not execute an editorial checkpoint")
    if mapped_agents | {terminal_handoff.get("canonical_agent")} != set(CANONICAL_AGENT_IDS):
        errors.append("all eight canonical agents must be represented exactly once as capabilities")

    return {
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "source_checkpoint_count": len(rows),
        "canonical_agent_count": len(CANONICAL_AGENT_IDS),
        "mapped_editorial_capabilities": len(mapped_agents),
        "terminal_agent": terminal_handoff.get("canonical_agent") if isinstance(terminal_handoff, Mapping) else None,
        "execution_mode": EXECUTION_MODE,
        "parallel_allowed": PARALLEL_ALLOWED,
        "secondary_engine_allowed": SECONDARY_ENGINE_ALLOWED,
    }


def canonical_agent_for(source_role: str) -> str:
    """Resolve one source checkpoint without creating a new runtime agent."""

    for row in BRAZIL_FILES_ROLE_CROSSWALK:
        if row["source_role"] == source_role:
            return row["canonical_agent"]
    raise BrazilFilesCrosswalkError(f"unknown Brazil Files source role: {source_role}")


def build_crosswalk_report() -> dict[str, Any]:
    """Return a deterministic report suitable for a read-only technical gate."""

    return validate_crosswalk()


if __name__ == "__main__":
    import json

    print(json.dumps(build_crosswalk_report(), ensure_ascii=False, indent=2))
