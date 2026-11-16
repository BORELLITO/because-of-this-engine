"""Fail-closed contract for manually captured LoreMotion clips.

LoreMotion is an optional browser source, not a production render engine.
This module validates evidence and metadata only; it never downloads, renders,
promotes, publishes, or changes the active episode manifest.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

CANONICAL_PROVIDER = "loremotion"
ALLOWED_MODELS = frozenset({"LTX 2.5", "MiniMax H3"})
ALLOWED_ASPECT_RATIO = "9:16"
ALLOWED_WATERMARK_STATUS = "NONE"
ALLOWED_CAPTURE_MODE = "browser_manual"
ALLOWED_PROMOTION_MODE = "MANUAL_REVIEW_ONLY"
MAX_DURATION_SECONDS = 15.0


def _loremotion_url(value: Any, path_fragment: str | None = None) -> bool:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme != "https" or parsed.hostname != "loremotion.com":
        return False
    return path_fragment is None or path_fragment in parsed.path


def _safe_relative_asset_path(value: Any) -> bool:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    return bool(raw) and not path.is_absolute() and ".." not in path.parts


def validate_loremotion_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    provider = str(candidate.get("provider") or "").strip().lower()
    model = str(candidate.get("model") or "").strip()
    aspect_ratio = str(candidate.get("aspect_ratio") or "").strip()
    capture_mode = str(candidate.get("capture_mode") or "").strip()
    promotion = str(candidate.get("promotion") or "").strip()

    if provider != CANONICAL_PROVIDER:
        failures.append(f"provider must be {CANONICAL_PROVIDER}")
    if model not in ALLOWED_MODELS:
        failures.append(f"model must be one of {sorted(ALLOWED_MODELS)}")
    if aspect_ratio != ALLOWED_ASPECT_RATIO:
        failures.append("aspect_ratio must be 9:16")
    if capture_mode != ALLOWED_CAPTURE_MODE:
        failures.append("capture_mode must be browser_manual")
    if promotion != ALLOWED_PROMOTION_MODE:
        failures.append("promotion must remain MANUAL_REVIEW_ONLY")
    if candidate.get("approved_for_render") is True:
        failures.append("LoreMotion candidates cannot self-authorize render")

    if not _loremotion_url(candidate.get("source_page_url"), "/generate"):
        failures.append("source_page_url must be the LoreMotion generator")
    if not _safe_relative_asset_path(candidate.get("asset_path")):
        failures.append("asset_path must be a safe relative path")

    try:
        width = int(candidate.get("width", 0))
        height = int(candidate.get("height", 0))
        duration = float(candidate.get("duration_seconds", 0))
    except (TypeError, ValueError):
        width = height = 0
        duration = 0.0
        failures.append("width, height and duration_seconds must be numeric")
    if width < 720 or height < 720:
        failures.append("source resolution must be at least 720 pixels on both axes")
    if height and abs((width / height) - (9 / 16)) > 0.02:
        failures.append("source dimensions must preserve the locked 9:16 aspect ratio")
    if not 0 < duration <= MAX_DURATION_SECONDS:
        failures.append("duration_seconds must be greater than 0 and at most 15 seconds")

    browser_receipt = candidate.get("browser_receipt")
    if not isinstance(browser_receipt, dict):
        failures.append("browser_receipt is required")
    else:
        if browser_receipt.get("status") != "DONE":
            failures.append("browser_receipt.status must be DONE")
        if browser_receipt.get("model") != model:
            failures.append("browser_receipt.model does not match candidate model")
        if browser_receipt.get("aspect_ratio") != aspect_ratio:
            failures.append("browser_receipt.aspect_ratio does not match candidate")
        if browser_receipt.get("watermark_status") != ALLOWED_WATERMARK_STATUS:
            failures.append("browser_receipt.watermark_status must be NONE")

    rights = candidate.get("rights_receipt")
    if not isinstance(rights, dict):
        failures.append("rights_receipt is required")
    else:
        if rights.get("status") != "VERIFIED":
            failures.append("rights_receipt.status must be VERIFIED")
        if rights.get("commercial_use_claim") is not True:
            failures.append("commercial_use_claim must be explicitly recorded")
        if rights.get("input_rights_confirmed") is not True:
            failures.append("input_rights_confirmed must be explicitly confirmed")
        if rights.get("model_terms_checked") is not True:
            failures.append("model_terms_checked must be explicitly confirmed")
        if not _loremotion_url(rights.get("terms_url"), "/terms"):
            failures.append("rights_receipt.terms_url must point to LoreMotion Terms")
        if not _loremotion_url(rights.get("acceptable_use_url"), "/acceptable-use"):
            failures.append("rights_receipt.acceptable_use_url must point to LoreMotion Acceptable Use")

    return {
        "gate": "LOREMOTION_MANUAL_INTAKE_V21",
        "status": "PASS" if not failures else "BLOCKED",
        "failures": failures,
        "provider": CANONICAL_PROVIDER,
        "model": model,
        "promotion": "BLOCKED_BY_DEFAULT",
        "approved_for_render": False,
        "render": "NOT_RUN",
        "publication": "NOT_RUN",
        "next_action": (
            "human_visual_qa_then_manifest_review"
            if not failures
            else "correct_receipt_or_metadata"
        ),
    }


__all__ = ["validate_loremotion_candidate"]
