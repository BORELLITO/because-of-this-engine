#!/usr/bin/env python3
"""Create a hash-bound preview approval after a human review."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .require_preview_approval import input_fingerprint, manifest_hash, resolve_inside
except ImportError:
    from require_preview_approval import input_fingerprint, manifest_hash, resolve_inside


def create_approval(manifest_path: Path, reviewer: str, output_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    episode_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_spec = manifest.get("output")
    if not isinstance(output_spec, dict) or not output_spec.get("path"):
        raise ValueError("Manifest output.path is required.")
    preview = resolve_inside(episode_dir, str(output_spec["path"]).format(mode="preview"))
    if not preview.is_file():
        raise ValueError("Render and review the preview before creating approval.")
    approval = {
        "approved": True,
        "video_id": manifest.get("video_id"),
        "preview_manifest_sha256": manifest_hash(manifest_path),
        "preview_inputs_sha256": input_fingerprint(manifest, episode_dir),
        "preview_output_sha256": manifest_hash(preview),
        "reviewer": reviewer,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    output_path = output_path if output_path.is_absolute() else episode_dir / output_path
    output_path = output_path.resolve()
    if episode_dir not in output_path.parents:
        raise ValueError("Approval output must remain inside episode directory.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return approval


def main() -> int:
    parser = argparse.ArgumentParser(description="Create approval after human preview review.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approved", action="store_true", help="Explicitly confirm the human review.")
    args = parser.parse_args()
    if not args.approved:
        parser.error("Pass --approved only after reviewing the preview on a mobile screen.")
    try:
        print(json.dumps(create_approval(args.manifest, args.reviewer, args.output), ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"APPROVAL CREATION FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
