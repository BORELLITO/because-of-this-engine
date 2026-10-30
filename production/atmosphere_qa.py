#!/usr/bin/env python3
"""Read-only luminance and provenance QA for opted-in Cinematic Dread MP4s.

This is a technical exposure gate, NOT subjective approval, factual imagery
verification or copyright clearance. Samples center frame, avoiding the HUD
and karaoke overlay where possible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from production.cinematic_dread import AtmosphereError, plan, timeline

VERSION = "dread-qa-1"
FRAME_SIZE = (96, 96)
MIN_P90 = 36
MAX_P90 = 249
MAX_DARK_FRACTION = 0.84


class AtmosphereQAError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _raw_gray_frame(media: Path, timestamp: float) -> bytes:
    if not media.is_file():
        raise AtmosphereQAError("Render output missing")
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-ss", f"{timestamp:.3f}", "-i", str(media),
        "-frames:v", "1", "-vf",
        "crop=trunc(iw*0.8/2)*2:trunc(ih*0.60/2)*2:"
        "trunc(iw*0.10/2)*2:trunc(ih*0.19/2)*2,"
        "scale=96:96,format=gray",
        "-f", "rawvideo", "pipe:1",
    ], capture_output=True, timeout=35, check=False)
    if result.returncode != 0 or len(result.stdout) != FRAME_SIZE[0] * FRAME_SIZE[1]:
        raise AtmosphereQAError("FFmpeg frame inspection failed: " + result.stderr.decode("utf-8", errors="replace")[-450:])
    return result.stdout


def luma_metrics(pixels: bytes) -> dict[str, Any]:
    if len(pixels) != FRAME_SIZE[0] * FRAME_SIZE[1]:
        raise AtmosphereQAError("Invalid sampled central frame")
    ordered = sorted(pixels)
    p50 = ordered[int(0.50 * (len(ordered) - 1))]
    p90 = ordered[int(0.90 * (len(ordered) - 1))]
    dark = sum(v < 13 for v in ordered) / len(ordered)
    return {"p50": p50, "p90": p90, "near_black_fraction": round(dark, 4),
            "status": ("PASS" if MIN_P90 <= p90 <= MAX_P90 and dark <= MAX_DARK_FRACTION else "BLOCKED")}


def _output(manifest: dict[str, Any], path: Path, mode: str) -> Path:
    relative = str((manifest.get("output") or {}).get("path", "rendered/{video_id}-{mode}.mp4"))
    relative = relative.format(video_id=manifest["video_id"], mode=mode)
    target = (path.parent / relative).resolve()
    if path.parent.resolve() not in target.parents:
        raise AtmosphereQAError("Output escapes episode directory")
    return target


def inspect(manifest_path: Path, mode: str, media_path: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    direction = plan(manifest)
    if not direction.get("enabled"):
        return {"status": "ATMOSPHERE_DISABLED", "enabled": False}
    if mode == "final" and direction["director_review"] != "APPROVED":
        raise AtmosphereQAError("Final atmosphere requires director review APPROVED")
    output = media_path or _output(manifest, manifest_path, mode)
    if not output.is_file():
        raise AtmosphereQAError("Graded MP4 is missing")
    from production.render_video_episode import audio_duration
    narration = (manifest_path.parent / manifest["audio"]["path"]).resolve()
    if manifest_path.parent not in narration.parents:
        raise AtmosphereQAError("Narration escapes episode directory")
    seconds = audio_duration(narration)
    schedule = timeline(direction, manifest["scenes"], seconds)
    checks = []
    for item in schedule:
        timestamp = (item["start"] + item["end"]) / 2
        metrics = luma_metrics(_raw_gray_frame(output, timestamp))
        checks.append({**item, "sample_time": round(timestamp, 3), **metrics})
    blocked = [c["scene_id"] for c in checks if c["status"] != "PASS"]
    result = {
        "status": ("ATMOSPHERE_EXPOSURE_BLOCKED" if blocked else "ATMOSPHERE_TECHNICAL_PASS"),
        "profile": direction["profile"], "enabled": True, "mode": mode,
        "review_status": direction["director_review"],
        "human_editorial_approval_granted_by_this_gate": False,
        "manifest_sha256": sha256_file(manifest_path),
        "render_sha256": sha256_file(output),
        "scene_count": len(checks), "blocked_scenes": blocked, "sampled_exposure": checks,
        "luma_thresholds": {"min_p90": MIN_P90, "max_p90": MAX_P90,
                             "max_dark_fraction": MAX_DARK_FRACTION},
        "source_visual_truth_reviewed_here": False,
        "no_text_layer_added": True,
        "qa_version": VERSION,
    }
    return result


def verify_report_against_media(manifest_path: Path, media: Path, mode: str) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    direction = plan(manifest)
    if not direction["enabled"]:
        return {"status": "NOT_APPLICABLE", "enabled": False}
    report_path = (manifest_path.parent / "rendered" / f"atmosphere-qa-{mode}.json").resolve()
    if not report_path.is_file():
        raise AtmosphereQAError("Missing scene-specific graded-media QA evidence")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report.get("status") != "ATMOSPHERE_TECHNICAL_PASS"
        or report.get("profile") != direction["profile"]
        or report.get("mode") != mode
        or report.get("manifest_sha256") != sha256_file(manifest_path)
        or report.get("render_sha256") != sha256_file(media)
        or report.get("scene_count") != len(direction["scenes"])
        or report.get("blocked_scenes") != []):
        raise AtmosphereQAError("Stale or blocked atmosphere QA evidence")
    if mode == "final" and (direction["director_review"] != "APPROVED"
                            or report.get("review_status") != "APPROVED"):
        raise AtmosphereQAError("Director did not approve the final Cinematic Dread look")
    return {"status": "ATMOSPHERE_QA_EVIDENCE_VERIFIED", "enabled": True,
            "render_sha256": report["render_sha256"], "director_review": direction["director_review"]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--mode", choices=["draft-preview", "preview", "final"], required=True)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    try:
        report = inspect(a.manifest, a.mode)
        if report["status"] == "ATMOSPHERE_DISABLED":
            print(json.dumps(report))
            return 0
        output = a.report or (a.manifest.parent / "rendered" / f"atmosphere-qa-{a.mode}.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        print(json.dumps({"status": report["status"],"blocked_scenes":report["blocked_scenes"],
                          "review_status":report["review_status"]}))
        return 0 if report["status"] == "ATMOSPHERE_TECHNICAL_PASS" else 1
    except (AtmosphereQAError, AtmosphereError, OSError, ValueError,
            TypeError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print("ATMOSPHERE_QA_BLOCKED: " + str(exc))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
