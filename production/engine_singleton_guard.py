#!/usr/bin/env python3
"""Enforce one active engine profile and remove legacy execution paths from the tree."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from production.canonical_config import (
    CANONICAL_PROFILE_FINGERPRINT,
    CANONICAL_PROFILE_ID,
)

POLICY_PATH = Path("production/active_engine_policy.json")
SCAN_ROOTS = (Path("production"), Path(".github"), Path("examples"), Path("episodes"))
BLOCKED_PATH_MARKERS = (
    "/v1/",
    "/v1.",
    "/legacy/",
    "/deprecated/",
    "/old-engine/",
    "/old_engine/",
    "_v1.",
    "-v1.",
)


def _tracked_paths(repo_root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        paths: list[Path] = []
        for root in SCAN_ROOTS:
            absolute = repo_root / root
            if absolute.exists():
                paths.extend(path.relative_to(repo_root) for path in absolute.rglob("*") if path.is_file())
        return paths


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _check_policy(repo_root: Path, errors: list[str]) -> None:
    path = repo_root / POLICY_PATH
    if not path.is_file():
        errors.append(f"missing active engine policy: {POLICY_PATH}")
        return
    try:
        policy = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid active engine policy: {exc}")
        return
    if policy.get("active_engine_profile") != CANONICAL_PROFILE_ID:
        errors.append("active policy profile does not match canonical_config.py")
    if policy.get("active_engine_fingerprint") != CANONICAL_PROFILE_FINGERPRINT:
        errors.append("active policy fingerprint does not match canonical_config.py")
    if policy.get("update_rule") != "approved_update_supersedes_previous_active_engine":
        errors.append("active policy does not require approved updates to supersede the previous engine")
    if policy.get("retired_versions") != "must_not_remain_executable_in_active_tree":
        errors.append("active policy does not quarantine retired versions")


def _check_paths(repo_root: Path, errors: list[str]) -> None:
    for relative in _tracked_paths(repo_root):
        normalized = "/" + str(relative).replace("\\", "/").lower() + "/"
        if any(marker in normalized for marker in BLOCKED_PATH_MARKERS):
            errors.append(f"legacy engine execution path is present: {relative}")


def _check_manifests(repo_root: Path, errors: list[str]) -> None:
    candidates: list[Path] = []
    for root in (repo_root / "episodes", repo_root / "examples"):
        if root.exists():
            candidates.extend(path for path in root.rglob("*.json") if path.is_file())
    for path in candidates:
        try:
            value = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        profile = value.get("engine_profile")
        fingerprint = value.get("engine_profile_fingerprint")
        if profile is None and fingerprint is None:
            continue
        if profile != CANONICAL_PROFILE_ID:
            errors.append(f"{path}: legacy or non-canonical engine_profile={profile!r}")
        if fingerprint != CANONICAL_PROFILE_FINGERPRINT:
            errors.append(f"{path}: legacy or non-canonical engine_profile_fingerprint")


def _check_single_declaration(repo_root: Path, errors: list[str]) -> None:
    canonical = repo_root / "production/canonical_config.py"
    if not canonical.is_file():
        errors.append("production/canonical_config.py is missing")
        return
    text = canonical.read_text(encoding="utf-8")
    if len(re.findall(r"^CANONICAL_PROFILE_ID\s*=", text, flags=re.MULTILINE)) != 1:
        errors.append("canonical profile must have exactly one active declaration")
    if len(re.findall(r"^CANONICAL_PROFILE_FINGERPRINT\s*=", text, flags=re.MULTILINE)) != 1:
        errors.append("canonical fingerprint must have exactly one active declaration")


def run(repo_root: Path) -> int:
    errors: list[str] = []
    _check_policy(repo_root, errors)
    _check_paths(repo_root, errors)
    _check_manifests(repo_root, errors)
    _check_single_declaration(repo_root, errors)
    if errors:
        for error in errors:
            print(f"ENGINE_SINGLETON_BLOCKED: {error}")
        return 1
    print(
        "ENGINE_SINGLETON_PASS: "
        f"{CANONICAL_PROFILE_ID} is the only executable engine profile; "
        "retired versions remain audit-only in Git history."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    return run(args.repo_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
