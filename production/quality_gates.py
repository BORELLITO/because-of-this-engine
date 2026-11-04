#!/usr/bin/env python3
"""Canonical executable G0-G11 gates from the V6 master prompt."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.asset_reuse_brain import AssetReuseBrainError, audit as audit_asset_reuse
from production.audio_reuse_brain import AudioReuseError, audit as audit_audio_reuse
from production.caption_quality import CaptionQualityError, quality_report
from audits.mobile_caption_ui_v11 import MobileUIReviewError, inspect as inspect_mobile_caption_ui
from production.canonical_config import CanonicalConfigError, validate_canonical_manifest
from production.prompt_compliance import (
    PROMPT_GATE_ORDER,
    validate_approval,
    validate_audio,
    validate_dimensions,
    validate_packaging,
)
from production.story_creation import audit_story_creation
from production.video_asset_contract import VideoContractError, load_manifest, validate_manifest

GATES = PROMPT_GATE_ORDER
ACTIVE_BY_PHASE = {
    "pre-render": set(range(8)),
    "post-render": set(range(10)),
    "final": set(range(12)),
}


def _read(path: Path | None, label: str) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be an object: {path}")
    return value


def _gate(code: str, name: str, status: str, evidence: str) -> dict[str, str]:
    return {"code": code, "name": name, "status": status, "evidence": evidence}


def _story_creation(manifest: dict[str, Any], base: Path, mode: str) -> tuple[str, dict[str, Any]]:
    path = base / "rendered" / f"story-creation-{mode}.json"
    try:
        report = _read(path, "story creation report") if path.is_file() else audit_story_creation(manifest)
        # A cached report is reusable only when it contains the current editorial
        # layer. Older C0-C11 reports must be re-audited and cannot bypass E0-E10.
        if (
            path.is_file()
            and (
                report.get("schema_version") != "1.1"
                or not isinstance(report.get("editorial_story"), dict)
                or report.get("editorial_story", {}).get("schema_version") != "7.4"
            )
        ):
            report = audit_story_creation(manifest)
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return f"BLOCKED: {exc}", {}
    if report.get("status") != "STORY_CREATION_PASS":
        return "BLOCKED: story creation report did not pass", report
    return "PASS: original story, hook, escalation and payoff gates passed", report


def _story_intelligence(base: Path, mode: str = "final") -> tuple[str, dict[str, Any]]:
    visual = None
    # Never accept a draft report as evidence for a final release.
    candidates = (
        ("visual-story-qa-final.json",)
        if mode == "final" else
        ("visual-story-qa-preview.json", "visual-story-qa-draft-preview.json", "visual-story-qa-production.json")
    )
    for name in candidates:
        candidate = base / "rendered" / name
        if candidate.is_file():
            visual = _read(candidate, "visual story QA")
            break
    timing = _read(base / "rendered" / "narration-coverage.json", "narration coverage") if (base / "rendered" / "narration-coverage.json").is_file() else None
    evidence = {"visual": visual, "timing": timing}
    # Missing reports must never be promoted to PASS merely because the
    # optional pre-existing files were not found. The previous implementation
    # silently passed precisely this case, masking absent QA.
    if visual is None:
        return "BLOCKED: visual story QA report is missing", evidence
    if visual.get("status") != "VISUAL_STORY_QA_PASS":
        return "BLOCKED: visual story QA did not pass", evidence
    if timing is None:
        return "BLOCKED: narration coverage report is missing", evidence
    coverage = timing.get("narration_coverage") or {}
    if timing.get("status") != "STORY_INTELLIGENCE_PASS" or coverage.get("timing_status") != "FORCED_ALIGNMENT_SCENE_TIMES_PASS":
        return "BLOCKED: forced-alignment narration coverage did not pass", evidence
    return "PASS: semantic visual review, continuity and forced timing verified", evidence


def _provenance(manifest: dict[str, Any], mode: str) -> tuple[str, str]:
    truth = (manifest.get("story_profile") or {}).get("truth_mode") or (manifest.get("story_creation") or {}).get("truth", {}).get("mode")
    errors: list[str] = []
    if not str(truth or "").strip():
        errors.append("truth_mode is missing")
    story_truth = (manifest.get("story_creation") or {}).get("truth") or {}
    if not str(story_truth.get("disclosure") or "").strip():
        errors.append("story truth disclosure is missing")
    required = ("source_page_url", "license", "sha256", "rights_status", "approved_for_render", "drive_file_id")
    for scene in manifest.get("scenes", []):
        asset = scene.get("asset") or {}
        for key in required:
            if not asset.get(key):
                errors.append(f"{scene.get('scene_id', '?')}.{key}")
        if mode == "final":
            if asset.get("rights_status") != "APPROVED" or asset.get("approved_for_render") is not True:
                errors.append(f"{scene.get('scene_id', '?')}.approved_rights")
            for key in ("author", "acquisition_timestamp", "original_filename", "mime_type", "duration_seconds", "width", "height", "filesize_bytes", "job_ownership", "scene_usage"):
                if asset.get(key) in (None, ""):
                    errors.append(f"{scene.get('scene_id', '?')}.{key}")
    return ("BLOCKED: missing rights/originality evidence: " + ", ".join(errors[:10]), "") if errors else (
        "PASS: rights, provenance, declared truth mode and originality evidence are complete", ""
    )


def _visual(manifest_path: Path, base: Path, mode: str) -> tuple[str, str]:
    try:
        spec = validate_manifest(manifest_path, base, mode=mode, check_files=True, enforce_canonical=True)
    except (VideoContractError, OSError, ValueError) as exc:
        return "BLOCKED", str(exc)
    # Cached JSON is diagnostic history, not live proof of a clean source.
    # Re-evaluate against the current manifest, every episode snapshot and the
    # registry on every gate execution. Otherwise a stale PASS can be replayed
    # after the source or asset ledger changes.
    try:
        reuse = audit_asset_reuse(
            manifest_path, base.parents[1],
            registry_path=base.parents[1] / "episodes" / "asset-memory-registry.json",
        )
    except (AssetReuseBrainError, OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return "BLOCKED", str(exc)
    if reuse.get("status") != "ASSET_REUSE_PASS":
        return "BLOCKED", f"fresh source-ledger audit failed: {reuse.get('reason', 'ambiguous or reused clip')}"
    return "PASS", (
        f"{len(spec['scenes'])} approved semantic scenes; fresh ledger scan of "
        f"{reuse.get('scanned_manifest_count', '?')} manifests / "
        f"{reuse.get('registry_asset_count', '?')} registered assets; "
        "historical Git refs and external Drive sources still need independent audit"
    )


def _narration(manifest: dict[str, Any], base: Path) -> tuple[str, str]:
    audio = manifest.get("audio") or {}
    voice = manifest.get("voice") or {}
    # Match the actual 7.4 canonical voice contract, not retired V6 field names.
    if not all(str(voice.get(key, "")).strip() for key in (
        "provider", "model_or_voice_type", "voice_name", "language_code", "style"
    )):
        return "BLOCKED", "canonical narration profile is incomplete"
    path = base / str(audio.get("path", ""))
    if not path.is_file():
        return "BLOCKED", "final narration WAV is missing"
    return "PASS", "canonical voice profile and final narration artifact are present"


def _captions(manifest_path: Path, mode: str) -> tuple[str, str]:
    try:
        report = quality_report(manifest_path, require_word_level=mode == "final")
    except (CaptionQualityError, OSError, ValueError, json.JSONDecodeError) as exc:
        return "BLOCKED", str(exc)
    if report.get("status") != "CAPTION_QA_PASS":
        return "BLOCKED", "caption quality report did not pass"
    return "PASS", f"{report.get('event_count', '?')} forced-aligned events; karaoke timing verified"


def _captions_with_platform_ui(manifest_path: Path, mode: str, phase: str) -> tuple[str, str]:
    caption_status, caption_evidence = _captions(manifest_path, mode)
    if phase != "final":
        return caption_status, caption_evidence
    # Real interface evidence is separate from ASS validity. Never trust
    # a static margin or ASS-file declaration as device-side approval.
    try:
        ui_review = inspect_mobile_caption_ui(manifest_path)
    except (MobileUIReviewError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return "BLOCKED", caption_evidence + f"; mobile UI review could not be validated: {exc}"
    if ui_review.get("status") != "UI_EVIDENCE_ATTESTED":
        return "BLOCKED", caption_evidence + "; TikTok/YouTube mobile evidence pending: " + ", ".join(
            ui_review.get("issues") or ["manual UI review missing"]
        )
    return caption_status, caption_evidence + "; independent platform screenshots and reviewed render/caption SHA binding checked"


def _audio_history(manifest_path: Path, mode: str) -> tuple[str, str]:
    """Fresh global audio history check: never trust a cached PASS file."""
    try:
        report = audit_audio_reuse(
            manifest_path, manifest_path.parent.parents[1],
            strict=mode == "final",
        )
    except (AudioReuseError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return "BLOCKED", f"audio memory unavailable or malformed: {exc}"
    if report.get("status") != "PASS":
        return "BLOCKED", "; ".join(report.get("errors") or ["global audio history blocked"])
    return "PASS", (
        f"audio ledger freshly checked across {report.get('scanned_manifest_count')} "
        f"manifest snapshots; {report.get('ledger_track_count')} tracks registered; "
        "rights/actual listening remain independent gates"
    )


def _output(manifest: dict[str, Any], base: Path, mode: str) -> Path:
    template = str((manifest.get("output") or {}).get("path", "rendered/{video_id}-{mode}.mp4"))
    return (base / template.format(video_id=manifest["video_id"], mode=mode)).resolve()


def evaluate(
    manifest_path: Path,
    mode: str,
    phase: str,
    *,
    release_report_path: Path | None = None,
    delivery_receipt_path: Path | None = None,
    final_manifest_path: Path | None = None,
    cleanup_receipt_path: Path | None = None,
    post_publication_receipt_path: Path | None = None,
) -> dict[str, Any]:
    if phase not in ACTIVE_BY_PHASE:
        raise RuntimeError(f"Unknown gate phase: {phase}")
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = load_manifest(manifest_path)
    active = ACTIVE_BY_PHASE[phase]
    release = _read(release_report_path, "release report")
    final_manifest = _read(final_manifest_path, "final manifest")
    post = _read(post_publication_receipt_path, "post-publication receipt")
    gates: list[dict[str, str]] = []

    try:
        canonical = validate_canonical_manifest(manifest, source_label=str(manifest_path))
        g0_status, g0_evidence = "PASS", f"locked profile {canonical['profile_id']} and V6 contract"
    except (CanonicalConfigError, TypeError, ValueError) as exc:
        g0_status, g0_evidence = "BLOCKED", str(exc)
    gates.append(_gate("G0", "PRE_FLIGHT", g0_status, g0_evidence))

    creation_status, creation = _story_creation(manifest, base, mode)
    intel_status, intelligence = _story_intelligence(base, mode)
    g1_status = "PASS" if creation_status.startswith("PASS") else "BLOCKED"
    gates.append(_gate("G1", "SCRIPT_SUSPENSE", g1_status, creation_status + "; central question, consequence and suspense arc required"))
    g2_status, g2_evidence = _provenance(manifest, mode)
    gates.append(_gate("G2", "RIGHTS_ORIGINALITY_FICTION", "PASS" if g2_status == "PASS" else "BLOCKED", g2_evidence))
    g3_status, g3_evidence = _visual(manifest_path, base, mode)
    if intel_status.startswith("BLOCKED"):
        g3_status, g3_evidence = "BLOCKED", intel_status
    gates.append(_gate("G3", "VISUAL_CLIPS", g3_status, g3_evidence))
    g4_status, g4_evidence = _narration(manifest, base)
    gates.append(_gate("G4", "NARRATION", g4_status, g4_evidence))

    from production.prompt_compliance import validate_audio
    if 5 in active or release:
        audio = validate_audio(manifest, release, strict=mode == "final")
        memory_status, memory_evidence = _audio_history(manifest_path, mode)
        audio_status = "PASS" if audio["status"] == "PASS" and memory_status == "PASS" else "BLOCKED"
        audio_evidence = "; ".join(audio["errors"]) if audio["errors"] else audio["track_reuse_policy"]
        gates.append(_gate("G5", "AUDIO_MIX", audio_status, audio_evidence + "; " + memory_evidence))
    else:
        gates.append(_gate("G5", "AUDIO_MIX", "DEFERRED", f"phase {phase} runs before audio mix validation"))

    packaging = validate_packaging(manifest, strict=mode == "final")

    caption_status, caption_evidence = _captions_with_platform_ui(manifest_path, mode, phase)
    gates.append(_gate("G6", "CAPTIONS_KARAOKE", caption_status, caption_evidence))
    if 7 in active or phase == "final":
        gates.append(_gate("G7", "PACKAGING", packaging["status"], "; ".join(packaging["errors"]) if packaging["errors"] else "three title/thumbnail directions, fiction disclosure and consequence-safe CTA verified"))
    else:
        gates.append(_gate("G7", "PACKAGING", "DEFERRED", f"phase {phase} runs before packaging validation"))

    if 8 in active:
        if release and release.get("status") == "VIDEO_RELEASE_VALIDATED":
            if mode == "final" and (manifest.get("preview_approval") or {}).get("status") != "PASS":
                g8_status, g8_evidence = "BLOCKED", "final mode requires an approved preview record"
            else:
                g8_status, g8_evidence = "PASS", "rendered preview/final preserves the approved fixed HUD, logo, karaoke and outro"
        else:
            g8_status, g8_evidence = "BLOCKED", "validated release report is missing"
    else:
        g8_status, g8_evidence = "DEFERRED", f"phase {phase} runs before preview/render"
    gates.append(_gate("G8", "PREVIEW", g8_status, g8_evidence))

    if 9 in active:
        dims = validate_dimensions(release)
        g9_status = "PASS" if release and release.get("technical_qa") == "PASS" and dims["status"] == "PASS" else "BLOCKED"
        g9_evidence = "; ".join(dims["errors"]) if dims["errors"] else f"{release.get('dimensions') if release else 'missing'} at {release.get('fps') if release else 'missing'} fps; anomaly and technical QA required"
    else:
        g9_status, g9_evidence = "DEFERRED", f"phase {phase} runs before render QA"
    gates.append(_gate("G9", "RENDER_TECHNICAL", g9_status, g9_evidence))

    if 10 in active:
        approval = validate_approval(manifest, release, strict=mode == "final")
        gates.append(_gate("G10", "HUMAN_APPROVAL", approval["status"], "; ".join(approval["errors"]) if approval["errors"] else "human approval package, score, reviewer and incident status verified"))
    else:
        gates.append(_gate("G10", "HUMAN_APPROVAL", "DEFERRED", f"phase {phase} runs before human approval"))

    if 11 in active:
        if post:
            from production.prompt_compliance import validate_post_publication
            post_report = validate_post_publication(post, release)
            g11_status = post_report["status"]
            g11_evidence = "; ".join(post_report["errors"]) if post_report["errors"] else f"manual publication verified on {post.get('platform')}"
        else:
            g11_status, g11_evidence = "DEFERRED", "publication is manual; submit a post-publication receipt to close G11"
    else:
        g11_status, g11_evidence = "DEFERRED", f"phase {phase} runs before post-publication verification"
    gates.append(_gate("G11", "POST_PUBLICATION", g11_status, g11_evidence))

    blocking = [gate for gate in gates if gate["status"] == "BLOCKED"]
    return {
        "status": "GATES_BLOCKED" if blocking else "GATES_PASS",
        "phase": phase,
        "job_id": manifest.get("job_id") or (manifest.get("job") or {}).get("job_id"),
        "video_id": manifest.get("video_id"),
        "mode": mode,
        "gates": gates,
        "story_creation": creation,
        "story_intelligence": intelligence,
        "release": release,
        "final_manifest": final_manifest,
        "delivery": _read(delivery_receipt_path, "delivery receipt"),
        "cleanup": _read(cleanup_receipt_path, "cleanup receipt"),
        "next_action": "MANUAL_PUBLICATION_AND_G11_RECEIPT" if not post else "COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), required=True)
    parser.add_argument("--phase", choices=tuple(ACTIVE_BY_PHASE), required=True)
    parser.add_argument("--release-report", type=Path)
    parser.add_argument("--delivery-receipt", type=Path)
    parser.add_argument("--final-manifest", type=Path)
    parser.add_argument("--cleanup-receipt", type=Path)
    parser.add_argument("--post-publication-receipt", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate(
            args.manifest,
            args.mode,
            args.phase,
            release_report_path=args.release_report,
            delivery_receipt_path=args.delivery_receipt,
            final_manifest_path=args.final_manifest,
            cleanup_receipt_path=args.cleanup_receipt,
            post_publication_receipt_path=args.post_publication_receipt,
        )
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["status"] == "GATES_PASS" else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"QUALITY GATES BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
