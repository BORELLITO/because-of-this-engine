"""Editorial orchestration contract for the Brazil Files era.

This module does not research the web, generate narration or render media. It
defines the deterministic hand-off between the editorial subagents and the
canonical Runflow. A case must pass this contract before it can become an
episode package.
"""

from __future__ import annotations

from typing import Any, Mapping


BRAZIL_FILES_EDITORIAL_ID = "because-of-this-brazil-files-v1"
NARRATION_LANGUAGE = "en-US"
VISUAL_PROFILE = "cinematic_dread_v73"
BRAZIL_FIRST_MODE = "BRAZIL_FIRST_RESPECTFUL_DOCUMENTARY"

RETENTION_FRAMEWORK = {
    "hook_window_seconds": [0, 3],
    "required_beats": [
        "specific_hook",
        "brazilian_context",
        "escalation",
        "contradiction_or_reveal",
        "emotional_payoff",
        "single_cta",
    ],
    "forbidden_shortcuts": [
        "clickbait_without_payoff",
        "unsupported_claim_as_fact",
        "generic_brazil_stereotype",
        "cta_before_payoff",
    ],
}

VISUAL_CLIP_CONTRACT = {
    "semantic_match": "MANDATORY",
    "brazilian_context": "MANDATORY_WHEN_NARRATIVELY_RELEVANT",
    "temporal_continuity": "MANDATORY",
    "geographic_continuity": "MANDATORY",
    "lighting_and_mood_continuity": "MANDATORY",
    "generic_filler_clips": "BLOCK",
    "beautiful_but_semantically_wrong_clips": "BLOCK",
    "source_asset_reuse": "BLOCK_GLOBAL",
    "rights_and_provenance": "MANDATORY",
    "dramatization_disclosure": "REQUIRED_WHEN_NEEDED",
}

CASE_LANES = {
    "DOCUMENTED_UNEXPLAINED",
    "FAMOUS_LEGEND",
    "DISPUTED_OR_EXPLAINED",
}

PRODUCTION_BLOCKS = (
    {
        "block_id": "01_CASE_RESEARCH",
        "analyst": "CASE_RESEARCH",
        "reviewer": "CASE_RESEARCH_REVIEW",
        "output": "case-dossier.json",
        "gate": "sources_and_timeline_verified",
    },
    {
        "block_id": "02_CLAIM_CALIBRATION",
        "analyst": "CLAIM_CALIBRATION",
        "reviewer": "CLAIM_CALIBRATION_REVIEW",
        "output": "claim-calibration.json",
        "gate": "fact_claim_legend_and_hypothesis_separated",
    },
    {
        "block_id": "03_BRAZILIAN_CONTEXT",
        "analyst": "BRAZILIAN_CONTEXT",
        "reviewer": "BRAZILIAN_CONTEXT_REVIEW",
        "output": "brazil-context.json",
        "gate": "brazilian_value_and_respect_verified",
    },
    {
        "block_id": "04_NARRATIVE_ARCHITECTURE",
        "analyst": "NARRATIVE_ARCHITECT",
        "reviewer": "NARRATIVE_ARCHITECTURE_REVIEW",
        "output": "narrative-outline.json",
        "gate": "causal_arc_and_payoff_verified",
    },
    {
        "block_id": "05_RETENTION_ENGINEERING",
        "analyst": "RETENTION_ARCHITECT",
        "reviewer": "RETENTION_REVIEW",
        "output": "retention-map.json",
        "gate": "hook_escalation_emotion_and_cta_verified",
    },
    {
        "block_id": "06_ENGLISH_LOCALIZATION",
        "analyst": "ENGLISH_LOCALIZATION",
        "reviewer": "ENGLISH_LOCALIZATION_REVIEW",
        "output": "script-en-US.txt",
        "gate": "natural_english_and_meaning_preserved",
    },
    {
        "block_id": "07_VISUAL_MATCH",
        "analyst": "VISUAL_MATCH",
        "reviewer": "VISUAL_MATCH_REVIEW",
        "output": "visual-beat-map.json",
        "gate": "every_narrative_beat_has_direct_visual_anchor",
    },
    {
        "block_id": "08_VISUAL_CLIP_DIRECTION",
        "analyst": "VISUAL_CLIP_DIRECTOR",
        "reviewer": "VISUAL_CONTINUITY_REVIEW",
        "output": "clip-selection-dossier.json",
        "gate": "semantic_continuity_rights_and_non_reuse_verified",
    },
    {
        "block_id": "09_RIGHTS_AND_CITATION",
        "analyst": "RIGHTS_AND_CITATION",
        "reviewer": "RIGHTS_REVIEW",
        "output": "rights-and-citations.json",
        "gate": "source_and_media_rights_verified",
    },
    {
        "block_id": "10_BRAND_CONTINUITY",
        "analyst": "BRAND_CONTINUITY",
        "reviewer": "BRAND_REGRESSION_REVIEW",
        "output": "brand-continuity.json",
        "gate": "voice_visual_caption_logo_and_outro_locked",
    },
    {
        "block_id": "11_FINAL_QA",
        "analyst": "SCRIPT_QA",
        "reviewer": "RED_TEAM_REVIEW",
        "output": "script-qa.json",
        "gate": "all_editorial_and_production_traps_closed",
    },
)

AGENT_PIPELINE = tuple(
    agent
    for block in PRODUCTION_BLOCKS
    for agent in (block["analyst"], block["reviewer"])
)

REQUIRED_BRIEF_FIELDS = (
    "case_id",
    "working_title",
    "lane",
    "premise",
    "source_urls",
    "unknowns",
    "visual_anchors",
    "brazilian_anchor",
    "cultural_value",
)


class BrazilFilesOrchestratorError(ValueError):
    """Raised when a Brazil Files case brief is unsafe or incomplete."""


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def validate_case_brief(brief: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the editorial hand-off without pretending research is complete."""
    if not isinstance(brief, Mapping):
        raise BrazilFilesOrchestratorError("case brief must be an object")

    errors: list[str] = []
    missing = [field for field in REQUIRED_BRIEF_FIELDS if field not in brief]
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")

    lane = str(brief.get("lane", "")).strip()
    if lane and lane not in CASE_LANES:
        errors.append(f"lane must be one of: {', '.join(sorted(CASE_LANES))}")

    if brief.get("narration_language", NARRATION_LANGUAGE) != NARRATION_LANGUAGE:
        errors.append("narration_language must remain en-US")
    if brief.get("visual_profile", VISUAL_PROFILE) != VISUAL_PROFILE:
        errors.append("visual_profile must remain cinematic_dread_v73")
    if brief.get("preserve_visual_motor", True) is not True:
        errors.append("preserve_visual_motor must be true")

    for field in ("case_id", "working_title", "premise"):
        if field in brief and not _text(brief.get(field)):
            errors.append(f"{field} must be non-empty text")
    for field in ("source_urls", "unknowns", "visual_anchors"):
        if field in brief and not _text_list(brief.get(field)):
            errors.append(f"{field} must be a non-empty list of text")
    for field in ("brazilian_anchor", "cultural_value"):
        if field in brief and not _text(brief.get(field)):
            errors.append(f"{field} must be non-empty text")

    representation_mode = brief.get("representation_mode", BRAZIL_FIRST_MODE)
    if representation_mode != BRAZIL_FIRST_MODE:
        errors.append("representation_mode must remain BRAZIL_FIRST_RESPECTFUL_DOCUMENTARY")

    forbidden_scope = ("verbo no chão", "verbo-no-chao", "verbo_no_chao")
    serialized = str(dict(brief)).lower()
    if any(marker in serialized for marker in forbidden_scope):
        errors.append("brief references an isolated project outside this repository")

    return {
        "status": "PASS" if not errors else "BLOCKED",
        "editorial_id": BRAZIL_FILES_EDITORIAL_ID,
        "case_id": brief.get("case_id"),
        "lane": lane or None,
        "narration_language": NARRATION_LANGUAGE,
        "visual_profile": VISUAL_PROFILE,
        "representation_mode": BRAZIL_FIRST_MODE,
        "brazil_is_editorial_protagonist": True,
        "preserve_visual_motor": True,
        "errors": errors,
    }


def build_preparation_plan(brief: Mapping[str, Any]) -> dict[str, Any]:
    """Return a fail-closed plan for the subagents and Runflow hand-off."""
    report = validate_case_brief(brief)
    if report["status"] != "PASS":
        raise BrazilFilesOrchestratorError("case brief is blocked: " + "; ".join(report["errors"]))

    return {
        "status": "READY_FOR_AGENT_EXECUTION",
        "editorial_id": BRAZIL_FILES_EDITORIAL_ID,
        "case_id": brief["case_id"],
        "lane": brief["lane"],
        "narration_language": NARRATION_LANGUAGE,
        "visual_profile": VISUAL_PROFILE,
        "representation_mode": BRAZIL_FIRST_MODE,
        "brazil_is_editorial_protagonist": True,
        "preserve_visual_motor": True,
        "retention_framework": RETENTION_FRAMEWORK,
        "visual_clip_contract": VISUAL_CLIP_CONTRACT,
        "flow_status": "PENDING_BLOCK_EXECUTION",
        "runflow_handoff": "BLOCKED_UNTIL_ALL_BLOCK_REVIEWERS_PASS",
        "blocks": [
            {
                **block,
                "analyst_status": "PENDING",
                "reviewer_status": "PENDING",
                "gate_status": "BLOCKED_UNTIL_REVIEW_PASS",
            }
            for block in PRODUCTION_BLOCKS
        ],
        "agents": [
            {"name": name, "status": "REQUIRED"}
            for name in AGENT_PIPELINE
        ],
        "required_outputs": [
            "case-dossier.json",
            "claim-calibration.json",
            "script-en-US.txt",
            "visual-beat-map.json",
            "rights-and-citations.json",
            "brand-continuity.json",
            "script-qa.json",
        ],
    }


def validate_flow_receipts(receipts: Mapping[str, Any]) -> dict[str, Any]:
    """Close the preparation flow only when every analyst/reviewer pair passes."""
    raw_blocks = receipts.get("blocks") if isinstance(receipts, Mapping) else None
    if not isinstance(raw_blocks, Mapping):
        return {
            "status": "FLOW_BLOCKED",
            "flow_status": "MISSING_BLOCK_RECEIPTS",
            "failed_blocks": [block["block_id"] for block in PRODUCTION_BLOCKS],
            "runflow_handoff": "BLOCKED",
        }

    failed: list[str] = []
    missing: list[str] = []
    evaluated: list[dict[str, Any]] = []
    for block in PRODUCTION_BLOCKS:
        block_id = block["block_id"]
        receipt = raw_blocks.get(block_id)
        if not isinstance(receipt, Mapping):
            missing.append(block_id)
            evaluated.append({"block_id": block_id, "status": "MISSING"})
            continue
        analyst = receipt.get("analyst_status")
        reviewer = receipt.get("reviewer_status")
        passed = analyst == "PASS" and reviewer == "PASS"
        if not passed:
            failed.append(block_id)
        evaluated.append({
            "block_id": block_id,
            "analyst_status": analyst,
            "reviewer_status": reviewer,
            "status": "PASS" if passed else "BLOCKED",
        })

    blocked = sorted(set(failed + missing))
    return {
        "status": "FLOW_PASS" if not blocked else "FLOW_BLOCKED",
        "flow_status": "ALL_BLOCK_REVIEWERS_PASS" if not blocked else "REVIEW_REQUIRED",
        "block_count": len(PRODUCTION_BLOCKS),
        "evaluated_blocks": evaluated,
        "failed_blocks": blocked,
        "runflow_handoff": "READY_FOR_RUNFLOW_PREPARATION_GATE" if not blocked else "BLOCKED",
    }

