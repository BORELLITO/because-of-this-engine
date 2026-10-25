#!/usr/bin/env python3
"""Run the fail-closed visual-story gate for a v2 episode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.video_asset_contract import VideoContractError, load_manifest, validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        spec = validate_manifest(manifest, args.manifest.parent, mode=args.mode, check_files=True)
        scenes = []
        for scene in spec["scenes"]:
            qa = scene.get("visual_qa") or {}
            scenes.append({
                "scene_id": scene["scene_id"],
                "narration_excerpt": scene.get("narration_excerpt"),
                "story_beat": scene.get("story_beat"),
                "visual_match": scene.get("visual_match"),
                "semantic_score": qa.get("score"),
                "coverage": qa.get("coverage"),
                "status": qa.get("status"),
                "reason": qa.get("reason"),
                "missing": qa.get("missing"),
                "forbidden_hits": qa.get("forbidden_hits"),
            })
        report = {
            "status": "VISUAL_STORY_QA_PASS",
            "video_id": spec["video_id"],
            "mode": args.mode,
            "scene_count": len(scenes),
            "scenes": scenes,
            "policy": {
                "narration_is_master_context": True,
                "isolated_keyword_matching": False,
                "forbidden_visuals_blocked": True,
                "reviewed_visual_evidence_required": True,
            },
        }
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, VideoContractError, json.JSONDecodeError) as exc:
        print(f"VISUAL STORY QA BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
