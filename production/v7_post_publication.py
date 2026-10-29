#!/usr/bin/env python3
"""Close V7.1 G11 from an explicit manual-publication receipt."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from production.production_record_v7 import validate_record, write_record


class PostPublicationError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PostPublicationError(f"{path} must contain a JSON object")
    return value


def close_g11(record: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    validate_record(record)
    required = ("video_id", "platform", "public_url", "published_at", "video_sha256")
    missing = [key for key in required if not str(receipt.get(key, "")).strip()]
    if missing:
        raise PostPublicationError(f"manual publication receipt is missing: {', '.join(missing)}")
    if receipt.get("manual_confirmation") is not True or receipt.get("automatic_publication") is not False:
        raise PostPublicationError("G11 requires explicit manual_confirmation=true and automatic_publication=false")
    expected_video = (record.get("production") or {}).get("production_id")
    if str(receipt.get("video_id")) != str(expected_video):
        raise PostPublicationError("publication receipt video_id does not match the production record")
    if str(receipt.get("platform", "")).lower() not in {"youtube", "youtube_shorts", "tiktok", "instagram_reels"}:
        raise PostPublicationError("publication platform is not in the approved receipt allowlist")
    parsed_url = urlparse(str(receipt["public_url"]))
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise PostPublicationError("publication receipt public_url must be an HTTPS URL")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(receipt["video_sha256"])):
        raise PostPublicationError("publication receipt video_sha256 must be a 64-character hex digest")
    try:
        datetime.fromisoformat(str(receipt["published_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise PostPublicationError("publication receipt published_at must be an ISO-8601 timestamp") from exc
    prior_gates = [record["gates"][f"G{i}"] for i in range(11)]
    if any(gate.get("state") != "passed" for gate in prior_gates):
        raise PostPublicationError("G11 cannot close until G0 through G10 are all passed")
    gate = record["gates"]["G11"]
    if gate.get("state") == "passed":
        return record
    gate.update({
        "state": "passed",
        "severity": "critical_blocking",
        "score": 1.0,
        "evidence": f"manual publication verified on {receipt['platform']} at {receipt['published_at']}",
        "artifacts": [receipt.get("receipt_id", f"g11-{receipt['video_id']}-{receipt['published_at']}")],
        "next_action": "none",
        "finished_at": _now(),
        "human_decision": {"type": "manual_publication_receipt", "platform": receipt["platform"]},
    })
    record.setdefault("post_publication_receipts", []).append({**receipt, "verified_at_utc": _now()})
    record["production"]["state"] = "manually_published"
    record["production"]["updated_at"] = _now()
    record["next_action"] = "COMPLETE"
    validate_record(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = _load(args.record)
        receipt = _load(args.receipt)
        updated = close_g11(record, receipt)
        write_record(args.record, updated)
        print(json.dumps({"status": "G11_MANUAL_PUBLICATION_PASS", "record": str(args.record)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, PostPublicationError) as exc:
        print(f"V7 G11 BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
