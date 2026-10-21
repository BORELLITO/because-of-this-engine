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
