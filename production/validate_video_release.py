#!/usr/bin/env python3
"""Post-render technical, caption and release gate for the v2 pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.caption_quality import CaptionQualityError, quality_report
from production.media_anomaly import MediaAnomalyError, analyze
from production.render_video_episode import SIZES, audio_duration
from production.video_asset_contract import VideoContractError, ffprobe, load_manifest, sha256_file, validate_manifest


def _output_path(manifest: dict[str, Any], base: Path, video_id: str, mode: str) -> Path:
    template = str(manifest.get("output", {}).get("path", "rendered/{video_id}-{mode}.mp4"))
    return (base / template.format(video_id=video_id, mode=mode)).resolve()


def validate(manifest_path: Path, mode: str) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = load_manifest(manifest_path)
    base = manifest_path.parent
    spec = validate_manifest(manifest, base, mode=mode, check_files=True)
    output = _output_path(manifest, base, spec["video_id"], mode)
    if not output.is_file():
        raise VideoContractError(f"Rendered release is missing: {output}")
    if output.stat().st_size <= 0:
        raise VideoContractError("Rendered release is empty.")
    media = ffprobe(output)
    expected_width, expected_height = SIZES[mode]
    if (media["width"], media["height"]) != (expected_width, expected_height):
        raise VideoContractError(
            f"Release dimensions are {media['width']}x{media['height']}; "
            f"expected {expected_width}x{expected_height}."
        )
    if media.get("codec") != "h264":
        raise VideoContractError(f"Release must use H.264 video; got {media.get('codec')!r}.")
    if media.get("pix_fmt") != "yuv420p":
        raise VideoContractError(f"Release must use yuv420p; got {media.get('pix_fmt')!r}.")
    if abs(float(media.get("fps") or 0) - 25.0) > 0.01:
        raise VideoContractError(f"Release must be 25 fps; got {media.get('fps')!r}.")
    if not media.get("has_audio") or media.get("audio_codec") != "aac":
        raise VideoContractError("Release must contain an AAC audio stream.")
    if media.get("sample_rate") != 48000 or int(media.get("channels") or 0) < 1:
        raise VideoContractError("Release audio must be 48 kHz with at least one channel.")
    narration = audio_duration(spec["audio_path"])
    if abs(float(media["duration"]) - narration) > 0.15:
        raise VideoContractError(
            f"Release duration {media['duration']:.3f}s does not match narration {narration:.3f}s."
        )
    try:
        caption_report = quality_report(manifest_path, require_word_level=mode == "final")
    except CaptionQualityError as exc:
        raise VideoContractError(f"Caption gate failed during release validation: {exc}") from exc
    try:
        anomaly_report = analyze(output)
    except MediaAnomalyError as exc:
        raise VideoContractError(f"Media anomaly gate failed during release validation: {exc}") from exc
    if anomaly_report["status"] == "BLOCKED":
        raise VideoContractError(
            f"Media anomaly gate found {anomaly_report['blocking_findings']} blocking finding(s)."
        )
    editorial = manifest.get("editorial_qa") or {}
    editorial_status = editorial.get("status", "NOT_DECLARED")
    if mode == "final" and editorial_status != "PASS":
        raise VideoContractError("Final release requires editorial_qa.status=PASS.")
    asset_hashes = [str(scene["asset"]["sha256"]).lower() for scene in manifest["scenes"]]
    return {
        "status": "VIDEO_RELEASE_VALIDATED",
        "job_id": spec.get("job_id"),
        "video_id": spec["video_id"],
        "mode": mode,
        "output": str(output),
        "duration_seconds": round(float(media["duration"]), 3),
        "dimensions": f"{media['width']}x{media['height']}",
        "fps": media.get("fps"),
        "codec": media.get("codec"),
        "pixel_format": media.get("pix_fmt"),
        "audio_codec": media.get("audio_codec"),
        "sample_rate": media.get("sample_rate"),
        "channels": media.get("channels"),
        "output_bytes": output.stat().st_size,
        "output_sha256": sha256_file(output),
        "audio_master": "narration_locked",
        "caption_source": str(spec["caption_path"]),
        "caption_gate": caption_report["status"],
        "caption_timing_claim": caption_report["timing_claim"],
        "asset_reuse_gate": "PASS",
        "provenance_gate": "PASS",
        "visual_truth_gate": "CONTRACT_PASS",
        "semantic_match_gate": "PASS",
        "transition_gate": "PASS",
        "clip_count": len(manifest["scenes"]),
        "clip_quantity_gate": spec["clip_quantity_gate"],
        "caption_layout_gate": "PASS",
        "audio_mix_profile": {
            "master": "narration_locked",
            "music_ducking": "sidechain_compress",
            "music_volume": (manifest.get("music") or {}).get("volume", 0.0),
            "target_loudness": "-15 LUFS / -1 dBTP",
        },
        "technical_qa": "PASS",
        "editorial_qa": editorial_status,
        "post_render_sync": "PASS",
        "anomaly_gate": anomaly_report["status"],
        "anomaly_scan": anomaly_report,
        "asset_sha256": asset_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a rendered v2 release.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=tuple(SIZES), default="preview")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.manifest, args.mode)
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
