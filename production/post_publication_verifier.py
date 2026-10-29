#!/usr/bin/env python3
"""Validate the manual publication receipt and close G11 safely."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from production.prompt_compliance import PromptComplianceError, validate_post_publication


class PostPublicationError(RuntimeError):
    pass


def verify(final_manifest_path: Path, receipt_path: Path) -> dict[str, Any]:
    final_manifest_path = final_manifest_path.resolve()
    receipt_path = receipt_path.resolve()
    try:
        payload = json.loads(final_manifest_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PostPublicationError("final manifest or publication receipt is unreadable") from exc
    if not isinstance(payload, dict) or not isinstance(receipt, dict):
        raise PostPublicationError("final manifest and publication receipt must be objects")
    if payload.get("status") != "READY_FOR_MANUAL_PUBLICATION":
        raise PostPublicationError("final manifest is not waiting for manual publication")
    release = payload.get("qa") or {}
    report = validate_post_publication(receipt, release if "duration_seconds" in release else None)
    if report["status"] != "PASS":
        raise PostPublicationError("; ".join(report["errors"]))
    payload["status"] = "PRODUCTION_COMPLETE"
    payload["publication_status"] = "PUBLISHED_VERIFIED"
    payload["post_publication"] = {
        "status": "PASS",
        "platform": receipt["platform"],
        "url": receipt["url"],
        "receipt_sha256": __import__("hashlib").sha256(receipt_path.read_bytes()).hexdigest(),
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "divergences": receipt.get("divergences", []),
    }
    payload["next_action"] = "REPORT_METRICS_AFTER_SEVEN_DAYS"
    fd, temp_name = tempfile.mkstemp(prefix=f".{final_manifest_path.name}.", dir=final_manifest_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, final_manifest_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {
        "status": "POST_PUBLICATION_VERIFIED",
        "final_manifest": str(final_manifest_path),
        "platform": receipt["platform"],
        "url": receipt["url"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.final_manifest, args.receipt), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, PromptComplianceError, PostPublicationError) as exc:
        print(f"POST-PUBLICATION BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
