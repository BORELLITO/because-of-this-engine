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

# Operationalized from the approved Brazil Files visual direction. This is a
# selection contract, not a renderer contract: it prevents the editorial
# pipeline from passing visually attractive but semantically wrong material to
# Runflow.
VISUAL_CLIP_BLOCK_SPEC = {
    "doctrine": "HYBRID_DOCUMENTARY_DRAMATIZATION",
    "dramatization_mode": "FACELESS_CINEMATIC_REENACTMENT",
    "source_strategy": "VERIFIED_ARCHIVE_LICENSED_STOCK_TARGETED_GENERATION",
    "rhythm": "PROGRESSIVE",
    "shot_count": 16,
    "distribution": {
        "EVIDENCE_OR_ARCHIVE": 5,
        "BRAZILIAN_REAL_WORLD": 5,
        "FACELESS_REENACTMENT": 5,
        "CTA": 1,
    },
    "treatment": "CINEMATIC_DOCUMENTARY",
    "camera_language": "CONTROLLED_REALISTIC",
    "continuity": "STRICT",
    "transition_language": "NARRATIVE_MOTIVATED",
    "disclosure_label": "DRAMATIZED REENACTMENT",
    "candidate_range_per_beat": [3, 5],
    "selection_priority": [
        "DIRECT_SEMANTIC_MATCH",
        "BRAZILIAN_CONTEXT",
        "TEMPORAL_AND_GEOGRAPHIC_CONTINUITY",
        "VERIFIED_RIGHTS",
        "CINEMATIC_QUALITY",
    ],
    "approval_mode": "AUTOMATIC_FAIL_CLOSED",
    "source_asset_reuse": "BLOCK_GLOBAL",
}

CLIP_REPRESENTATION_TYPES = frozenset(VISUAL_CLIP_BLOCK_SPEC["distribution"])
CLIP_REQUIRED_FIELDS = (
    "beat_id",
    "script_excerpt",
    "narrative_function",
    "representation_type",
    "visual_anchor",
    "location",
    "era",
    "camera",
    "continuity",
    "candidates",
    "selected_candidate",
    "rejection_log",
)

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


def _mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _candidate_has_verified_rights(candidate: Mapping[str, Any]) -> bool:
    return (
        _text(candidate.get("candidate_id"))
        and _text(candidate.get("source_url"))
        and _text(candidate.get("license"))
        and _text(candidate.get("fingerprint"))
        and candidate.get("rights_status") == "VERIFIED"
    )


def validate_clip_selection_dossier(dossier: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the 16-beat visual hand-off before Runflow preparation.

    The validator intentionally checks editorial evidence and provenance, not
    whether a media file is playable. Media probing remains a later technical
    gate. A dossier cannot pass by omitting rejected candidates or by treating
    a beautiful but semantically wrong clip as an acceptable fallback.
    """
    errors: list[str] = []
    if not isinstance(dossier, Mapping):
        return {
            "status": "BLOCKED",
            "errors": ["clip selection dossier must be an object"],
            "beat_count": 0,
        }

    beats = dossier.get("beats")
    if not isinstance(beats, list):
        errors.append("beats must be a list")
        beats = []
    if len(beats) != VISUAL_CLIP_BLOCK_SPEC["shot_count"]:
        errors.append("dossier must contain exactly 16 beats")

    seen_beats: set[str] = set()
    seen_fingerprints: set[str] = set()
    representation_counts = {kind: 0 for kind in CLIP_REPRESENTATION_TYPES}
    for index, beat in enumerate(beats, start=1):
        if not _mapping(beat):
            errors.append(f"beat {index} must be an object")
            continue
        missing = [field for field in CLIP_REQUIRED_FIELDS if field not in beat]
        if missing:
            errors.append(f"beat {index} missing fields: {', '.join(missing)}")
            continue

        beat_id = str(beat.get("beat_id", "")).strip()
        if not _text(beat_id) or beat_id in seen_beats:
            errors.append(f"beat {index} has a missing or duplicate beat_id")
        seen_beats.add(beat_id)
        for field in ("script_excerpt", "narrative_function", "visual_anchor", "location", "era"):
            if not _text(beat.get(field)):
                errors.append(f"beat {beat_id or index} {field} must be non-empty text")

        representation = beat.get("representation_type")
        if representation not in CLIP_REPRESENTATION_TYPES:
            errors.append(f"beat {beat_id or index} has an invalid representation_type")
        else:
            representation_counts[representation] += 1

        camera = beat.get("camera")
        continuity = beat.get("continuity")
        if not _mapping(camera) or camera.get("language") != "CONTROLLED_REALISTIC":
            errors.append(f"beat {beat_id or index} must use controlled realistic camera language")
        if not _mapping(continuity):
            errors.append(f"beat {beat_id or index} continuity must be an object")
        else:
            for field in ("previous_link", "next_link", "light", "mood"):
                if not _text(continuity.get(field)):
                    errors.append(f"beat {beat_id or index} continuity missing {field}")

        candidates = beat.get("candidates")
        if not isinstance(candidates, list):
            errors.append(f"beat {beat_id or index} candidates must be a list")
            candidates = []
        minimum, maximum = VISUAL_CLIP_BLOCK_SPEC["candidate_range_per_beat"]
        candidate_floor = 1 if representation == "CTA" else minimum
        if not candidate_floor <= len(candidates) <= maximum:
            errors.append(f"beat {beat_id or index} must contain {candidate_floor} to {maximum} candidates")

        selected = beat.get("selected_candidate")
        selected_id = selected.get("candidate_id") if _mapping(selected) else None
        selected_count = 0
        candidate_ids: set[str] = set()
        for candidate in candidates:
            if not _mapping(candidate):
                errors.append(f"beat {beat_id or index} contains a non-object candidate")
                continue
            candidate_id = str(candidate.get("candidate_id", "")).strip()
            if not candidate_id or candidate_id in candidate_ids:
                errors.append(f"beat {beat_id or index} has a missing or duplicate candidate_id")
            candidate_ids.add(candidate_id)
            decision = candidate.get("decision")
            if decision == "SELECTED":
                selected_count += 1
                if not _candidate_has_verified_rights(candidate) and representation != "CTA":
                    errors.append(f"beat {beat_id or index} selected candidate lacks verified rights metadata")
            elif decision != "REJECTED":
                errors.append(f"beat {beat_id or index} candidate decision must be SELECTED or REJECTED")
            if decision == "REJECTED" and not _text(candidate.get("rejection_reason")):
                errors.append(f"beat {beat_id or index} rejected candidates need a rejection_reason")
        if selected_count != 1 or not _mapping(selected) or selected_id not in candidate_ids:
            errors.append(f"beat {beat_id or index} must have exactly one selected candidate")
        if not isinstance(beat.get("rejection_log"), list):
            errors.append(f"beat {beat_id or index} rejection_log must be a list")

        if representation == "FACELESS_REENACTMENT":
            if beat.get("disclosure_label") != VISUAL_CLIP_BLOCK_SPEC["disclosure_label"]:
                errors.append(f"beat {beat_id or index} reenactment disclosure is required")
        elif beat.get("disclosure_label") not in (None, ""):
            errors.append(f"beat {beat_id or index} has an unexpected disclosure label")

        if _mapping(selected):
            fingerprint = str(selected.get("fingerprint", "")).strip()
            if fingerprint and fingerprint in seen_fingerprints:
                errors.append(f"selected asset is reused: {fingerprint}")
            if fingerprint:
                seen_fingerprints.add(fingerprint)

    expected_distribution = VISUAL_CLIP_BLOCK_SPEC["distribution"]
    if representation_counts != expected_distribution:
        errors.append(
            "representation distribution must be exactly "
            + ", ".join(f"{key}={value}" for key, value in expected_distribution.items())
        )
    if dossier.get("approval_mode") != VISUAL_CLIP_BLOCK_SPEC["approval_mode"]:
        errors.append("approval_mode must be AUTOMATIC_FAIL_CLOSED")
    if dossier.get("semantic_match") != "DIRECT":
        errors.append("semantic_match must be DIRECT")
    if dossier.get("source_asset_reuse") != "BLOCK_GLOBAL":
        errors.append("source_asset_reuse must be BLOCK_GLOBAL")

    return {
        "status": "PASS" if not errors else "BLOCKED",
        "beat_count": len(beats),
        "representation_counts": representation_counts,
        "selected_asset_count": len(seen_fingerprints),
        "errors": errors,
    }


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
        "visual_clip_block_spec": VISUAL_CLIP_BLOCK_SPEC,
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
            "clip-selection-dossier.json",
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

