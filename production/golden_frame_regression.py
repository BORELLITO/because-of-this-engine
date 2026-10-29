#!/usr/bin/env python3
"""Golden layout regression for the locked Because Of This presentation system."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production.render_video_episode import SIZES, layout_px
from production.canonical_config import CANONICAL_PROFILE_ID
from production.video_asset_contract import VideoContractError, ffprobe

EXPECTED = {
    "engine_profile": CANONICAL_PROFILE_ID,
    "brand": {
        "logo_enabled": True,
        "logo_anchor": "center_top",
        "logo_width": 540,
        "logo_top": 72,
        "logo_margin": 54,
        "logo_opacity": 0.82,
    },
    "captions": {
        "alignment": 2,
        "margin_v": 320,
        "word_highlight_enabled": True,
        "word_highlight_mode": "timestamp_color_transform",
    },
    "loop": {
        "transition": "continuity_fade",
        "logo_anchor": "center_center",
        "logo_width": 820,
    },
}


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VideoContractError(f"Could not read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise VideoContractError("Manifest must be a JSON object.")
    return value


def _output_path(manifest: dict[str, Any], manifest_path: Path, mode: str) -> Path:
    configured = str((manifest.get("output") or {}).get("path", ""))
    if not configured:
        raise VideoContractError("Manifest output.path is missing.")
    relative = configured.replace("{video_id}", str(manifest["video_id"])).replace("{mode}", mode)
    return (manifest_path.parent / relative).resolve()


def _assert(report: dict[str, Any], label: str, actual: Any, expected: Any, errors: list[str]) -> None:
    passed = actual == expected
    report[label] = {"status": "PASS" if passed else "BLOCKED", "actual": actual, "expected": expected}
    if not passed:
        errors.append(f"{label}: expected {expected!r}, got {actual!r}")


def run(manifest_path: Path, mode: str, report_path: Path) -> int:
    manifest = _load(manifest_path)
    errors: list[str] = []
    checks: dict[str, Any] = {}
    _assert(checks, "engine_profile", manifest.get("engine_profile"), EXPECTED["engine_profile"], errors)
    if mode not in SIZES:
        raise VideoContractError(f"Unknown render mode: {mode}")
    expected_dimensions = list(SIZES[mode])

    brand = manifest.get("brand") or {}
    for key, expected in EXPECTED["brand"].items():
        _assert(checks, f"brand.{key}", brand.get(key), expected, errors)

    captions = manifest.get("captions") or {}
    style = captions.get("style") or {}
    for key, expected in EXPECTED["captions"].items():
        actual = style.get(key) if key in {"alignment", "margin_v"} else captions.get(key)
        _assert(checks, f"captions.{key}", actual, expected, errors)

    loop = manifest.get("loop") or {}
    for key, expected in EXPECTED["loop"].items():
        _assert(checks, f"loop.{key}", loop.get(key), expected, errors)

    video_path = _output_path(manifest, manifest_path, mode)
    if not video_path.is_file():
        errors.append(f"rendered video is missing: {video_path}")
        media = {}
    else:
        media = ffprobe(video_path)
        _assert(checks, "rendered_dimensions", [media["width"], media["height"]], expected_dimensions, errors)
        _assert(checks, "rendered_has_audio", media["has_audio"], True, errors)
        if not 60.0 <= float(media["duration"]) <= 75.0:
            errors.append(f"rendered duration is outside 60-75s: {media['duration']}")

    report = {
        "status": "PASS" if not errors else "BLOCKED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "video": str(video_path),
        "expected_dimensions": expected_dimensions,
        "expected_visual_layout": {
            "logo_width_px": layout_px(EXPECTED["brand"]["logo_width"], expected_dimensions[0]),
            "logo_top_px": layout_px(EXPECTED["brand"]["logo_top"], expected_dimensions[0]),
            "outro_logo_width_px": layout_px(EXPECTED["loop"]["logo_width"], expected_dimensions[0]),
        },
        "checks": checks,
        "media": media,
        "errors": errors,
        "purpose": "Protect the locked HUD, caption, karaoke, logo, proportion and outro presentation contract.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + chr(10), encoding="utf-8")
    if errors:
        for error in errors:
            print(f"GOLDEN_LAYOUT_BLOCKED: {error}")
        return 1
    print("GOLDEN_LAYOUT_PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--mode", required=True, choices=("draft-preview", "preview", "final"))
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        return run(Path(args.manifest), args.mode, Path(args.report))
    except VideoContractError as exc:
        print(f"GOLDEN_LAYOUT_BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
