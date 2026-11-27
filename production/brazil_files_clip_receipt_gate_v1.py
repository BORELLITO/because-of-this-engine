"""Fail-closed inventory gate for real Brazil Files EP001 clip receipts.

The gate counts only receipt JSON files already committed to the staged case.
It never downloads media, calls a provider, selects a clip or starts Runflow.
A receipt is evidence, not approval: all receipts remain unselected and the
production handoff stays blocked until the complete dossier and later reviews.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

RECEIPTS_ROOT = Path("episodes/brazil-files/episode-001/clip-receipts")
EXPECTED_CASE_ID = "official-ufo-night-1986"
MIN_REQUIRED_RECEIPTS = 22
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _failure(receipt_name: str, message: str) -> str:
    return f"{receipt_name}: {message}"


def _validate_receipt(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [_failure(path.name, f"unreadable JSON: {exc}")]

    if not isinstance(receipt, dict):
        return None, [_failure(path.name, "receipt must be an object")]

    required_strings = (
        "receipt_id",
        "case_id",
        "beat_id",
        "candidate_id",
        "source_id",
        "source_url",
        "media_url",
        "license_url",
        "rights_status",
        "fingerprint_status",
        "semantic_review",
        "runflow_handoff",
    )
    for key in required_strings:
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            errors.append(_failure(path.name, f"{key} must be a non-empty string"))

    if receipt.get("schema_version") != "1.0":
        errors.append(_failure(path.name, "schema_version must be 1.0"))
    if receipt.get("case_id") != EXPECTED_CASE_ID:
        errors.append(_failure(path.name, "case_id does not match the canonical staged case"))
    if receipt.get("rights_status") != "VERIFIED":
        errors.append(_failure(path.name, "rights_status must be VERIFIED"))
    if receipt.get("fingerprint_status") != "VERIFIED":
        errors.append(_failure(path.name, "fingerprint_status must be VERIFIED"))
    if receipt.get("selected_for_production") is not False:
        errors.append(_failure(path.name, "selected_for_production must remain false"))
    if receipt.get("production_started") is not False:
        errors.append(_failure(path.name, "production_started must remain false"))
    if receipt.get("runflow_handoff") != "BLOCKED_UNTIL_FULL_DOSSIER_AND_ALL_RECEIPTS":
        errors.append(_failure(path.name, "runflow_handoff must remain blocked"))

    source_evidence = receipt.get("source_page_evidence")
    if not isinstance(source_evidence, dict) or not source_evidence.get("license_claim"):
        errors.append(_failure(path.name, "source_page_evidence.license_claim is required"))

    download = receipt.get("download_evidence")
    if not isinstance(download, dict):
        errors.append(_failure(path.name, "download_evidence is required"))
    else:
        digest = download.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(_failure(path.name, "download_evidence.sha256 must be 64 lowercase hex characters"))
        if download.get("integrity_check") != "sha256_verified_against_downloaded_bytes":
            errors.append(_failure(path.name, "download integrity must be explicitly verified"))
        for key in ("width", "height", "duration_seconds"):
            value = download.get(key)
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(_failure(path.name, f"download_evidence.{key} must be positive"))
        if not isinstance(download.get("file_name"), str) or not download["file_name"].strip():
            errors.append(_failure(path.name, "download_evidence.file_name is required"))

    return receipt, errors


def evaluate_clip_receipt_gate(repo_root: Path = Path(".")) -> dict[str, Any]:
    """Return a deterministic inventory report without mutating the repository."""

    root = repo_root.resolve()
    receipts_dir = root / RECEIPTS_ROOT
    errors: list[str] = []
    receipts: list[dict[str, Any]] = []
    valid_receipts: list[dict[str, Any]] = []
    seen_candidates: set[str] = set()
    seen_fingerprints: set[str] = set()

    if not receipts_dir.is_dir():
        errors.append(f"receipt directory is missing: {RECEIPTS_ROOT}")
        files: list[Path] = []
    else:
        files = sorted(path for path in receipts_dir.glob("*.json") if path.is_file())

    for path in files:
        receipt, receipt_errors = _validate_receipt(path)
        errors.extend(receipt_errors)
        if receipt is None:
            continue
        receipts.append(receipt)
        duplicate = False
        candidate_id = receipt.get("candidate_id")
        if candidate_id in seen_candidates:
            errors.append(_failure(path.name, f"duplicate candidate_id: {candidate_id}"))
            duplicate = True
        elif isinstance(candidate_id, str):
            seen_candidates.add(candidate_id)
        download = receipt.get("download_evidence")
        fingerprint = download.get("sha256") if isinstance(download, dict) else None
        if fingerprint in seen_fingerprints:
            errors.append(_failure(path.name, f"duplicate sha256 fingerprint: {fingerprint}"))
            duplicate = True
        elif isinstance(fingerprint, str):
            seen_fingerprints.add(fingerprint)
        if not receipt_errors and not duplicate:
            valid_receipts.append(receipt)

    verified_receipt_count = len(valid_receipts)
    missing_receipts = max(0, MIN_REQUIRED_RECEIPTS - verified_receipt_count)
    if verified_receipt_count < MIN_REQUIRED_RECEIPTS:
        errors.append(
            f"only {verified_receipt_count} verified receipts found; "
            f"{missing_receipts} more required (minimum {MIN_REQUIRED_RECEIPTS})"
        )

    status = "CLIP_RECEIPTS_PASS" if not errors else "CLIP_RECEIPTS_BLOCKED"
    return {
        "status": status,
        "case_id": EXPECTED_CASE_ID,
        "receipts_root": str(RECEIPTS_ROOT),
        "receipt_file_count": len(files),
        "verified_receipt_count": verified_receipt_count,
        "required_receipt_count": MIN_REQUIRED_RECEIPTS,
        "missing_receipts": missing_receipts,
        "unique_candidate_count": len(seen_candidates),
        "unique_fingerprint_count": len(seen_fingerprints),
        "errors": errors,
        "production_started": False,
        "runflow_handoff": "BLOCKED",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    report = evaluate_clip_receipt_gate(parser.parse_args().repo_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "CLIP_RECEIPTS_PASS" else 1)
