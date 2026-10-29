#!/usr/bin/env python3
"""Executable V6 compliance contracts that sit between the prompt and the renderer.

The creative inputs may change per episode. The production invariants do not.
This module is intentionally deterministic and fail-closed.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROMPT_GATE_ORDER = (
    ("G0", "PRE_FLIGHT"),
    ("G1", "SCRIPT_SUSPENSE"),
    ("G2", "RIGHTS_ORIGINALITY_FICTION"),
    ("G3", "VISUAL_CLIPS"),
    ("G4", "NARRATION"),
    ("G5", "AUDIO_MIX"),
    ("G6", "CAPTIONS_KARAOKE"),
    ("G7", "PACKAGING"),
    ("G8", "PREVIEW"),
    ("G9", "RENDER_TECHNICAL"),
    ("G10", "HUMAN_APPROVAL"),
    ("G11", "POST_PUBLICATION"),
)
PROMPT_GATE_CODES = tuple(code for code, _ in PROMPT_GATE_ORDER)
PROMPT_GATE_NAMES = dict(PROMPT_GATE_ORDER)
ALLOWED_GATE_STATUSES = {"PASS", "BLOCKED", "DEFERRED", "ADVISORY", "PENDING_MANUAL"}
FINAL_DIMENSIONS = (1080, 1920)
FINAL_FPS = 60
SHORTS_DURATION = (60.0, 75.0)


class PromptComplianceError(ValueError):
    """Raised when a prompt invariant is absent, ambiguous or contradicted."""


def _read(path: Path | None, label: str) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromptComplianceError(f"Could not read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise PromptComplianceError(f"{label} must be a JSON object: {path}")
    return value


def _is_nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _truth_mode(manifest: dict[str, Any]) -> str:
    profile = manifest.get("story_profile") or {}
    story = manifest.get("story_creation") or {}
    truth = story.get("truth") or {}
    return str(profile.get("truth_mode") or truth.get("mode") or "").upper()


def _hook(manifest: dict[str, Any]) -> str:
    profile = manifest.get("story_profile") or {}
    idea = (manifest.get("story_creation") or {}).get("idea") or {}
    return str(
        profile.get("central_question")
        or idea.get("central_question")
        or manifest.get("title")
        or "the unexplained detail"
    ).strip()


def build_packaging(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build three auditable packaging directions before human selection.

    This creates concepts only; it never publishes or silently selects a
    thumbnail asset. The selected direction still requires human approval.
    """
    title = str(manifest.get("title") or "Because Of This").strip()
    hook = _hook(manifest)
    candidates = [
        {
            "candidate_id": "PKG-01",
            "title": f"THE DETAIL THAT CHANGED EVERYTHING",
            "concept": f"Open on the most impossible visual evidence for: {hook}",
            "thumbnail_text": "ONE DETAIL",
            "promise": "The viewer will understand why the overlooked detail mattered.",
            "mystery": "The cause is withheld until the consequence is visible.",
            "spoiler_risk": "LOW",
        },
        {
            "candidate_id": "PKG-02",
            "title": f"WHAT THE CAMERA CAUGHT NEXT",
            "concept": f"Lead with the unanswered question and the final visual recurrence: {hook}",
            "thumbnail_text": "CAUGHT ON CAMERA",
            "promise": "The viewer will follow the evidence to its irreversible turn.",
            "mystery": "The final implication is protected from the title and thumbnail.",
            "spoiler_risk": "LOW",
        },
        {
            "candidate_id": "PKG-03",
            "title": f"NO ONE COULD EXPLAIN THIS",
            "concept": f"Use a restrained investigative frame around the central question: {hook}",
            "thumbnail_text": "NO EXPLANATION",
            "promise": "The viewer will receive a coherent reveal, not an empty cliffhanger.",
            "mystery": "The answer is not disclosed in the packaging.",
            "spoiler_risk": "MEDIUM",
        },
    ]
    fiction = _truth_mode(manifest) in {"DECLARED_FICTION", "FICTION", "ORIGINAL_FICTION"}
    description = (
        "This episode is an original fictional suspense story. Visuals are licensed "
        "representations and are not documentary evidence."
        if fiction
        else "This episode presents source-backed information with the applicable evidence and rights records."
    )
    return {
        "version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_title": title,
        "candidates": candidates,
        "selected_candidate_id": candidates[0]["candidate_id"],
        "selection_status": "PENDING_HUMAN_APPROVAL",
        "description": description,
        "cta": {
            "text": "Follow for the next unexplained story.",
            "placement": "after_consequence_before_or_with_final_logo",
            "before_consequence": False,
        },
        "spoiler_policy": "no_title_or_thumbnail_text may disclose the final consequence",
    }


def validate_packaging(manifest: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    package = manifest.get("packaging")
    if not isinstance(package, dict):
        package = build_packaging(manifest)
    candidates = package.get("candidates")
    errors: list[str] = []
    if not isinstance(candidates, list) or len(candidates) != 3:
        errors.append("packaging must contain exactly three candidates")
        candidates = candidates if isinstance(candidates, list) else []
    required = ("candidate_id", "title", "concept", "thumbnail_text", "promise", "mystery", "spoiler_risk")
    ids: set[str] = set()
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict):
            errors.append(f"packaging candidate {index} is not an object")
            continue
        missing = [key for key in required if not _is_nonempty(candidate.get(key))]
        if missing:
            errors.append(f"packaging candidate {index} missing: {', '.join(missing)}")
        candidate_id = str(candidate.get("candidate_id", ""))
        if candidate_id in ids:
            errors.append(f"duplicate packaging candidate_id: {candidate_id}")
        ids.add(candidate_id)
        if candidate.get("spoiler_risk") not in {"LOW", "MEDIUM", "HIGH"}:
            errors.append(f"packaging candidate {index} has invalid spoiler_risk")
    selected = package.get("selected_candidate_id")
    if selected not in ids:
        errors.append("packaging.selected_candidate_id must identify one of the three candidates")
    cta = package.get("cta") or {}
    if not _is_nonempty(cta.get("text")) or cta.get("before_consequence") is True:
        errors.append("packaging CTA must exist and cannot appear before the consequence")
    description = str(package.get("description", ""))
    if _truth_mode(manifest) in {"DECLARED_FICTION", "FICTION", "ORIGINAL_FICTION"} and "fiction" not in description.lower():
        errors.append("fiction episodes must disclose fiction in the description")
    if strict and package.get("selection_status") not in {"APPROVED", "PENDING_HUMAN_APPROVAL"}:
        errors.append("packaging selection has an invalid approval state")
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "package": package,
        "candidate_count": len(candidates),
    }


def validate_audio(manifest: dict[str, Any], release: dict[str, Any] | None = None, *, strict: bool = False) -> dict[str, Any]:
    music = manifest.get("music") or {}
    errors: list[str] = []
    for key in ("path", "license"):
        if not _is_nonempty(music.get(key)):
            errors.append(f"music.{key} is required")
    if music.get("commercial_use") is not True:
        errors.append("music.commercial_use must be true")
    if music.get("attribution_required") is True and not _is_nonempty(music.get("attribution")):
        errors.append("music.attribution is required when attribution_required=true")
    if strict:
        for key in ("track_id", "source_url", "sha256", "reuse_status", "origin_recorded_at"):
            if not _is_nonempty(music.get(key)):
                errors.append(f"music.{key} is required for final production")
        if music.get("reuse_status") not in {"FRESH", "APPROVED_REUSE"}:
            errors.append("complete music tracks must be fresh or explicitly approved")
        similarity = music.get("similarity_review") or {}
        if similarity.get("status") != "PASS":
            errors.append("music similarity review must be PASS")
        device_tests = music.get("device_tests") or {}
        for device in ("phone", "headphones", "low_volume"):
            if device_tests.get(device) != "PASS":
                errors.append(f"music.device_tests.{device} must be PASS")
        effects = manifest.get("effects") or []
        if not isinstance(effects, list):
            errors.append("effects must be an array")
        for index, effect in enumerate(effects, 1):
            if not isinstance(effect, dict):
                errors.append(f"effects[{index}] must be an object")
                continue
            if effect.get("reuse_status") not in {"FRESH", "APPROVED_REUSE"}:
                errors.append(f"effects[{index}].reuse_status must be explicit")
            if effect.get("cooldown_videos", 0) < 3 and effect.get("reuse_status") == "APPROVED_REUSE":
                errors.append(f"effects[{index}] violates the three-video cooldown")
    if release:
        mix = release.get("audio_mix_profile") or {}
        if mix.get("master") != "narration_locked" or mix.get("music_ducking") != "sidechain_compress":
            errors.append("release audio mix must be narration-locked with sidechain ducking")
        if float(mix.get("music_volume", 1.0)) > 0.20:
            errors.append("music volume exceeds the locked suspense ceiling")
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "narration_priority": "absolute",
        "track_reuse_policy": "complete tracks never reused; reusable SFX require three-video cooldown",
    }


def validate_approval(
    manifest: dict[str, Any],
    release: dict[str, Any] | None = None,
    preview: dict[str, Any] | None = None,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    editorial = manifest.get("editorial_qa") or {}
    errors: list[str] = []
    if strict:
        if editorial.get("status") != "PASS":
            errors.append("editorial_qa.status must be PASS")
        if not _is_nonempty(editorial.get("reviewer")) or not _is_nonempty(editorial.get("reviewed_at")):
            errors.append("human reviewer and reviewed_at are required")
        try:
            if float(editorial.get("score", 0)) < 8:
                errors.append("editorial score must be at least 8/10")
        except (TypeError, ValueError):
            errors.append("editorial score must be numeric")
        incidents = manifest.get("incidents") or []
        critical = [item for item in incidents if isinstance(item, dict) and item.get("severity") == "CRITICAL" and item.get("status") != "resolved"]
        if critical:
            errors.append("unresolved critical incidents block approval")
        package = manifest.get("approval_package") or {}
        required_package = (
            "video", "script", "narration", "music_effects", "captions_karaoke",
            "packaging", "gate_statuses", "rights_origins", "failures_fixed", "final_hash",
        )
        missing = [key for key in required_package if package.get(key) not in {True, "PASS", "PRESENT"}]
        if missing:
            errors.append("approval_package missing: " + ", ".join(missing))
        if preview and preview.get("preview_hash") and release and release.get("output_sha256"):
            if preview["preview_hash"] != release["output_sha256"] and manifest.get("preview_approval", {}).get("approved_final_match") is not True:
                errors.append("final does not match the approved preview")
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "approval_rule": "human approval is valid only with all mandatory gates passed, no critical incident and score >=8",
    }


def validate_dimensions(report: dict[str, Any] | None) -> dict[str, Any]:
    errors: list[str] = []
    if report:
        dimensions = str(report.get("dimensions", ""))
        if dimensions != f"{FINAL_DIMENSIONS[0]}x{FINAL_DIMENSIONS[1]}":
            errors.append(f"dimensions must be {FINAL_DIMENSIONS[0]}x{FINAL_DIMENSIONS[1]}")
        try:
            if abs(float(report.get("fps", 0)) - FINAL_FPS) > 0.01:
                errors.append(f"fps must be {FINAL_FPS}")
        except (TypeError, ValueError):
            errors.append("fps is missing or invalid")
        try:
            duration = float(report.get("duration_seconds", 0))
            if not SHORTS_DURATION[0] <= duration <= SHORTS_DURATION[1]:
                errors.append("duration must be between 60 and 75 seconds")
        except (TypeError, ValueError):
            errors.append("duration is missing or invalid")
    return {"status": "PASS" if not errors else "BLOCKED", "errors": errors}


def validate_post_publication(receipt: dict[str, Any], final_report: dict[str, Any] | None = None) -> dict[str, Any]:
    required = {
        "status": "PASS",
        "platform": None,
        "url": None,
        "file_available": True,
        "duration_ok": True,
        "audio_ok": True,
        "captions_ok": True,
        "framing_ok": True,
        "title_ok": True,
        "thumbnail_ok": True,
        "description_ok": True,
        "comment_ok": True,
    }
    errors: list[str] = []
    for key, expected in required.items():
        if key not in receipt:
            errors.append(f"post-publication receipt missing {key}")
        elif expected is not None and receipt.get(key) != expected:
            errors.append(f"post-publication {key} must be {expected!r}")
        elif expected is None and not _is_nonempty(receipt.get(key)):
            errors.append(f"post-publication {key} is required")
    if not isinstance(receipt.get("divergences", []), list):
        errors.append("post-publication divergences must be an array")
    if receipt.get("divergences"):
        errors.append("post-publication divergences must be empty")
    if final_report and receipt.get("duration_seconds") is not None:
        try:
            if abs(float(receipt["duration_seconds"]) - float(final_report["duration_seconds"])) > 0.15:
                errors.append("published duration diverges from validated release")
        except (KeyError, TypeError, ValueError):
            errors.append("published duration is invalid")
    return {"status": "PASS" if not errors else "BLOCKED", "errors": errors}


def validate_bundle(
    manifest: dict[str, Any],
    *,
    mode: str,
    release: dict[str, Any] | None = None,
    preview: dict[str, Any] | None = None,
    post_publication: dict[str, Any] | None = None,
) -> dict[str, Any]:
    strict = mode == "final"
    reports = {
        "audio": validate_audio(manifest, release, strict=strict),
        "packaging": validate_packaging(manifest, strict=strict),
        "approval": validate_approval(manifest, release, preview, strict=strict),
        "media": validate_dimensions(release),
    }
    if post_publication is not None:
        reports["post_publication"] = validate_post_publication(post_publication, release)
    errors = [f"{name}: {error}" for name, report in reports.items() for error in report.get("errors", [])]
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "mode": mode,
        "errors": errors,
        "reports": reports,
        "prompt_gate_order": [{"code": code, "name": name} for code, name in PROMPT_GATE_ORDER],
    }


def validate_gate_report(report: dict[str, Any]) -> dict[str, Any]:
    gates = report.get("gates")
    if not isinstance(gates, list):
        raise PromptComplianceError("gate report must contain a gates array")
    actual = [(item.get("code"), item.get("name")) for item in gates if isinstance(item, dict)]
    expected = list(PROMPT_GATE_ORDER)
    if actual != expected:
        raise PromptComplianceError(f"gate order/semantics mismatch: expected {expected}, got {actual}")
    return {"status": "PASS", "gate_count": len(gates), "gate_order": list(PROMPT_GATE_ORDER)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--release-report", type=Path)
    parser.add_argument("--post-publication-receipt", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        release = _read(args.release_report, "release report")
        post = _read(args.post_publication_receipt, "post-publication receipt")
        report = validate_bundle(manifest, mode=args.mode, release=release, post_publication=post)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "PASS" else 1
    except (OSError, UnicodeError, json.JSONDecodeError, PromptComplianceError) as exc:
        print(f"PROMPT COMPLIANCE BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
