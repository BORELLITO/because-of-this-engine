#!/usr/bin/env python3
"""Run the fail-closed visual-story and story-intelligence gates for v2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.story_intelligence import StoryIntegrityError, audit_manifest
from production.video_asset_contract import load_manifest
from production.visual_semantics import require_visual_fit, visual_match_report


def _scene_report(scene: dict, mode: str) -> dict:
    scene_id = scene.get("scene_id", "?")
    qa = {
        "scene_id": scene_id,
        "narration_excerpt": scene.get("narration_excerpt"),
        "story_beat": scene.get("story_beat"),
        "visual_match": scene.get("visual_match"),
    }
    try:
        if not str(scene.get("narration_excerpt", "")).strip():
            raise ValueError("narration_excerpt is missing; narration must remain the master context")
        candidate = scene.get("asset")
        if not isinstance(candidate, dict):
            raise ValueError("scene asset is missing")
        result = visual_match_report(scene, candidate, require_review=True)
        qa.update({
            "semantic_score": result.get("score"),
            "coverage": result.get("coverage"),
            "preferred_coverage": result.get("preferred_coverage"),
            "status": result.get("status"),
            "reason": result.get("reason"),
            "missing": result.get("missing"),
            "critical_missing": result.get("critical_missing"),
            "forbidden_hits": result.get("forbidden_hits"),
            "matched": result.get("matched"),
            "reviewed": result.get("reviewed"),
            "evidence_basis": result.get("evidence_basis"),
            "pixel_evidence": result.get("pixel_evidence"),
        })
        if result.get("status") != "PASS":
            return qa
        require_visual_fit(scene, candidate, mode=mode)
    except (ValueError, TypeError, AttributeError) as exc:
        qa.update({
            "status": "BLOCKED",
            "reason": str(exc),
            "semantic_score": 0.0,
            "coverage": 0.0,
            "preferred_coverage": 0.0,
            "missing": {},
            "critical_missing": {},
            "forbidden_hits": [],
            "matched": {},
            "reviewed": False,
            "evidence_basis": "",
            "pixel_evidence": {"status": "BLOCKED", "issues": [str(exc)]},
        })
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
        story_report = None
        story_error = None
        try:
            script_path = (args.manifest.resolve().parent / manifest["script"]["path"]).resolve()
            script_text = script_path.read_text(encoding="utf-8")
            story_report = audit_manifest(manifest, script_text)
        except (OSError, KeyError, TypeError, ValueError, StoryIntegrityError) as exc:
            story_error = str(exc)

        scenes = [_scene_report(scene, args.mode) for scene in manifest.get("scenes", [])]
        blocked = [scene for scene in scenes if scene["status"] != "PASS"]
        status = "VISUAL_STORY_QA_PASS" if story_error is None and not blocked else "VISUAL_STORY_QA_BLOCKED"
        report = {
            "status": status,
            "video_id": manifest.get("video_id"),
            "mode": args.mode,
            "scene_count": len(scenes),
            "blocked_scene_count": len(blocked),
            "story_intelligence": story_report,
            "story_intelligence_error": story_error,
            "scenes": scenes,
            "blocking_scenes": blocked,
            "policy": {
                "story_graph_required": True,
                "narration_coverage_required": True,
                "narration_is_master_context": True,
                "isolated_keyword_matching": False,
                "forbidden_visuals_blocked": True,
                "critical_visual_anchors_blocked": True,
                "reviewed_visual_evidence_required": True,
                "pixel_evidence_required_in_final": True,
                "all_scene_failures_reported": True,
            },
        }
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False))
        return 1 if status != "VISUAL_STORY_QA_PASS" else 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"VISUAL STORY QA BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
