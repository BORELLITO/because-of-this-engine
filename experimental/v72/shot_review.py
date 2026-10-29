#!/usr/bin/env python3
"""Free, read-only shot-selection audit for the V7.2 experimental preview.

Inspired by the MIT-licensed AI Shorts Generator candidate review idea, but
intentionally refuses its cross-video clip reuse model. Never modifies manifests,
downloads media, grants rights, or approves a scene.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from production.asset_reuse_brain import source_asset_key

class ReviewError(ValueError):
    pass

def review(manifest: dict[str, Any]) -> dict[str, Any]:
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ReviewError("Scene list is absent")
    preview_only = manifest.get("lifecycle_status") == "DRAFT_PREVIEW_ONLY"
    seen_sources: dict[str, str] = {}
    seen_ids: set[str] = set()
    rows: list[dict[str, Any]] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ReviewError("Scene must be an object")
        scene_id = str(scene.get("scene_id", "")).strip()
        if not scene_id or scene_id in seen_ids:
            raise ReviewError("Scene IDs must be nonempty and unique")
        seen_ids.add(scene_id)
        asset = scene.get("asset") or {}
        semantics = scene.get("visual_semantics") or {}
        narrative = semantics.get("narrative_anchors") or {}
        anchors = narrative.get("direct_required")
        issues = []
        if not isinstance(anchors, list) or not anchors or not all(isinstance(x, str) and x.strip() for x in anchors):
            issues.append("MISSING_REQUIRED_VISUAL_ANCHORS")
            anchors = []
        if not scene.get("narration_excerpt"):
            issues.append("MISSING_NARRATION_EXCERPT")
        if not isinstance(asset, dict):
            issues.append("MISSING_ASSET_RECORD")
            asset = {}
        source_key = source_asset_key(asset)
        if not source_key:
            issues.append("MISSING_SOURCE_IDENTITY")
        elif source_key in seen_sources:
            issues.append("REPEATED_SOURCE_IN_EPISODE:" + seen_sources[source_key])
        else:
            seen_sources[source_key] = scene_id
        if not asset.get("drive_file_id"):
            issues.append("MISSING_DRIVE_ASSET_REFERENCE")
        rights = str(asset.get("rights_status") or asset.get("rights") or "").upper()
        if preview_only:
            if rights != "PREVIEW_ONLY":
                issues.append("PREVIEW_ASSET_RIGHTS_MISMATCH")
        elif rights == "PREVIEW_ONLY":
            issues.append("PREVIEW_ASSET_NOT_RELEASE_CLEARED")
        rows.append({
            "scene_id": scene_id,
            "narration_excerpt": scene.get("narration_excerpt"),
            "required_anchors": anchors,
            "source_identity": source_key,
            "drive_reference_present": bool(asset.get("drive_file_id")),
            "claimed_visual_match": scene.get("visual_match"),
            "visual_match_is_unverified_metadata": True,
            "rights_status": rights or "UNVERIFIED",
            "issues": issues,
            "status": "BLOCKED" if issues else "METADATA_READY",
        })
    problems = sum(bool(row["issues"]) for row in rows)
    return {
        "experimental_version": "7.2",
        "mode": "DRAFT_PREVIEW" if preview_only else "RELEASE_CANDIDATE",
        "status": "BLOCKED" if problems else "METADATA_READY",
        "scene_count": len(rows),
        "blocked_scene_count": problems,
        "visual_content_verified": False,
        "media_files_verified": False,
        "rights_verified_for_publication": False,
        "manual_approval_required": True,
        "reused_sources_within_manifest_blocked": True,
        "note": "Metadata-only audit. Real pixels, global cross-episode memory, usage rights and audio-video timing need canonical V7 checks.",
        "scenes": rows,
    }

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = review(value)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({k:v for k,v in result.items() if k!="scenes"}, ensure_ascii=False))
        return 1 if result["status"] == "BLOCKED" else 0
    except (OSError, json.JSONDecodeError, ReviewError, ValueError) as exc:
        print("V72_METADATA_REVIEW_BLOCKED: " + str(exc))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
