#!/usr/bin/env python3
"""Fail-closed guard for high-signal credentials in the public repository."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Iterable


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9_]{20,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("openai-style-key", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{20,}\b")),
)


def _tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [root / item for item in result.stdout.decode("utf-8").split("\0") if item]


def scan_text(path: Path, text: str) -> list[dict[str, int | str]]:
    failures: list[dict[str, int | str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                failures.append({"path": str(path), "line": line_number, "rule": rule})
    return failures


def scan_paths(root: Path, paths: Iterable[Path] | None = None) -> dict[str, object]:
    failures: list[dict[str, int | str]] = []
    candidates = _tracked_paths(root) if paths is None else list(paths)
    for path in candidates:
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            failures.append({"path": str(path.relative_to(root)), "line": 0, "rule": f"unreadable:{exc}"})
            continue
        if b"\0" in raw:
            continue
        failures.extend(scan_text(path.relative_to(root), raw.decode("utf-8", errors="replace")))
    return {
        "status": "PUBLIC_SECRET_GUARD_PASS" if not failures else "PUBLIC_SECRET_GUARD_BLOCKED",
        "failures": failures,
        "scanned_file_count": len(candidates),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = scan_paths(args.repo_root.resolve())
    print(report)
    return 0 if report["status"] == "PUBLIC_SECRET_GUARD_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
