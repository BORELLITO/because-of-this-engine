"""Fail-closed production states for the V2.1 canonical path."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

STATES = ("DRAFT","PACKAGE_PENDING","FACT_CHECK_PENDING","STORY_PENDING","ASSETS_PENDING","RIGHTS_PENDING","REUSE_PENDING","VOICE_PENDING","AUDIO_PENDING","CAPTIONS_PENDING","PREVIEW_PENDING","THUMBNAIL_PENDING","THUMBNAIL_QA","HUMAN_REVIEW","TECHNICAL_QA","NEEDS_CORRECTION","BLOCKED","APPROVED_FOR_MANUAL_PUBLICATION","MANUALLY_PUBLISHED","METRICS_PENDING","ARCHIVED")
TRANSITIONS = {"DRAFT":{"PACKAGE_PENDING","BLOCKED"},"PACKAGE_PENDING":{"FACT_CHECK_PENDING","BLOCKED"},"FACT_CHECK_PENDING":{"STORY_PENDING","BLOCKED"},"STORY_PENDING":{"ASSETS_PENDING","BLOCKED"},"ASSETS_PENDING":{"RIGHTS_PENDING","BLOCKED"},"RIGHTS_PENDING":{"REUSE_PENDING","BLOCKED"},"REUSE_PENDING":{"VOICE_PENDING","BLOCKED"},"VOICE_PENDING":{"AUDIO_PENDING","BLOCKED"},"AUDIO_PENDING":{"CAPTIONS_PENDING","BLOCKED"},"CAPTIONS_PENDING":{"PREVIEW_PENDING","BLOCKED"},"PREVIEW_PENDING":{"THUMBNAIL_PENDING","BLOCKED"},"THUMBNAIL_PENDING":{"THUMBNAIL_QA","BLOCKED"},"THUMBNAIL_QA":{"HUMAN_REVIEW","NEEDS_CORRECTION","BLOCKED"},"HUMAN_REVIEW":{"TECHNICAL_QA","NEEDS_CORRECTION","BLOCKED"},"TECHNICAL_QA":{"APPROVED_FOR_MANUAL_PUBLICATION","NEEDS_CORRECTION","BLOCKED"},"APPROVED_FOR_MANUAL_PUBLICATION":{"MANUALLY_PUBLISHED","ARCHIVED","BLOCKED"},"MANUALLY_PUBLISHED":{"METRICS_PENDING","ARCHIVED"},"METRICS_PENDING":{"ARCHIVED"},"NEEDS_CORRECTION":{"PACKAGE_PENDING","FACT_CHECK_PENDING","STORY_PENDING","ASSETS_PENDING","RIGHTS_PENDING","REUSE_PENDING","VOICE_PENDING","AUDIO_PENDING","CAPTIONS_PENDING","PREVIEW_PENDING","THUMBNAIL_PENDING","BLOCKED"},"BLOCKED":{"PACKAGE_PENDING","ARCHIVED"},"ARCHIVED":set()}

class StateTransitionError(ValueError): pass
def assert_transition(current: str,target: str) -> None:
    if current not in STATES or target not in STATES: raise StateTransitionError(f"unknown state: {current}->{target}")
    if target not in TRANSITIONS[current]: raise StateTransitionError(f"invalid transition: {current}->{target}")
def advance(current: str,target: str,*,evidence: Mapping[str,Any]|None=None) -> dict[str,Any]:
    assert_transition(current,target)
    if target not in {"BLOCKED","NEEDS_CORRECTION"} and not evidence: raise StateTransitionError("evidence is required for every non-blocking transition")
    return {"previous_state":current,"state":target,"evidence":dict(evidence or {})}
def new_state_record(*,episode_id: str,implementation_id: str) -> dict[str,Any]:
    return {"episode_id":episode_id,"implementation_id":implementation_id,"state":"DRAFT","history":[],"production_enablement":False}
