#!/usr/bin/env python3
"""Run the fail-closed visual-story gate for a v2 episode.

This gate is deliberately diagnostic as well as blocking: it audits every
scene and writes all incompatible beats to one report, instead of hiding the
remaining failures behind the first bad scene.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.video_asset_contract import load_manifest
from production.visual_semantics import require_visual_fit


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
        result = require_visual_fit(scene, candidate, mode=mode)
        qa.update({
            "semantic_score": result.get("score"),
            "coverage": result.get("coverage"),
            "preferred_coverage": result.get("preferred_coverage"),
            "status": result.get("status"),
            "reason": result.get("reason"),
            "missing": result.get("missing"),
            "forbidden_hits": result.get("forbidden_hits"),
            "matched": result.get("matched"),
        })
    except (ValueError, TypeError, AttributeError) as exc:
        qa.update({
            "status": "BLOCKED",
            "reason": str(exc),
            "semantic_score": 0.0,
            "coverage": 0.0,
            "preferred_coverage": 0.0,
            "missing": {},
            "forbidden_hits": [],
            "matched": {},
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
        scenes = [_scene_report(scene, args.mode) for scene in manifest.get("scenes", [])]
        blocked = [scene for scene in scenes if scene["status"] != "PASS"]
        report = {
            "status": "VISUAL_STORY_QA_PASS" if not blocked else "VISUAL_STORY_QA_BLOCKED",
            "video_id": manifest.get("video_id"),
            "mode": args.mode,
            "scene_count": len(scenes),
            "blocked_scene_count": len(blocked),
            "scenes": scenes,
            "blocking_scenes": blocked,
            "policy": {
                "narration_is_master_context": True,
                "isolated_keyword_matching": False,
                "forbidden_visuals_blocked": True,
                "reviewed_visual_evidence_required": True,
                "all_scene_failures_reported": True,
            },
        }
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False))
        return 1 if blocked else 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"VISUAL STORY QA BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
