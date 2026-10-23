#!/usr/bin/env python3
"""Fail-closed master-clock and post-render QA gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Direct execution (python production/script.py) places production/ on sys.path.
# Add the repository root explicitly so package imports are stable in CI and locally.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.master_timeline import (
    MasterTimelineError,
    audio_metadata,
    build_timeline,
    read_contract,
    source_fingerprint,
    validate_final_media,
)
from production.validate_authorial_episode import caption_events, ffprobe


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the final master timeline and mux.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        contract_path = (
            args.contract.resolve()
            if args.contract
            else manifest_path.parent / "rendered" / f"master-contract-{args.mode}.json"
        )
        contract = read_contract(contract_path)
        current_sources = source_fingerprint(manifest_path, manifest)
        if current_sources["source_fingerprint"] != contract.get("source_fingerprint"):
            raise MasterTimelineError("Source fingerprint changed after the master contract; stale artifact blocked.")
        audio_path = (manifest_path.parent / manifest["audio"]["path"]).resolve()
        caption_path = (manifest_path.parent / manifest["captions"]["path"]).resolve()
        audio_info = audio_metadata(audio_path)
        events = caption_events(caption_path)
        timeline = build_timeline(manifest_path, manifest, events, audio_info=audio_info)
        output_path = (manifest_path.parent / str(manifest["output"]["path"]).format(mode=args.mode)).resolve()
        if not output_path.is_file():
            raise MasterTimelineError(f"Rendered output is missing: {output_path}")
        media = validate_final_media(
            ffprobe(output_path),
            expected_duration=float(audio_info["duration_seconds"]),
            expected_fps=int(manifest.get("fps", 25)),
        )
        visual_alignment = []
        if manifest.get("require_visual_plan", False):
            allowed_functions = {
                "literal", "contextual", "establishing", "evidence", "emotional",
                "symbolic", "explanatory", "transitional", "reveal", "payoff",
            }
            allowed_matches = {"HIGH_MATCH", "MEDIUM_MATCH"}
            for scene in manifest["scenes"]:
                visual_function = str(scene.get("visual_function", "")).lower()
                visual_match = str(scene.get("visual_match", ""))
                if visual_function not in allowed_functions or visual_match not in allowed_matches:
                    raise MasterTimelineError(
                        f"Visual story gate failed for {scene.get('scene_id', '?')}: "
                        "visual_function/visual_match is missing or unsafe."
                    )
                visual_alignment.append({
                    "scene_id": scene["scene_id"],
                    "visual_function": visual_function,
                    "visual_match": visual_match,
                    "status": "PASS",
                })
        gates = {
            "NARRATION_MASTER_OK": True,
            "TIMEBASE_OK": timeline["timebase"] == f"1/{timeline['fps']}",
            "ALIGNMENT_OK": timeline["alignment_mode"] in {
                "forced_alignment", "hybrid_alignment", "phrase_level_manual_reviewed"
            },
            "ALIGNMENT_DECLARED_HONESTLY": (
                timeline["alignment_mode"] != "phrase_level_manual_reviewed"
                or (
                    timeline["word_level_available"] is False
                    and bool(timeline.get("alignment_source"))
                    and timeline.get("alignment_confidence") == "reviewed_phrase_level"
                )
            ),
            "SCENE_TIMELINE_OK": abs(
                timeline["scene_timeline_duration_seconds"]
                - timeline["audio_duration_seconds"]
            ) <= 0.10,
            "CAPTION_SYNC_OK": timeline["caption_end_gap_seconds"] <= float(
                manifest["captions"].get("end_tolerance_seconds", 0.10)
            ),
            "TIMELINE_CONSISTENCY_OK": abs(
                media["audio_duration_seconds"] - timeline["audio_duration_seconds"]
            ) <= 0.10,
            "POST_RENDER_SYNC_OK": media["post_render_sync"] == "PASS",
            "IMAGE_STORY_MATCH_OK": bool(visual_alignment) if manifest.get("require_visual_plan", False) else True,
        }
        if not all(gates.values()):
            raise MasterTimelineError("One or more critical master gates failed.")
        report = {
            "status": "MASTER_TIMELINE_VALIDATED",
            "video_id": manifest["video_id"],
            "mode": args.mode,
            "narration_master_id": contract["narration_master_id"],
            "source_fingerprint": current_sources["source_fingerprint"],
            "critical_gates": gates,
            "timeline": timeline,
            "media": media,
            "visual_alignment": visual_alignment,
            "stale_artifact_check": "PASS",
            "full_watch_required": True,
        }
        report_path = args.report.resolve() if args.report else manifest_path.parent / "rendered" / f"master-timeline-{args.mode}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report["status"],
            "video_id": report["video_id"],
            "mode": args.mode,
            "audio_duration_seconds": timeline["audio_duration_seconds"],
            "caption_count": timeline["caption_count"],
            "alignment_mode": timeline["alignment_mode"],
            "post_render_sync": media["post_render_sync"],
            "stale_artifact_check": report["stale_artifact_check"],
            "scene_timeline": "PASS" if gates["SCENE_TIMELINE_OK"] else "FAIL",
            "alignment_honesty": "PASS" if gates["ALIGNMENT_DECLARED_HONESTLY"] else "FAIL",
            "report": str(report_path),
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, KeyError, json.JSONDecodeError, MasterTimelineError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
