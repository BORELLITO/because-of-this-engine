#!/usr/bin/env python3
"""Require explicit human approval before a final authorial render."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


class ApprovalError(RuntimeError):
    pass


def manifest_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_fingerprint(manifest: dict, episode_dir: Path) -> str:
    digest = hashlib.sha256()
    for scene in manifest.get("scenes", []):
        image = resolve_inside(episode_dir, scene.get("image"))
        digest.update(str(scene.get("scene_id")).encode("utf-8"))
        digest.update(hashlib.sha256(image.read_bytes()).digest())
    for section, key in (("audio", "path"), ("captions", "path")):
        spec = manifest.get(section)
        if isinstance(spec, dict) and spec.get(key):
            path = resolve_inside(episode_dir, spec[key])
            digest.update(section.encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def resolve_inside(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ApprovalError("Approval path must be a non-empty string.")
    target = (base / relative).resolve()
    if target != base and base not in target.parents:
        raise ApprovalError("Approval path escapes the episode directory.")
    return target


def require_approval(manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    episode_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approval = manifest.get("approval")
    if not isinstance(approval, dict) or not approval.get("path"):
        raise ApprovalError("Manifest requires approval.path for final renders.")
    approval_path = resolve_inside(episode_dir, approval["path"])
    if not approval_path.is_file():
        raise ApprovalError(f"Preview approval file is missing: {approval_path}")
    data = json.loads(approval_path.read_text(encoding="utf-8"))
    if data.get("approved") is not True:
        raise ApprovalError("Preview approval is not marked approved.")
    if data.get("video_id") != manifest.get("video_id"):
        raise ApprovalError("Approval video_id does not match the manifest.")
    if data.get("preview_manifest_sha256") != manifest_hash(manifest_path):
        raise ApprovalError("Approval was created for a different manifest version.")
    expected_inputs = input_fingerprint(manifest, episode_dir)
    if data.get("preview_inputs_sha256") != expected_inputs:
        raise ApprovalError("Approval was created for different episode inputs.")
    output_spec = manifest.get("output")
    if not isinstance(output_spec, dict) or not output_spec.get("path"):
        raise ApprovalError("Manifest output.path is required for approval.")
    preview_output = resolve_inside(episode_dir, str(output_spec["path"]).format(mode="preview"))
    if not preview_output.is_file():
        raise ApprovalError("The approved preview output is missing.")
    if data.get("preview_output_sha256") != manifest_hash(preview_output):
        raise ApprovalError("Approval was created for a different preview output.")
    reviewer = data.get("reviewer")
    approved_at = data.get("approved_at")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ApprovalError("Approval requires a reviewer.")
    if not isinstance(approved_at, str) or not approved_at.strip():
        raise ApprovalError("Approval requires approved_at.")
    try:
        datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError("approved_at must be an ISO-8601 timestamp.") from exc
    return {"approval_path": str(approval_path), "reviewer": reviewer, "approved_at": approved_at}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check preview approval for a final render.")
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(require_approval(args.manifest), ensure_ascii=False, indent=2))
    except (ApprovalError, OSError, json.JSONDecodeError) as exc:
        print(f"APPROVAL BLOCKED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
