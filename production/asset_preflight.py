#!/usr/bin/env python3
"""Fail-closed visual preflight for approved scene assets.

This stage runs after Drive hydration and before narration/render.  It creates
one auditable contact sheet for the whole visual sequence and blocks assets
that have not been individually approved, are not classified, cannot survive
the locked 9:16 crop, or contain a pre-composed layout.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production.video_asset_contract import (
    VideoContractError,
    _validate_clean_frame_layout,
    ffprobe,
)

ALLOWED_ASSET_CLASSES = {"evidence", "reconstruction", "atmosphere"}
EXPECTED_PIXEL_QC = {
    "external_branding": "NONE",
    "crop_safety": "PASS",
}
CONTACT_COLUMNS = 3
CONTACT_ROWS = 4
THUMB_WIDTH = 270
THUMB_HEIGHT = 480


def _run(command: list[str], *, label: str) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise VideoContractError(f"{label} failed: {detail[-500:]}") from exc


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise VideoContractError("Manifest must be a JSON object.")
    return value


def _crop_issue(scene: dict[str, Any], metadata: dict[str, Any]) -> str | None:
    width = float(metadata.get("width", 0))
    height = float(metadata.get("height", 0))
    if width < 720 or height < 720:
        return f"source resolution is below 720 pixels ({int(width)}x{int(height)})"
    focus = scene.get("focus") or {}
    try:
        focus_x = float(focus.get("x", 0.5))
        focus_y = float(focus.get("y", 0.5))
    except (TypeError, ValueError):
        return "focus coordinates are not numeric"
    if not 0.0 <= focus_x <= 1.0 or not 0.0 <= focus_y <= 1.0:
        return "focus coordinates must remain between 0 and 1"

    target_aspect = 9.0 / 16.0
    source_aspect = width / height
    if source_aspect > target_aspect:
        crop_width = height * target_aspect
        crop_left = (width - crop_width) / 2.0
        crop_right = crop_left + crop_width
        focus_pixel = focus_x * width
        if not crop_left <= focus_pixel <= crop_right:
            return "declared focus falls outside the locked 9:16 center crop"
    elif source_aspect < target_aspect:
        crop_height = width / target_aspect
        crop_top = (height - crop_height) / 2.0
        crop_bottom = crop_top + crop_height
        focus_pixel = focus_y * height
        if not crop_top <= focus_pixel <= crop_bottom:
            return "declared focus falls outside the locked 9:16 center crop"
    return None


def _render_contact_sheet(
    scenes: list[dict[str, Any]],
    episode_dir: Path,
    contact_sheet: Path,
    work_dir: Path,
) -> list[dict[str, Any]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: list[Path] = []
    labels: list[dict[str, Any]] = []
    for scene in scenes:
        scene_id = str(scene["scene_id"])
        asset = scene["asset"]
        path = (episode_dir / str(asset["path"])).resolve()
        metadata = ffprobe(path)
        duration = float(metadata["duration"])
        timestamp = min(max(duration * 0.50, 0.0), max(0.0, duration - min(0.05, duration / 10.0)))
        frame_path = work_dir / f"{scene_id}.jpg"
        vf = (
            f"scale={THUMB_WIDTH}:{THUMB_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={THUMB_WIDTH}:{THUMB_HEIGHT},"
            f"drawtext=text={scene_id}:x=12:y=12:fontsize=30:"
            "fontcolor=white:box=1:boxcolor=black@0.65"
        )
        _run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                vf,
                "-q:v",
                "3",
                str(frame_path),
            ],
            label=f"contact-sheet frame {scene_id}",
        )
        frame_paths.append(frame_path)
        labels.append(
            {
                "scene_id": scene_id,
                "timestamp_seconds": round(timestamp, 3),
                "source": str(asset.get("source_page_url", "")),
                "asset_class": asset.get("asset_class"),
            }
        )

    if not frame_paths:
        raise VideoContractError("Cannot create a contact sheet without scenes.")
    _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-pattern_type",
            "glob",
            "-i",
            str(work_dir / "*.jpg"),
            "-frames:v",
            "1",
            "-vf",
            f"tile={CONTACT_COLUMNS}x{CONTACT_ROWS}:padding=10:margin=10:color=black",
            "-q:v",
            "2",
            str(contact_sheet),
        ],
        label="visual contact sheet",
    )
    return labels


def run(manifest_path: Path, report_path: Path, contact_sheet: Path) -> int:
    manifest = _load_manifest(manifest_path)
    episode_dir = manifest_path.parent
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise VideoContractError("Manifest requires scenes for visual preflight.")

    errors: list[str] = []
    asset_report: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for scene in scenes:
        scene_id = str(scene.get("scene_id", "?"))
        asset = scene.get("asset")
        if not isinstance(asset, dict):
            errors.append(f"{scene_id}: asset is missing")
            continue
        asset_class = str(asset.get("asset_class", "")).strip().lower()
        if asset_class not in ALLOWED_ASSET_CLASSES:
            errors.append(
                f"{scene_id}: asset_class must be one of {sorted(ALLOWED_ASSET_CLASSES)}"
            )
        if asset.get("scene_approval") != "APPROVED":
            errors.append(f"{scene_id}: individual scene approval is not APPROVED")
        evidence = asset.get("visual_evidence") or {}
        pixel_qc = evidence.get("pixel_qc") if isinstance(evidence, dict) else {}
        for key, expected in EXPECTED_PIXEL_QC.items():
            if not isinstance(pixel_qc, dict) or pixel_qc.get(key) != expected:
                errors.append(f"{scene_id}: pixel_qc.{key} must be {expected}")
        path_value = str(asset.get("path", ""))
        if path_value.lower() in seen_paths:
            errors.append(f"{scene_id}: runtime asset path is repeated")
        seen_paths.add(path_value.lower())
        path = (episode_dir / path_value).resolve()
        if not path.is_file():
            errors.append(f"{scene_id}: hydrated asset is missing: {path}")
            continue
        try:
            metadata = ffprobe(path)
            crop_issue = _crop_issue(scene, metadata)
            if crop_issue:
                errors.append(f"{scene_id}: {crop_issue}")
            _validate_clean_frame_layout(path, scene_id, float(metadata["duration"]))
            asset_report.append(
                {
                    "scene_id": scene_id,
                    "asset_id": asset.get("asset_id"),
                    "asset_class": asset_class,
                    "scene_approval": asset.get("scene_approval"),
                    "dimensions": [metadata["width"], metadata["height"]],
                    "duration_seconds": metadata["duration"],
                    "crop_safety": "PASS",
                    "embedded_layout": "NONE",
                    "external_branding": "NONE",
                }
            )
        except (VideoContractError, OSError, ValueError) as exc:
            errors.append(f"{scene_id}: {exc}")

    contact_labels: list[dict[str, Any]] = []
    work_dir = contact_sheet.parent / ".asset-contact-sheet"
    if not errors:
        try:
            contact_labels = _render_contact_sheet(scenes, episode_dir, contact_sheet, work_dir)
        except VideoContractError as exc:
            errors.append(str(exc))
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)

    report = {
        "status": "PASS" if not errors else "BLOCKED",
        "manifest": str(manifest_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_count": len(scenes),
        "contact_sheet": str(contact_sheet) if contact_sheet.is_file() else None,
        "contact_sheet_labels": contact_labels,
        "assets": asset_report,
        "errors": errors,
        "review_contract": {
            "asset_class_required": True,
            "individual_scene_approval_required": True,
            "external_branding": "NONE",
            "crop_safety": "PASS",
            "embedded_layout": "NONE",
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + chr(10), encoding="utf-8")
    if errors:
        for error in errors:
            print(f"VISUAL_PREFLIGHT_BLOCKED: {error}", file=sys.stderr)
        return 1
    print(f"VISUAL_PREFLIGHT_PASS: {contact_sheet}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--contact-sheet", required=True)
    args = parser.parse_args()
    try:
        return run(Path(args.manifest), Path(args.report), Path(args.contact_sheet))
    except VideoContractError as exc:
        print(f"VISUAL_PREFLIGHT_BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
