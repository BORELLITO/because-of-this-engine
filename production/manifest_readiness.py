#!/usr/bin/env python3
"""Fast, fail-closed manifest audit before expensive media initialization.

Never infer scene approval from earlier render success, licenses or older
metadata. Historical manifests are auditable but not automatically upgraded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_CLASSES = {"evidence", "reconstruction", "atmosphere"}
PIXEL_QC_REQUIREMENTS = {"external_branding": "NONE", "crop_safety": "PASS"}


def audit(manifest: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode not in {"preview", "final"}:
        raise ValueError("mode must be preview or final")
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    errors: list[str] = []
    status = manifest.get("lifecycle_status")
    if status == "ARCHIVED_HISTORICAL":
        errors.append("archived historical episode cannot enter the current production workflow")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("manifest requires a non-empty scenes list")
        scenes = []
    for i, scene in enumerate(scenes, 1):
        scene_id = str(scene.get("scene_id", i)) if isinstance(scene, dict) else str(i)
        asset = scene.get("asset") if isinstance(scene, dict) else None
        if not isinstance(asset, dict):
            errors.append(f"{scene_id}: missing video asset object")
            continue
        if asset.get("asset_class") not in ALLOWED_CLASSES:
            errors.append(f"{scene_id}: asset_class requires human review and an approved classification")
        if asset.get("scene_approval") != "APPROVED":
            errors.append(f"{scene_id}: scene_approval must be explicitly APPROVED")
        visual = asset.get("visual_evidence")
        pixel_qc = visual.get("pixel_qc") if isinstance(visual, dict) else None
        for name, expected in PIXEL_QC_REQUIREMENTS.items():
            if not isinstance(pixel_qc, dict) or pixel_qc.get(name) != expected:
                errors.append(f"{scene_id}: visual_evidence.pixel_qc.{name} must be {expected} after verification")
    if mode == "final":
        editorial = manifest.get("editorial_qa")
        if not isinstance(editorial, dict) or editorial.get("status") != "PASS":
            errors.append("final mode requires human editorial_qa.status=PASS")
        elif not editorial.get("reviewer") or not editorial.get("reviewed_at"):
            errors.append("final mode requires editorial reviewer and review timestamp")
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "video_id": manifest.get("video_id", ""),
        "lifecycle_status": status,
        "mode": mode,
        "scene_count": len(scenes),
        "errors": errors,
        "migration_policy": "review_missing_evidence_manually_never_auto_approve",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--episodes-dir", type=Path, default=Path("episodes"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.inventory:
        paths = sorted(args.episodes_dir.glob("*/manifest.json"))
        if not paths:
            print("MANIFEST_INVENTORY_ERROR: no episode manifests found")
            return 1
        for path in paths:
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                preview = audit(manifest, "preview")
                final = audit(manifest, "final")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                print(f"MANIFEST_INVENTORY_ERROR: {path}: {exc}")
                return 1
            print(f"MANIFEST_INVENTORY: {path} preview={preview['status']} "
                  f"final={final['status']} visual_issues={len(preview['errors'])} "
                  f"final_issues={len(final['errors'])}")
        return 0  # Report-only, never invent old evidence or approvals.
    if args.manifest is None:
        parser.error("--manifest is required unless --inventory is used")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = audit(manifest, args.mode)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"MANIFEST_READINESS_ERROR: {exc}")
        return 1
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    if result["errors"]:
        for error in result["errors"]:
            print(f"MANIFEST_READINESS_BLOCKED: {error}")
        return 1
    print(f"MANIFEST_READINESS_PASS: {result['video_id']} ({args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
