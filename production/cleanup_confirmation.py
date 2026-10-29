#!/usr/bin/env python3
"""Explicitly confirmed, scoped cleanup for runner-local ephemeral media."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CleanupError(RuntimeError):
    pass


PATTERNS = (
    "rendered/*.mp4",
    "rendered/*.mov",
    "rendered/*.mkv",
    "runtime-assets/*.mp4",
    "runtime-assets/*.mov",
    "runtime-assets/*.mkv",
)


def cleanup(episode_dir: Path, delivery_receipt: Path, confirmation: str) -> dict[str, Any]:
    if confirmation.lower() != "true":
        raise CleanupError("explicit human cleanup confirmation is required")
    episode_dir = episode_dir.resolve()
    if not episode_dir.is_dir() or episode_dir.name in {"", ".", ".."}:
        raise CleanupError("episode directory is invalid")
    receipt = json.loads(delivery_receipt.resolve().read_text(encoding="utf-8"))
    if receipt.get("status") != "DRIVE_VERIFIED":
        raise CleanupError("cleanup requires a verified Drive delivery receipt")
    targets: list[Path] = []
    for pattern in PATTERNS:
        targets.extend(sorted(episode_dir.glob(pattern)))
    unique = sorted({path.resolve() for path in targets})
    for path in unique:
        if episode_dir not in path.parents:
            raise CleanupError(f"cleanup target escapes episode directory: {path}")
    deleted: list[str] = []
    for path in unique:
        if path.is_file():
            path.unlink()
            deleted.append(str(path))
    receipt_path = episode_dir / ".engine" / "cleanup-receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "CLEANUP_CONFIRMED_AND_COMPLETE",
        "confirmation": True,
        "delivery_receipt": str(delivery_receipt.resolve()),
        "deleted": deleted,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-dir", type=Path, required=True)
    parser.add_argument("--delivery-receipt", type=Path, required=True)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(cleanup(args.episode_dir, args.delivery_receipt, args.confirmation), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, CleanupError) as exc:
        print(f"CLEANUP BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
