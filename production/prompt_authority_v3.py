"""Authority check for the sole operational Because Of This Prompt V3."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

PROMPT_PATH = "docs/PROMPT_MESTRE_BECAUSE_OF_THIS_V3.md"
PROMPT_VERSION = "V3"
PROMPT_SHA256 = "354b9dfb3950e20aecf1b363a95916914a99a9f9cd2f5454d7dd0570c3d4487e"


def validate_prompt_authority(repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if policy.get("master_prompt_version") != PROMPT_VERSION:
        failures.append(
            f"master_prompt_version must be {PROMPT_VERSION}, got {policy.get('master_prompt_version')!r}"
        )
    if policy.get("master_prompt_path") != PROMPT_PATH:
        failures.append(
            f"master_prompt_path must be {PROMPT_PATH}, got {policy.get('master_prompt_path')!r}"
        )
    if policy.get("master_prompt_sha256") != PROMPT_SHA256:
        failures.append("active policy prompt SHA-256 does not match Prompt V3")

    path = repo_root / PROMPT_PATH
    if not path.is_file():
        failures.append(f"active Prompt V3 file is missing: {PROMPT_PATH}")
    else:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != PROMPT_SHA256:
            failures.append(f"Prompt V3 file hash mismatch: expected {PROMPT_SHA256}, got {digest}")

    return {
        "status": "PROMPT_AUTHORITY_PASS" if not failures else "PROMPT_AUTHORITY_BLOCKED",
        "path": PROMPT_PATH,
        "version": PROMPT_VERSION,
        "sha256": PROMPT_SHA256,
        "failures": failures,
    }
