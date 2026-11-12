"""Reconcile persisted narration/caption artifacts with the production record.

This audit records real artifact evidence without converting it into a final
mix, render, Drive-delivery, or publication authorization.
"""
from __future__ import annotations

import re
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _status(gate: str, failures: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "gate": gate,
        "status": "PASS" if not failures else "BLOCKED",
        "failures": sorted(set(failures)),
        **extra,
    }


def reconcile_artifacts(
    production_record: dict[str, Any],
    story_architecture: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare recorded Gemini/Charon artifacts without authorizing release."""
    narration = (story_architecture or {}).get("narration")
    if not isinstance(narration, dict) or narration.get("execution_status") != "GEMINI_CHARON_NARRATION_READY":
        return _status(
            "EP005_ARTIFACT_RECONCILIATION",
            [],
            mode="NOT_APPLICABLE_NO_PERSISTED_ARTIFACT_CLAIM",
            release_authorized=False,
        )

    latest = narration.get("latest_attempt")
    captions = narration.get("captions")
    failures: list[str] = []
    if not isinstance(latest, dict):
        failures.append("story architecture latest_attempt is missing")
        latest = {}
    if not isinstance(captions, dict):
        failures.append("story architecture captions evidence is missing")
        captions = {}

    expected_audio_sha = str(latest.get("audio_sha256") or "").strip().lower()
    expected_duration = latest.get("duration_seconds")
    expected_audio_artifact = str(latest.get("artifact") or "").strip()
    expected_audio_run = latest.get("workflow_run_id")
    expected_caption_artifact = str(captions.get("artifact") or "").strip()
    expected_caption_run = captions.get("workflow_run_id")
    if not SHA256.fullmatch(expected_audio_sha):
        failures.append("story architecture audio_sha256 is invalid")
    if not isinstance(expected_duration, (int, float)) or isinstance(expected_duration, bool):
        failures.append("story architecture duration_seconds is invalid")
    if not expected_audio_artifact or not isinstance(expected_audio_run, int):
        failures.append("story architecture narration artifact identity is incomplete")
    if not expected_caption_artifact or not isinstance(expected_caption_run, int):
        failures.append("story architecture caption artifact identity is incomplete")

    audio_evidence = production_record.get("narration_artifact_evidence")
    caption_evidence = production_record.get("caption_artifact_evidence")
    if not isinstance(audio_evidence, dict):
        failures.append("production record narration_artifact_evidence is missing")
        audio_evidence = {}
    if not isinstance(caption_evidence, dict):
        failures.append("production record caption_artifact_evidence is missing")
        caption_evidence = {}

    comparisons = (
        ("narration audio sha", audio_evidence.get("audio_sha256"), expected_audio_sha),
        ("narration duration", audio_evidence.get("duration_seconds"), expected_duration),
        ("narration artifact", audio_evidence.get("artifact_name"), expected_audio_artifact),
        ("narration workflow", audio_evidence.get("workflow_run_id"), expected_audio_run),
        ("caption artifact", caption_evidence.get("artifact_name"), expected_caption_artifact),
        ("caption workflow", caption_evidence.get("workflow_run_id"), expected_caption_run),
    )
    for label, actual, expected in comparisons:
        if actual != expected:
            failures.append(f"{label} differs between production record and story architecture")

    if audio_evidence.get("status") != "VERIFIED_GITHUB_ACTIONS_ARTIFACT":
        failures.append("narration artifact evidence status is not verified")
    if caption_evidence.get("status") != "VERIFIED_GITHUB_ACTIONS_ARTIFACT":
        failures.append("caption artifact evidence status is not verified")
    if production_record.get("production_enablement") is not False:
        failures.append("artifact reconciliation cannot enable production")
    return _status(
        "EP005_ARTIFACT_RECONCILIATION",
        failures,
        mode="PERSISTED_ARTIFACTS_RECONCILED",
        narration_artifact_verified=not failures,
        captions_artifact_verified=not failures,
        release_authorized=False,
        final_mix_bound=False,
        publication_authorized=False,
    )
