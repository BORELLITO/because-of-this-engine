"""E4 read-only media integrity verifier for new Because Of This candidates.

This tool can validate actual local/Drive-downloaded bytes without changing any
manifest, source file, publication state or TTS. A technical PASS never grants
copyright clearance or human editorial approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

MAX_ASSETS = 25
SAMPLE_POSITIONS = (0.25, 0.5, 0.75)
FRAME_WIDTH = 64
FRAME_PIXELS = FRAME_WIDTH * FRAME_WIDTH


class E4IntegrityError(ValueError):
    pass


def _bytes_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_json(path: Path) -> dict[str, Any]:
    try:
        report = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", str(path)], capture_output=True, check=True, timeout=60,
        )
        return json.loads(report.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise E4IntegrityError(f"ffprobe failed for {path.name}") from exc


def _sample_frame(path: Path, duration: float, fraction: float) -> bytes:
    if not 0 < duration <= 7200:
        raise E4IntegrityError("Video duration is missing or implausible")
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", f"{duration * fraction:.3f}", "-i", str(path),
        "-frames:v", "1", "-an",
        "-vf", (
            f"scale={FRAME_WIDTH}:{FRAME_WIDTH}:force_original_aspect_ratio=decrease,"
            f"pad={FRAME_WIDTH}:{FRAME_WIDTH}:(ow-iw)/2:(oh-ih)/2:color=black,format=gray"
        ),
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise E4IntegrityError(f"Cannot decode a sampled frame of {path.name}") from exc
    if len(result.stdout) != FRAME_PIXELS:
        raise E4IntegrityError(f"Frame had {len(result.stdout)} bytes, expected {FRAME_PIXELS}")
    return result.stdout


def _correlation(a: bytes, b: bytes) -> float:
    if len(a) != len(b) or not a:
        raise E4IntegrityError("Frame dimensions differ")
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    da = sum((x - ma) ** 2 for x in a)
    db = sum((y - mb) ** 2 for y in b)
    if da < 36 * n or db < 36 * n:
        return 0.0  # Near-uniform footage is not evidence of duplication.
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(da * db)


def _resolve_asset(root: Path, asset: dict[str, Any], alias: str | None) -> Path:
    # Exact relative paths only. No directory traversal or symlink escapes.
    candidates = [alias] if alias else [asset.get("path"), asset.get("original_filename")]
    for raw in candidates:
        if not isinstance(raw, str) or not raw.strip():
            continue
        candidate = (root / raw).resolve()
        if root != candidate and root not in candidate.parents:
            raise E4IntegrityError(f"Asset path escapes media root: {raw}")
        if candidate.is_file():
            return candidate
    raise E4IntegrityError(f"Local media file missing for {asset.get('asset_id', '?')}")


def verify(
    manifest_path: Path, media_root: Path, *,
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Inspect files without modifying them; status does not approve licensing."""
    root = media_root.resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= MAX_ASSETS:
        raise E4IntegrityError("Manifest must contain 1-25 scenes for bounded E4 verification")
    aliases = aliases or {}
    reports: list[dict[str, Any]] = []
    middles: dict[str, bytes] = {}

    for scene in scenes:
        scene_id = str(scene.get("scene_id") or "").strip()
        asset = scene.get("asset") or {}
        if not scene_id or not isinstance(asset, dict):
            raise E4IntegrityError("Scene ID or asset missing")
        try:
            path = _resolve_asset(root, asset, aliases.get(scene_id))
            size = path.stat().st_size
            sha = _bytes_sha256(path)
            claimed_sha = str(asset.get("sha256") or "").lower()
            claimed_size = asset.get("filesize_bytes")
            size_ok = (
                isinstance(claimed_size, (int, float)) and
                not isinstance(claimed_size, bool) and
                int(claimed_size) == size
            )
            sha_ok = bool(claimed_sha and sha == claimed_sha)
            probe = _inspect_json(path)
            video = next((v for v in probe.get("streams") or []
                          if v.get("codec_type") == "video"), None)
            if video is None:
                raise E4IntegrityError("No video stream")
            duration = float((probe.get("format") or {}).get("duration") or video.get("duration"))
            frames = [_sample_frame(path, duration, f) for f in SAMPLE_POSITIONS]
            middles[scene_id] = frames[1]
            report = {
                "scene_id": scene_id, "asset_id": asset.get("asset_id"),
                "drive_file_id": asset.get("drive_file_id"),
                "observed_sha256": sha, "expected_sha256": claimed_sha,
                "sha256_match": sha_ok, "bytes": size,
                "expected_bytes": claimed_size, "size_match": size_ok,
                "decoded_frame_count": len(frames), "duration_seconds": round(duration, 3),
                "codec": video.get("codec_name"), "width": video.get("width"),
                "height": video.get("height"),
                "status": "BYTES_AND_SAMPLED_FRAMES_PASS" if sha_ok and size_ok else "BLOCKED",
            }
        except (E4IntegrityError, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            report = {
                "scene_id": scene_id, "asset_id": asset.get("asset_id"),
                "status": "BLOCKED", "reason": str(exc)[:240],
            }
        reports.append(report)

    similarities = []
    keys = list(middles)
    for i, key in enumerate(keys):
        for other in keys[i + 1:]:
            score = _correlation(middles[key], middles[other])
            if score >= 0.965:
                similarities.append({
                    "scene_a": key, "scene_b": other,
                    "correlation": round(score, 4),
                    "classification": "VISUAL_REVIEW_REQUIRED_NOT_AUTOMATIC_DUPLICATE",
                })

    passed = sum(item["status"] == "BYTES_AND_SAMPLED_FRAMES_PASS" for item in reports)
    return {
        "schema_version": "1.1", "video_id": data.get("video_id"),
        "scope": "READ_ONLY_ACTUAL_BYTES_AND_SAMPLED_FRAMES",
        "status": "E4_TECHNICAL_PASS_WITH_REVIEW"
                  if passed == len(reports) and similarities else
                  "E4_TECHNICAL_PASS" if passed == len(reports) else "BLOCKED",
        "verified_clip_count": passed,
        "clip_count": len(reports),
        "decoded_frame_count": passed * len(SAMPLE_POSITIONS),
        "visual_similarity_candidates": similarities,
        "independent_source_license_verified": False,
        "third_party_rights_verified": False,
        "semantic_visual_review_complete": False,
        "human_approved": False,
        "approved_for_new_production": False,
        "source_files_modified": False,
        "assets": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--file-map", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        mapping = json.loads(args.file_map.read_text(encoding="utf-8")) if args.file_map else None
        report = verify(args.manifest, args.media_root, aliases=mapping)
    except (E4IntegrityError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"E4_TECHNICAL_BLOCKED: {exc}")
        return 1
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content)
    # Strong/inconclusive similarity is a mandatory review gate. Never
    # treat "E4_TECHNICAL_PASS_WITH_REVIEW" as a release-ready exit=0.
    return 0 if report["status"] == "E4_TECHNICAL_PASS" else (
        2 if report["status"] == "E4_TECHNICAL_PASS_WITH_REVIEW" else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
