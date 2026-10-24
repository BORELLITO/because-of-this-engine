#!/usr/bin/env python3
"""Write a truthful, reproducible final manifest after verified delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.pipeline_state import canonical_hash, job_id_from_manifest, sha256_file
from production.video_asset_contract import VideoContractError, load_manifest, resolve_inside


class FinalManifestError(RuntimeError):
    pass


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalManifestError(f"Could not read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise FinalManifestError(f"{label} must be a JSON object: {path}")
    return value


def _fingerprint_timeline(manifest: dict[str, Any]) -> str:
    rows = []
    for scene in manifest.get("scenes", []):
        rows.append({
            "scene_id": scene.get("scene_id"),
            "duration": scene.get("duration"),
            "source_in": scene.get("source_in", 0),
            "transition": scene.get("transition", {}),
            "asset_id": (scene.get("asset") or {}).get("asset_id"),
        })
    return canonical_hash(rows)


def finalize(manifest_path: Path, release_report_path: Path, delivery_receipt_path: Path,
             mode: str, output_path: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = load_manifest(manifest_path)
    release = _read_json(release_report_path.resolve(), "release report")
    delivery = _read_json(delivery_receipt_path.resolve(), "delivery receipt")
    if delivery.get("status") != "DRIVE_VERIFIED":
        raise FinalManifestError("Final manifest requires DRIVE_VERIFIED delivery receipt.")
    if release.get("status") != "VIDEO_RELEASE_VALIDATED":
        raise FinalManifestError("Final manifest requires a validated release report.")
    output = resolve_inside(base, str(manifest.get("output", {}).get("path", "rendered/{video_id}-{mode}.mp4")).format(video_id=manifest["video_id"], mode=mode), "Rendered output")
    if not output.is_file():
        raise FinalManifestError(f"Rendered output is missing: {output}")
    audio = resolve_inside(base, manifest["audio"]["path"], "Narration")
    captions = resolve_inside(base, manifest["captions"]["path"], "Captions")
    final_path = output_path.resolve() if output_path else base / "rendered" / f"final-manifest-{manifest['video_id']}-{mode}.json"
    if base not in final_path.parents:
        raise FinalManifestError("Final manifest must remain inside the episode directory.")
    assets = []
    for scene in manifest.get("scenes", []):
        asset = scene["asset"]
        assets.append({
            "scene_id": scene["scene_id"],
            "asset_id": asset["asset_id"],
            "provider": asset["provider"],
            "source_page_url": asset["source_page_url"],
            "license": asset["license"],
            "sha256": asset["sha256"],
            "perceptual_hash": asset.get("perceptual_hash"),
            "drive_file_id": asset.get("drive_file_id"),
            "visual_match": scene["visual_match"],
            "visual_truth": scene["visual_truth"],
        })
    payload = {
        "status": "READY_FOR_CLEANUP",
        "job_id": job_id_from_manifest(manifest),
        "engine_version": "2.0",
        "schema_version": manifest.get("schema_version"),
        "video_id": manifest.get("video_id"),
        "mode": mode,
        "git_commit": __import__("os").environ.get("GITHUB_SHA"),
        "workflow_run": __import__("os").environ.get("GITHUB_RUN_ID"),
        "topic": manifest.get("title"),
        "voice": manifest.get("voice"),
        "fingerprints": {
            "manifest_sha256": sha256_file(manifest_path),
            "script_sha256": sha256_file(resolve_inside(base, manifest["script"]["path"], "Script")),
            "narration_sha256": sha256_file(audio),
            "voice_metadata_sha256": sha256_file(audio.with_name(audio.name + ".json")) if audio.with_name(audio.name + ".json").is_file() else None,
            "captions_sha256": sha256_file(captions),
            "footage_sha256": canonical_hash([item["sha256"] for item in assets]),
            "timeline_sha256": _fingerprint_timeline(manifest),
            "render_sha256": sha256_file(output),
        },
        "assets": assets,
        "qa": {
            "release_report": str(release_report_path.resolve()),
            "status": release.get("status"),
            "technical_qa": release.get("technical_qa"),
            "caption_gate": release.get("caption_gate"),
            "editorial_qa": release.get("editorial_qa"),
        },
        "delivery": delivery,
        "cleanup": {"status": "PENDING", "verified_before_cleanup": True},
        "timestamps": {"finalized_at_utc": datetime.now(timezone.utc).isoformat()},
    }
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "FINAL_MANIFEST_WRITTEN", "path": str(final_path), "job_id": payload["job_id"], "fingerprints": payload["fingerprints"]}


def mark_complete(final_manifest_path: Path, cleanup_receipt_path: Path) -> dict[str, Any]:
    final_manifest_path = final_manifest_path.resolve()
    payload = _read_json(final_manifest_path, "final manifest")
    receipt = _read_json(cleanup_receipt_path.resolve(), "cleanup delivery receipt")
    if payload.get("status") != "READY_FOR_CLEANUP":
        raise FinalManifestError("Final manifest is not waiting for cleanup completion.")
    if receipt.get("status") != "DRIVE_VERIFIED":
        raise FinalManifestError("Cleanup completion requires a verified Drive receipt.")
    payload["status"] = "PRODUCTION_COMPLETE"
    payload["cleanup"] = {
        "status": "PASS",
        "verified_before_cleanup": True,
        "verified_after_cleanup": True,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    final_manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "PRODUCTION_COMPLETE", "path": str(final_manifest_path), "job_id": payload.get("job_id")}



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--release-report", type=Path)
    parser.add_argument("--delivery-receipt", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--complete", action="store_true", help="Mark an already delivered final manifest complete after cleanup.")
    args = parser.parse_args()
    try:
        if args.complete:
            result = mark_complete(args.manifest, args.delivery_receipt)
        else:
            if not args.release_report:
                parser.error("--release-report is required unless --complete is used.")
            result = finalize(args.manifest, args.release_report, args.delivery_receipt, args.mode, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FinalManifestError, VideoContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FINAL MANIFEST BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
