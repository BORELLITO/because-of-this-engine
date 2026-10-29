#!/usr/bin/env python3
"""Prove that the active Because Of This entrypoint is the V7.1 engine only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from production.canonical_config import CANONICAL_PROFILE_ID, CANONICAL_PROFILE_FINGERPRINT
from production.v7_contract import PROMPT_SHA256, PROMPT_VERSION, validate_prompt_and_schema


class SingletonGuardError(RuntimeError):
    pass


FORBIDDEN_ACTIVE_MARKERS = (
    "because-of-this-v2-locked-2026-10",
    "master_prompt_version: 6.0",
    "GEMINI_API_KEY",
    "gemini-3.8-flash-tts",
    "elevenlabs",
    "narrate.py",
)


def _active_workflow_paths(root: Path) -> list[Path]:
    workflow_root = root / ".github" / "workflows"
    return sorted(path for path in workflow_root.glob("*.yml") if path.name == "because-of-this-v7.yml")


def audit(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    prompt = validate_prompt_and_schema(root)
    policy_path = root / "production" / "active_engine_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("active_engine_profile") != CANONICAL_PROFILE_ID:
        raise SingletonGuardError("active policy does not point to the V7.1 profile")
    if policy.get("active_engine_fingerprint") != CANONICAL_PROFILE_FINGERPRINT:
        raise SingletonGuardError("active policy fingerprint does not match canonical V7.1 config")
    if policy.get("master_prompt_version") != PROMPT_VERSION or policy.get("master_prompt_sha256") != PROMPT_SHA256:
        raise SingletonGuardError("active policy does not pin the canonical V7.1 prompt")
    if policy.get("production_schema") != "because-of-this://schemas/production-record/3.0.0":
        raise SingletonGuardError("active policy does not pin schema 3.0.0")
    workflows = _active_workflow_paths(root)
    if len(workflows) != 1:
        raise SingletonGuardError("exactly one V7 workflow must be active")
    offenders: list[str] = []
    for path in [policy_path, workflows[0], root / "production" / "v7_orchestrator.py", root / "production" / "cloud_tts.py"]:
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_ACTIVE_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(root)} contains forbidden active marker {marker}")
    if offenders:
        raise SingletonGuardError("; ".join(offenders))
    return {
        "status": "V7_SINGLE_ACTIVE_ENGINE_PASS",
        "profile": CANONICAL_PROFILE_ID,
        "fingerprint": CANONICAL_PROFILE_FINGERPRINT,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": PROMPT_SHA256,
        "workflow": str(workflows[0].relative_to(root)),
        "legacy_execution": "blocked_and_archived",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.repo_root), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, SingletonGuardError) as exc:
        print(f"V7 SINGLETON BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
