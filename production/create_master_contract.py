#!/usr/bin/env python3
"""Create a hash-bound master contract before rendering an authorial episode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from production.master_timeline import (
    MasterTimelineError,
    audio_metadata,
    build_timeline,
    source_fingerprint,
    write_contract,
)
from production.validate_authorial_episode import caption_events


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a narration-locked master contract.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        audio_path = (manifest_path.parent / manifest["audio"]["path"]).resolve()
        caption_path = (manifest_path.parent / manifest["captions"]["path"]).resolve()
        audio_info = audio_metadata(audio_path)
        events = caption_events(caption_path)
        timeline = build_timeline(manifest_path, manifest, events, audio_info=audio_info)
        sources = source_fingerprint(manifest_path, manifest)
        target = args.output or manifest_path.parent / "rendered" / f"master-contract-{args.mode}.json"
        contract = {
            "status": "MASTER_CONTRACT_CREATED",
            "video_id": manifest["video_id"],
            "mode": args.mode,
            "timeline_version": timeline["timeline_version"],
            "narration_master_id": f"{manifest['video_id']}:{sources['audio_sha256'][:16]}",
            "source_fingerprint": sources["source_fingerprint"],
            "sources": sources,
            "audio": audio_info,
            "timeline": timeline,
        }
        write_contract(target.resolve(), contract)
        print(json.dumps({
            "status": contract["status"],
            "video_id": contract["video_id"],
            "mode": args.mode,
            "contract": str(target.resolve()),
            "source_fingerprint": sources["source_fingerprint"],
            "alignment_mode": timeline["alignment_mode"],
            "audio_duration_seconds": timeline["audio_duration_seconds"],
            "caption_count": timeline["caption_count"],
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, KeyError, json.JSONDecodeError, MasterTimelineError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
