#!/usr/bin/env python3
"""Deterministic fingerprints and receipts for reuse-first video production.

This module is intentionally dependency-free so it can run before the full
production environment is installed. It treats runtime manifests and delivery
receipts as immutable evidence: a stage may be reused only when its inputs
produce the same fingerprint and the prior receipt is valid.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

REUSE_VERSION = "reuse-first-v1"
RENDERER_VERSION = "scene-render-cache-v1"
ALIGNMENT_VERSION = "vosk-alignment-v1"
CAPTION_VERSION = "caption-pipeline-v1"
MUSIC_VERSION = "procedural-music-v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _script_payload(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    script_candidates = [
        manifest_path.parent / "script.txt",
        manifest_path.parent / str(manifest.get("script_path", "")),
    ]
    script = next((p for p in script_candidates if str(p).strip() and p.is_file()), None)
    return {
        "sha256": file_digest(script) if script else None,
        "path": str(script.relative_to(manifest_path.parent)) if script else None,
        "narration": manifest.get("narration") or manifest.get("tts") or manifest.get("voice") or {},
    }


def _code_fingerprints(manifest_path: Path) -> dict[str, str]:
    """Hash every executable stage that can affect a reusable artifact."""
    repo_root = manifest_path.resolve().parents[1]
    files = {
        "reuse_first": repo_root / "production/reuse_first.py",
        "renderer": repo_root / "production/render_video_episode.py",
        "visual_effects": repo_root / "production/visual_effects_v73.py",
        "asset_hydration": repo_root / "production/google_drive_assets.py",
        "alignment": repo_root / "production/align_captions.py",
        "story_intelligence": repo_root / "production/story_intelligence.py",
        "caption_quality": repo_root / "production/caption_quality.py",
        "music": repo_root / "production/generate_suspense_bed.py",
        "release_validation": repo_root / "production/validate_video_release.py",
        "golden_layout": repo_root / "production/golden_frame_regression.py",
        "orchestrator": repo_root / "production/v7_orchestrator.py",
        "drive_delivery": repo_root / "production/google_drive_delivery.py",
        "narration_cache": repo_root / "production/narration_cache.py",
        "contract": repo_root / "production/v7_contract.py",
        "tts": repo_root / "production/gemini_tts.py",
        "production_record": repo_root / "production/production_record_v7.py",
        "canonical_config": repo_root / "production/canonical_config.py",
        "active_policy": repo_root / "production/active_engine_policy.json",
        "visual_contract": repo_root / "production/video_asset_contract.py",
        "quality_gates": repo_root / "production/quality_gates.py",
        "singleton_guard": repo_root / "production/v7_singleton_guard.py",
        "post_publication": repo_root / "production/v7_post_publication.py",
    }
    return {
        name: file_digest(path) if path.is_file() else "missing"
        for name, path in files.items()
    }


def _scene_payload(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for scene in manifest.get("scenes") or []:
        asset = scene.get("asset") or {}
        result.append(
            {
                "scene_id": scene.get("scene_id"),
                "beat_id": scene.get("beat_id"),
                "duration": scene.get("duration"),
                "source_in": scene.get("source_in", 0),
                "source_out": scene.get("source_out"),
                "focus": scene.get("focus"),
                "transition": scene.get("transition"),
                "asset_id": asset.get("asset_id"),
                "asset_sha256": asset.get("sha256"),
                "drive_file_id": asset.get("drive_file_id"),
                "visual_semantics": scene.get("visual_semantics"),
                "visual_match": scene.get("visual_match"),
            }
        )
    return result


def compute_fingerprints(manifest_path: Path, mode: str = "draft-preview") -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    script = _script_payload(manifest_path, manifest)
    scenes = _scene_payload(manifest)
    code = _code_fingerprints(manifest_path)
    grade = manifest.get("color_grade") or {}
    clip_policy = (manifest.get("editing") or {}).get("clip_quantity") or manifest.get("clip_policy") or {}
    music = manifest.get("music") or {}
    captions = manifest.get("captions") or manifest.get("caption_style") or {}
    brand = manifest.get("brand") or {}
    loop = manifest.get("loop") or {}

    narration_key = digest(
        {
            "version": REUSE_VERSION,
            "script": script,
            "video_id": manifest.get("video_id"),
            "mode": mode,
        }
    )
    alignment_key = digest(
        {
            "version": ALIGNMENT_VERSION,
            "narration_key": narration_key,
            "model": "vosk-model-en-us-0.22-lgraph",
            "secondary_model": "vosk-model-small-en-us-0.15",
            "code": {
                "alignment": code["alignment"],
                "story_intelligence": code["story_intelligence"],
            },
        }
    )
    caption_key = digest(
        {
            "version": CAPTION_VERSION,
            "alignment_key": alignment_key,
            "caption_style": captions,
            "code": {
                "caption_quality": code["caption_quality"],
                "alignment": code["alignment"],
            },
        }
    )
    music_key = digest(
        {
            "version": MUSIC_VERSION,
            "music": music,
            "duration": (music.get("generation") or {}).get("duration_seconds", 70),
            "sample_rate": (music.get("generation") or {}).get("sample_rate_hz", 48000),
            "code": code["music"],
        }
    )
    asset_key = digest(
        {
            "version": REUSE_VERSION,
            "video_id": manifest.get("video_id"),
            "scenes": [
                {
                    "scene_id": scene.get("scene_id"),
                    "asset_id": scene.get("asset_id"),
                    "asset_sha256": scene.get("asset_sha256"),
                    "drive_file_id": scene.get("drive_file_id"),
                }
                for scene in scenes
            ],
            "code": {"asset_hydration": code["asset_hydration"]},
        }
    )
    scene_key = digest(
        {
            "version": RENDERER_VERSION,
            "mode": mode,
            "width": 1080,
            "height": 1920,
            "scenes": scenes,
            "color_grade": grade,
            "clip_policy": clip_policy,
            "code": {
                "renderer": code["renderer"],
                "visual_effects": code["visual_effects"],
                "asset_hydration": code["asset_hydration"],
            },
        }
    )
    final_key = digest(
        {
            "version": RENDERER_VERSION,
            "mode": mode,
            "narration_key": narration_key,
            "alignment_key": alignment_key,
            "caption_key": caption_key,
            "music_key": music_key,
            "scene_key": scene_key,
            "brand": brand,
            "loop": loop,
            "code": code,
        }
    )
    return {
        "reuse_version": REUSE_VERSION,
        "renderer_version": RENDERER_VERSION,
        "mode": mode,
        "video_id": manifest.get("video_id"),
        "code_fingerprints": code,
        "narration_key": narration_key,
        "alignment_key": alignment_key,
        "caption_key": caption_key,
        "music_key": music_key,
        "asset_key": asset_key,
        "scene_key": scene_key,
        "final_key": final_key,
    }


def write_github_output(values: dict[str, Any], path: Path) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            handle.write(f"{key}={value}\n")


def write_receipt(
    fingerprints: dict[str, Any],
    receipt_path: Path,
    manifest_path: Path,
    delivery_receipt: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload: dict[str, Any] = {
        "status": "REUSE_RECEIPT_VALID",
        "reuse_version": REUSE_VERSION,
        "fingerprints": fingerprints,
        "manifest": str(manifest_path),
        "video_id": manifest.get("video_id"),
        "delivery": None,
    }
    if delivery_receipt and delivery_receipt.is_file():
        delivery = json.loads(delivery_receipt.read_text(encoding="utf-8"))
        if delivery.get("status") != "DRIVE_VERIFIED":
            raise RuntimeError("Delivery receipt is not DRIVE_VERIFIED.")
        payload["delivery"] = {
            "status": delivery.get("status"),
            "delivery_name": delivery.get("delivery_name"),
            "job_id": delivery.get("job_id"),
            "delivery_folder_id": delivery.get("delivery_folder_id"),
            "delivery_folder_url": delivery.get("delivery_folder_url"),
            "file_count": delivery.get("file_count"),
            "files": delivery.get("files", []),
        }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_name(receipt_path.name + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, receipt_path)
    return payload


def verify_receipt(receipt_path: Path, fingerprints: dict[str, Any]) -> tuple[bool, str]:
    if not receipt_path.is_file():
        return False, "receipt_missing"
    try:
        value = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "receipt_invalid_json"
    if value.get("status") != "REUSE_RECEIPT_VALID":
        return False, "receipt_status_invalid"
    stored = value.get("fingerprints") or {}
    if stored.get("final_key") != fingerprints.get("final_key"):
        return False, "fingerprint_mismatch"
    delivery = value.get("delivery") or {}
    if delivery.get("status") != "DRIVE_VERIFIED":
        return False, "delivery_not_verified"
    if not delivery.get("delivery_folder_url"):
        return False, "delivery_link_missing"
    try:
        file_count = int(delivery.get("file_count") or 0)
    except (TypeError, ValueError):
        return False, "delivery_file_count_invalid"
    if file_count <= 0 or not isinstance(delivery.get("files"), list) or len(delivery["files"]) != file_count:
        return False, "delivery_files_missing"
    if any(
        not isinstance(item, dict)
        or not item.get("id")
        or not item.get("name")
        or not item.get("size")
        or not item.get("md5")
        for item in delivery["files"]
    ):
        return False, "delivery_file_evidence_incomplete"
    return True, "reuse_valid"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    fp = sub.add_parser("fingerprint")
    fp.add_argument("--manifest", type=Path, required=True)
    fp.add_argument("--mode", default="draft-preview")
    fp.add_argument("--output", type=Path, required=True)
    fp.add_argument("--github-output", type=Path)

    receipt = sub.add_parser("write-receipt")
    receipt.add_argument("--manifest", type=Path, required=True)
    receipt.add_argument("--fingerprints", type=Path, required=True)
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--delivery-receipt", type=Path)

    verify = sub.add_parser("verify-receipt")
    verify.add_argument("--fingerprints", type=Path, required=True)
    verify.add_argument("--receipt", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "fingerprint":
            values = compute_fingerprints(args.manifest.resolve(), args.mode)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if args.github_output:
                write_github_output(values, args.github_output)
            print(json.dumps(values, ensure_ascii=False))
            return 0
        if args.command == "write-receipt":
            fingerprints = json.loads(args.fingerprints.read_text(encoding="utf-8"))
            payload = write_receipt(
                fingerprints,
                args.receipt.resolve(),
                args.manifest.resolve(),
                args.delivery_receipt.resolve() if args.delivery_receipt else None,
            )
            print(json.dumps(payload, ensure_ascii=False))
            return 0
        fingerprints = json.loads(args.fingerprints.read_text(encoding="utf-8"))
        valid, reason = verify_receipt(args.receipt.resolve(), fingerprints)
        print(json.dumps({"valid": valid, "reason": reason}, ensure_ascii=False))
        return 0 if valid else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"REUSE-FIRST BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
