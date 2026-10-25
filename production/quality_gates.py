#!/usr/bin/env python3
"""Canonical G0–G12 gate report for Because of This Engine v2."""
from __future__ import annotations
import argparse
import json
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

# Allow the workflow to execute this file directly from the repository root.
if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.caption_quality import CaptionQualityError, audio_duration, quality_report
from production.video_asset_contract import VideoContractError, load_manifest, validate_manifest

GATES = tuple((f"G{i}", name) for i, name in enumerate((
    "CONFIG", "RESEARCH", "SCRIPT", "VOICE", "ASSETS", "PROVENANCE",
    "TIMELINE", "CAPTIONS", "RENDER", "TECHNICAL", "EDITORIAL",
    "DELIVERY", "CLEANUP")))
ACTIVE_BY_PHASE = {"pre-render": set(range(8)), "post-render": set(range(11)), "final": set(range(13))}

def _read(path: Path | None, label: str) -> dict[str, Any] | None:
    if path is None: return None
    try: value = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise RuntimeError(f"Could not read {label}: {path}") from exc
    if not isinstance(value, dict): raise RuntimeError(f"{label} must be a JSON object: {path}")
    return value

def _inside(base: Path, value: str, label: str) -> Path:
    if not isinstance(value, str) or not value.strip(): raise RuntimeError(f"{label} path is missing.")
    path = (base / value).resolve()
    if path != base and base not in path.parents: raise RuntimeError(f"{label} escapes the episode directory.")
    return path

def _gate(code: str, name: str, status: str, evidence: str) -> dict[str, str]:
    return {"code": code, "name": name, "status": status, "evidence": evidence}

def _story_intelligence(m: dict[str, Any], base: Path, mode: str) -> tuple[str, str, dict[str, Any]]:
    visual_path = base / "rendered" / f"visual-story-qa-{mode}.json"
    timing_path = base / "rendered" / "narration-coverage.json"
    try:
        visual = _read(visual_path, "visual story QA")
        timing = _read(timing_path, "narration coverage")
        if visual.get("status") != "VISUAL_STORY_QA_PASS":
            return "BLOCKED", "visual story QA is not PASS", {
                "visual_story_qa": visual,
                "narration_coverage": timing,
            }
        story = visual.get("story_intelligence") or {}
        if story.get("status") != "STORY_INTELLIGENCE_PASS":
            return "BLOCKED", "story intelligence is not PASS", {
                "visual_story_qa": visual,
                "narration_coverage": timing,
            }
        coverage = timing.get("narration_coverage") or {}
        if timing.get("status") != "STORY_INTELLIGENCE_PASS":
            return "BLOCKED", "forced-alignment narration coverage is not PASS", {
                "visual_story_qa": visual,
                "narration_coverage": timing,
            }
        if coverage.get("timing_status") != "FORCED_ALIGNMENT_SCENE_TIMES_PASS":
            return "BLOCKED", "scene timing is not forced-alignment verified", {
                "visual_story_qa": visual,
                "narration_coverage": timing,
            }
        return "PASS", (
            f"story graph, sequence continuity and {coverage.get('scene_count', '?')} "
            "forced-aligned scene spans verified"
        ), {
            "visual_story_qa": visual,
            "narration_coverage": timing,
        }
    except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return "BLOCKED", str(exc), {}



def _research(m: dict[str, Any], mode: str) -> tuple[str, str]:
    value = m.get("research")
    if not isinstance(value, dict) or not isinstance(value.get("sources"), list) or not value["sources"]:
        return "BLOCKED", "research.sources is missing or empty"
    if not str(value.get("accessed_at", "")).strip(): return "BLOCKED", "research.accessed_at is missing"
    confidence = value.get("confidence")
    if mode == "final" and confidence not in {"HIGH", "MEDIUM"}:
        return "BLOCKED", "final mode requires research confidence HIGH or MEDIUM"
    return "PASS", f"{len(value['sources'])} source record(s), confidence={confidence}"

def _script(m: dict[str, Any], base: Path) -> tuple[str, str]:
    try:
        path = _inside(base, m["script"]["path"], "Script")
        words = len(path.read_text(encoding="utf-8").split())
    except (KeyError, OSError, UnicodeError, RuntimeError) as exc: return "BLOCKED", str(exc)
    if words < 1: return "BLOCKED", "canonical script is empty"
    profile = m.get("story_profile")
    missing = [k for k in ("primary_emotion", "central_question", "visual_symbol")
               if not isinstance(profile, dict) or not str(profile.get(k, "")).strip()]
    if missing: return "BLOCKED", f"story_profile missing: {', '.join(missing)}"
    return "PASS", f"{words} script words and complete story profile"

def _voice(m: dict[str, Any], base: Path) -> tuple[str, str, float | None]:
    try:
        audio_path = _inside(base, m["audio"]["path"], "Narration")
        duration = audio_duration(audio_path)
        profile = m.get("voice")
        if not isinstance(profile, dict):
            return "BLOCKED", "manifest.voice is required as the canonical voice profile", duration
        required = ("provider", "model", "voice", "language", "style")
        missing = [key for key in required if not str(profile.get(key, "")).strip()]
        if missing:
            return "BLOCKED", "manifest.voice missing: " + ", ".join(missing), duration
        metadata_path = audio_path.with_name(audio_path.name + ".json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if "gemini" not in str(metadata.get("provider", "")).lower():
            return "BLOCKED", "narration sidecar provider is not Gemini", duration
        for key in ("model", "voice", "language", "style"):
            if metadata.get(key) != profile.get(key):
                return "BLOCKED", f"voice sidecar {key} does not match manifest.voice", duration
    except (KeyError, OSError, UnicodeError, ValueError, TypeError, wave.Error,
            CaptionQualityError, json.JSONDecodeError, RuntimeError) as exc:
        return "BLOCKED", str(exc), None
    if not 60 <= duration <= 75:
        return "BLOCKED", f"narration duration {duration:.3f}s is outside 60–75s", duration
    return "PASS", f"measured narration {duration:.3f}s; voice profile and sidecar agree", duration

def _assets(m: dict[str, Any], base: Path, mode: str) -> tuple[str, str]:
    try: spec = validate_manifest(m, base, mode=mode, check_files=True)
    except (VideoContractError, OSError, ValueError) as exc: return "BLOCKED", str(exc)
    return "PASS", f"{len(spec['scenes'])} unique approved video scene(s)"

def _provenance(m: dict[str, Any], mode: str) -> tuple[str, str]:
    required = ("source_page_url", "license", "sha256", "rights_status", "approved_for_render")
    missing: list[str] = []
    for scene in m.get("scenes", []):
        asset = scene.get("asset") or {}
        for key in required:
            if not asset.get(key): missing.append(f"{scene.get('scene_id', '?')}.{key}")
        if not asset.get("drive_file_id"): missing.append(f"{scene.get('scene_id', '?')}.drive_file_id")
        if mode == "final":
            for key in ("author", "acquisition_timestamp", "original_filename", "mime_type",
                        "duration_seconds", "width", "height", "filesize_bytes", "job_ownership", "scene_usage"):
                if asset.get(key) in (None, ""): missing.append(f"{scene.get('scene_id', '?')}.{key}")
    return ("BLOCKED", "missing provenance: " + ", ".join(missing[:8])) if missing else (
        "PASS", f"{len(m.get('scenes', []))} asset provenance records complete")

def _timeline(m: dict[str, Any], duration: float | None) -> tuple[str, str]:
    total = sum(float(scene.get("duration", 0)) for scene in m.get("scenes", []))
    if not 60 <= total <= 75: return "BLOCKED", f"planned scene sum {total:.3f}s is outside 60–75s"
    if duration is None or not 60 <= duration <= 75: return "BLOCKED", "measured narration duration is unavailable or outside 60–75s"
    return "PASS", f"planned {total:.3f}s; measured master clock {duration:.3f}s"

def _output(m: dict[str, Any], base: Path, mode: str) -> Path:
    template = str(m.get("output", {}).get("path", "rendered/{video_id}-{mode}.mp4"))
    return (base / template.format(video_id=m["video_id"], mode=mode)).resolve()

def evaluate(manifest_path: Path, mode: str, phase: str, *, release_report_path: Path | None = None,
             delivery_receipt_path: Path | None = None, final_manifest_path: Path | None = None,
             cleanup_receipt_path: Path | None = None) -> dict[str, Any]:
    if phase not in ACTIVE_BY_PHASE: raise RuntimeError(f"Unknown gate phase: {phase}")
    manifest_path = manifest_path.resolve()
    base, manifest = manifest_path.parent, load_manifest(manifest_path)
    active = ACTIVE_BY_PHASE[phase]
    results: list[dict[str, str]] = []
    config_ok = (manifest.get("schema_version") == "2.0" and str(manifest.get("video_id", "")).strip()
                 and str(manifest.get("job_id") or (manifest.get("job") or {}).get("job_id") or "").strip()
                 and manifest.get("fps") == 25)
    results.append(_gate("G0", "CONFIG", "PASS" if config_ok else "BLOCKED",
        "schema 2.0, stable job_id and 25 fps" if config_ok else "schema 2.0, video_id, stable job_id and fps=25 are required"))
    status, evidence = _research(manifest, mode); results.append(_gate("G1", "RESEARCH", status, evidence))
    status, evidence = _script(manifest, base); results.append(_gate("G2", "SCRIPT", status, evidence))
    status, evidence, story_integrity = _story_intelligence(manifest, base, mode)
    results.append(_gate("S0", "STORY_INTELLIGENCE", status, evidence))
    results.append(_gate(
        "S1",
        "SEQUENCE_CONTINUITY",
        "PASS" if status == "PASS" else "BLOCKED",
        "story graph entity continuity and final motif recall verified"
        if status == "PASS" else "sequence continuity depends on STORY_INTELLIGENCE",
    ))
    results.append(_gate(
        "S2",
        "NARRATION_COVERAGE",
        "PASS" if status == "PASS" else "BLOCKED",
        "canonical script covered once in scene order with forced-aligned timing"
        if status == "PASS" else "narration coverage/timing depends on STORY_INTELLIGENCE",
    ))
    status, evidence, duration = _voice(manifest, base); results.append(_gate("G3", "VOICE", status, evidence))
    release = _read(release_report_path, "release report")
    final_manifest = _read(final_manifest_path, "final manifest")
    if phase == "final" and release and release.get("status") == "VIDEO_RELEASE_VALIDATED":
        status, evidence = "PASS", f"release report confirms {release.get('clip_count', '?')} validated scene(s)"
    else: status, evidence = _assets(manifest, base, mode)
    results.append(_gate("G4", "ASSETS", status, evidence))
    status, evidence = _provenance(manifest, mode); results.append(_gate("G5", "PROVENANCE", status, evidence))
    status, evidence = _timeline(manifest, duration); results.append(_gate("G6", "TIMELINE", status, evidence))
    try:
        captions = quality_report(manifest_path, require_word_level=mode == "final")
        status, evidence = "PASS", f"{captions['event_count']} events; {captions['timing_claim']}"
    except (CaptionQualityError, OSError, ValueError, json.JSONDecodeError) as exc: status, evidence = "BLOCKED", str(exc)
    results.append(_gate("G7", "CAPTIONS", status, evidence))
    output = _output(manifest, base, mode)
    if 8 in active:
        if release and release.get("status") == "VIDEO_RELEASE_VALIDATED":
            results.append(_gate("G8", "RENDER", "PASS", f"validated output: {release.get('output', output)}"))
        elif output.is_file() and output.stat().st_size > 0:
            results.append(_gate("G8", "RENDER", "PASS", f"output exists: {output}"))
        else: results.append(_gate("G8", "RENDER", "BLOCKED", "validated rendered output is missing"))
    else: results.append(_gate("G8", "RENDER", "DEFERRED", f"phase {phase} runs before render"))
    if 9 in active:
        if not release or release.get("status") != "VIDEO_RELEASE_VALIDATED":
            results.append(_gate("G9", "TECHNICAL", "BLOCKED", "validated release report is missing"))
        elif release.get("technical_qa") != "PASS" or release.get("anomaly_gate") not in {"PASS", "ADVISORY"}:
            results.append(_gate("G9", "TECHNICAL", "BLOCKED", "technical or anomaly QA did not pass"))
        else: results.append(_gate("G9", "TECHNICAL", "PASS", f"technical_qa={release.get('technical_qa')}; anomaly_gate={release.get('anomaly_gate')}"))
    else: results.append(_gate("G9", "TECHNICAL", "DEFERRED", f"phase {phase} runs before release QA"))
    editorial = manifest.get("editorial_qa") or {}
    if 10 in active:
        if mode == "final" and editorial.get("status") != "PASS":
            results.append(_gate("G10", "EDITORIAL", "BLOCKED", "final mode requires editorial_qa.status=PASS"))
        elif editorial.get("status") == "PASS": results.append(_gate("G10", "EDITORIAL", "PASS", "human editorial review is recorded"))
        else: results.append(_gate("G10", "EDITORIAL", "ADVISORY", "preview remains explicitly non-final"))
    else: results.append(_gate("G10", "EDITORIAL", "DEFERRED", f"phase {phase} runs before editorial release gate"))
    delivery = _read(delivery_receipt_path, "delivery receipt")
    if 11 in active:
        if delivery and delivery.get("status") == "DRIVE_VERIFIED":
            results.append(_gate("G11", "DELIVERY", "PASS", f"Drive folder {delivery.get('delivery_folder_id', 'verified')}"))
        else: results.append(_gate("G11", "DELIVERY", "BLOCKED", "DRIVE_VERIFIED receipt is missing"))
    else: results.append(_gate("G11", "DELIVERY", "DEFERRED", f"phase {phase} runs before Drive delivery"))
    cleanup = _read(cleanup_receipt_path, "cleanup receipt")
    if 12 in active:
        expected_completion = "PRODUCTION_COMPLETE" if mode == "final" else "PREVIEW_COMPLETE"
        complete = final_manifest and final_manifest.get("status") == expected_completion
        verified_cleanup = cleanup and cleanup.get("status") == "DRIVE_VERIFIED"
        if complete and verified_cleanup:
            status = "PASS" if mode == "final" else "ADVISORY"
            evidence = (
                "final manifest complete after verified cleanup"
                if mode == "final"
                else "preview cleanup verified; preview is never a production publication"
            )
            results.append(_gate("G12", "CLEANUP", status, evidence))
        else:
            results.append(_gate(
                "G12", "CLEANUP", "BLOCKED",
                f"{expected_completion} and a verified cleanup receipt are required"
            ))
    else: results.append(_gate("G12", "CLEANUP", "DEFERRED", f"phase {phase} runs before cleanup"))
    blocking = [item for item in results if item["status"] == "BLOCKED"]
    return {"status": "GATES_BLOCKED" if blocking else ("GATES_PASS" if phase == "final" else "GATES_PHASE_PASS"),
        "phase": phase, "job_id": manifest.get("job_id") or (manifest.get("job") or {}).get("job_id"),
        "video_id": manifest.get("video_id"), "mode": mode, "gates": results,
        "story_integrity": story_integrity,
        "blocking_gates": [item["code"] for item in blocking],
        "generated_at_utc": datetime.now(timezone.utc).isoformat()}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), required=True)
    parser.add_argument("--phase", choices=tuple(ACTIVE_BY_PHASE), required=True)
    parser.add_argument("--release-report", type=Path)
    parser.add_argument("--delivery-receipt", type=Path)
    parser.add_argument("--final-manifest", type=Path)
    parser.add_argument("--cleanup-receipt", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate(args.manifest, args.mode, args.phase, release_report_path=args.release_report,
                          delivery_receipt_path=args.delivery_receipt, final_manifest_path=args.final_manifest,
                          cleanup_receipt_path=args.cleanup_receipt)
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["status"] != "GATES_BLOCKED" else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"QUALITY GATES BLOCKED: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
