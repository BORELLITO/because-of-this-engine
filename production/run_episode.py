#!/usr/bin/env python3
"""Single orchestrator for the independent authorial episode pipeline.

The previous version routed episodes through the legacy Mars renderer. This
orchestrator now points only to the generic authorial renderer/validator so the
repository has one operational path and one set of gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parent
DEFAULT_MANIFEST = REPOSITORY / "examples/mars-climate-orbiter-render-manifest-v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def log_event(path: Path, **event: object) -> None:
    record = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), **event}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def acquire_lock(path: Path) -> None:
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Episode is already running: {path}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "created_at_utc": datetime.now(timezone.utc).isoformat()}))


def run_stage(stage: str, command: list[str], log_path: Path) -> int:
    log_event(log_path, stage=stage, status="STARTED", command=command)
    result = subprocess.run(command, check=False, timeout=1800)
    log_event(log_path, stage=stage, status="COMPLETED" if result.returncode == 0 else "FAILED", returncode=result.returncode)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one independent authorial episode.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--render", action="store_true", help="Render after preflight; without this flag only preflight runs.")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read manifest: {exc}", file=sys.stderr)
        return 2
    if manifest.get("schema_version") != "1.1":
        print("Legacy manifest rejected: use the independent authorial schema 1.1 path.", file=sys.stderr)
        return 2

    episode_dir = manifest_path.parent
    lock_path = manifest_path.with_suffix(".run.lock")
    log_path = episode_dir / "authorial-run-log.jsonl"
    started = time.monotonic()
    try:
        acquire_lock(lock_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    log_event(log_path, stage="RUN", status="STARTED", manifest=str(manifest_path), mode=args.mode, render=args.render)
    try:
        preflight = run_stage(
            "PREFLIGHT",
            [sys.executable, str(ROOT / "preflight_authorial_episode.py"), "--manifest", str(manifest_path), "--mode", args.mode],
            log_path,
        )
        if preflight != 0:
            return preflight
        if not args.render:
            print("PREFLIGHT_READY")
            return 0
        if args.mode == "final":
            approval = run_stage(
                "APPROVAL",
                [sys.executable, str(ROOT / "require_preview_approval.py"), "--manifest", str(manifest_path)],
                log_path,
            )
            if approval != 0:
                return approval
        rendered = run_stage(
            "RENDER",
            [sys.executable, str(ROOT / "render_authorial_episode.py"), "--manifest", str(manifest_path), "--mode", args.mode],
            log_path,
        )
        if rendered != 0:
            return rendered
        report_path = episode_dir / f"authorial-validation-{args.mode}.json"
        validated = run_stage(
            "VALIDATE",
            [sys.executable, str(ROOT / "validate_authorial_episode.py"), "--manifest", str(manifest_path), "--mode", args.mode, "--report", str(report_path)],
            log_path,
        )
        if validated == 0:
            output = episode_dir / str(manifest["output"]["path"]).format(mode=args.mode)
            log_event(log_path, stage="PACKAGE", status="VALIDATED", output=str(output), output_sha256=sha256(output))
        return validated
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        log_event(log_path, stage="RUN", status="FINISHED", duration_ms=round((time.monotonic() - started) * 1000, 1))


if __name__ == "__main__":
    raise SystemExit(main())
