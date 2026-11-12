"""Strict, replayable V2.1 master audio-mix receipt validation.

A receipt proves source-to-master lineage only when it contains hashes for the
master, mixed PCM, narration, mix command, execution log, and every audible
music/SFX source. Declarations and waveform correlation are not substitutes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_SCHEMA_VERSION = "1.0"
MASTER_PROOF = "VERIFIED_MASTER_AUDIO_MIX_AND_SOURCE_IDENTITY"
VALID_SFX_STATUS = {"VERIFIED_NONE", "VERIFIED_COMPLETE"}


def _is_sha(value: Any) -> bool:
    return bool(SHA.fullmatch(str(value or "").strip().lower()))


def _validate_source(source: Any, label: str, failures: list[str]) -> None:
    if not isinstance(source, dict):
        failures.append(f"{label} must be an object")
        return
    for key in ("identity", "sha256", "source_bytes_sha256"):
        if not str(source.get(key) or "").strip():
            failures.append(f"{label}.{key} is required")
    for key in ("sha256", "source_bytes_sha256"):
        if not _is_sha(source.get(key)):
            failures.append(f"{label}.{key} must be a lowercase SHA-256")
    if source.get("source_bytes_verified") is not True:
        failures.append(f"{label}.source_bytes_verified must be true")
    if source.get("audible_use_verified") is not True:
        failures.append(f"{label}.audible_use_verified must be true")


def validate_mix_receipt(
    receipt: Any,
    *,
    expected_episode_id: str | None = None,
) -> list[str]:
    """Return deterministic validation failures; an empty list means valid."""
    failures: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]

    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        failures.append("schema_version must be 1.0")
    if receipt.get("verification_method") != MASTER_PROOF:
        failures.append("verification_method is not the canonical master proof")
    if receipt.get("source_identity_verified_in_mix") is not True:
        failures.append("source_identity_verified_in_mix must be true")

    episode_id = str(receipt.get("episode_id") or "").strip()
    if not episode_id:
        failures.append("episode_id is required")
    elif expected_episode_id is not None and episode_id != expected_episode_id:
        failures.append("episode_id does not match the registry row")

    for key in (
        "master_video_sha256",
        "mixed_audio_sha256",
        "narration_sha256",
        "mix_command_sha256",
        "mix_execution_log_sha256",
    ):
        if not _is_sha(receipt.get(key)):
            failures.append(f"{key} must be a lowercase SHA-256")
    if not str(receipt.get("artifact_id") or "").strip():
        failures.append("artifact_id is required")

    music_sources = receipt.get("music_sources")
    if not isinstance(music_sources, list) or not music_sources:
        failures.append("music_sources must contain at least one source")
    else:
        for index, source in enumerate(music_sources):
            _validate_source(source, f"music_sources[{index}]", failures)

    sfx_status = receipt.get("sfx_usage_status")
    if sfx_status not in VALID_SFX_STATUS:
        failures.append("sfx_usage_status must be VERIFIED_NONE or VERIFIED_COMPLETE")
    sfx_sources = receipt.get("sfx_sources")
    if not isinstance(sfx_sources, list):
        failures.append("sfx_sources must be a list")
    else:
        for index, source in enumerate(sfx_sources):
            _validate_source(source, f"sfx_sources[{index}]", failures)
        if sfx_status == "VERIFIED_NONE" and sfx_sources:
            failures.append("VERIFIED_NONE cannot contain SFX sources")
        if sfx_status == "VERIFIED_COMPLETE" and not sfx_sources:
            failures.append("VERIFIED_COMPLETE requires explicit SFX sources")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    failures = validate_mix_receipt(receipt)
    print(json.dumps({"status": "PASS" if not failures else "BLOCKED", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
