#!/usr/bin/env python3
"""Post-render release gate for the v2 video-only pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from production.render_video_episode import SIZES, audio_duration
from production.video_asset_contract import VideoContractError, ffprobe, load_manifest, validate_manifest


def validate(manifest_path: Path, mode: str) -> dict:
    manifest = load_manifest(manifest_path)
    spec = validate_manifest(manifest, manifest_path.parent, mode=mode, check_files=True)
    output = (manifest_path.parent / str(manifest.get("output", {}).get("path", "rendered/{video_id}-{mode}.mp4")).format(video_id=spec["video_id"], mode=mode)).resolve()
    if not output.is_file():
        raise VideoContractError(f"Rendered release is missing: {output}")
    media = ffprobe(output)
    expected_width, expected_height = SIZES[mode]
    if (media["width"], media["height"]) != (expected_width, expected_height):
        raise VideoContractError(f"Release dimensions are {media['width']}x{media['height']}; expected {expected_width}x{expected_height}.")
    if media.get("codec") != "h264":
        raise VideoContractError(f"Release must use H.264 video; got {media.get('codec')!r}.")
    narration = audio_duration(spec["audio_path"])
    if abs(float(media["duration"]) - narration) > 0.15:
        raise VideoContractError(f"Release duration {media['duration']:.3f}s does not match narration {narration:.3f}s.")
    return {
        "status": "VIDEO_RELEASE_VALIDATED",
        "video_id": spec["video_id"],
        "mode": mode,
        "output": str(output),
        "duration_seconds": round(float(media["duration"]), 3),
        "dimensions": f"{media['width']}x{media['height']}",
        "codec": media.get("codec"),
        "audio_master": "narration_locked",
        "caption_source": str(spec["caption_path"]),
        "asset_reuse_gate": "PASS",
        "visual_truth_gate": "PASS",
        "post_render_sync": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=tuple(SIZES), default="preview")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.manifest.resolve(), args.mode)
        target = args.report.resolve() if args.report else args.manifest.resolve().parent / "rendered" / f"video-release-{args.mode}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (VideoContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"VIDEO RELEASE BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


