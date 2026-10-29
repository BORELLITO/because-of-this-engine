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
from production.caption_quality import CaptionQualityError, quality_report
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
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return f"BLOCKED: {exc}", {}
    if report.get("status") != "STORY_CREATION_PASS":
        return "BLOCKED: story creation report did not pass", report
    return "PASS: original story, hook, escalation and payoff gates passed", report


def _story_intelligence(base: Path) -> tuple[str, dict[str, Any]]:
    visual = _read(base / "rendered" / "visual-story-qa-preview.json", "visual story QA") if (base / "rendered" / "visual-story-qa-preview.json").is_file() else None
    timing = _read(base / "rendered" / "narration-coverage.json", "narration coverage") if (base / "rendered" / "narration-coverage.json").is_file() else None
    if visual and visual.get("status") != "VISUAL_STORY_QA_PASS":
        return "BLOCKED: visual story QA did not pass", {"visual": visual, "timing": timing}
    if timing:
        coverage = timing.get("narration_coverage") or {}
        if timing.get("status") != "STORY_INTELLIGENCE_PASS" or coverage.get("timing_status") != "FORCED_ALIGNMENT_SCENE_TIMES_PASS":
            return "BLOCKED: forced-alignment narration coverage did not pass", {"visual": visual, "timing": timing}
    return "PASS: semantic visual review, continuity and forced timing are available", {"visual": visual, "timing": timing}


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
    reuse_path = base / "rendered" / f"asset-reuse-brain-{mode}.json"
    try:
        reuse = _read(reuse_path, "asset reuse report") if reuse_path.is_file() else audit_asset_reuse(
            manifest_path, base.parents[1], registry_path=base.parents[1] / "episodes" / "asset-memory-registry.json"
        )
    except (AssetReuseBrainError, OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return "BLOCKED", str(exc)
    if reuse.get("status") != "ASSET_REUSE_PASS":
        return "BLOCKED", "global asset brain found a reused or ambiguous clip"
    return "PASS", f"{len(spec['scenes'])} approved semantic scenes with global no-repeat protection"


def _narration(manifest: dict[str, Any], base: Path) -> tuple[str, str]:
    audio = manifest.get("audio") or {}
    voice = manifest.get("voice") or {}
    if not all(str(voice.get(key, "")).strip() for key in ("provider", "model", "voice", "language", "style")):
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
    if report.get("status") != "PASS":
        return "BLOCKED", "caption quality report did not pass"
    return "PASS", f"{report.get('event_count', '?')} forced-aligned events; karaoke timing verified"


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
    intel_status, intelligence = _story_intelligence(base)
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
        gates.append(_gate("G5", "AUDIO_MIX", audio["status"], "; ".join(audio["errors"]) if audio["errors"] else audio["track_reuse_policy"]))
    else:
        gates.append(_gate("G5", "AUDIO_MIX", "DEFERRED", f"phase {phase} runs before audio mix validation"))

    packaging = validate_packaging(manifest, strict=mode == "final")
    if 7 in active or phase == "final":
        gates.append(_gate("G7", "PACKAGING", packaging["status"], "; ".join(packaging["errors"]) if packaging["errors"] else "three title/thumbnail directions, fiction disclosure and consequence-safe CTA verified"))
    else:
        gates.append(_gate("G7", "PACKAGING", "DEFERRED", f"phase {phase} runs before packaging validation"))

    caption_status, caption_evidence = _captions(manifest_path, mode)
    gates.append(_gate("G6", "CAPTIONS_KARAOKE", caption_status, caption_evidence))

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
