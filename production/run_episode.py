#!/usr/bin/env python3
"""Run and validate one independent episode with a lock and JSONL audit log."""

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
DEFAULT_MANIFEST = ROOT / "mars-climate-orbiter-episode.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: dict) -> None:
    temp = path.with_name(f".{path.name}.part")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and validate one independent BECAUSE OF THIS episode.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--render", action="store_true", help="Run the local FFmpeg render before validation.")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    episode_id = manifest["episode_id"]
    lock_path = manifest_path.with_suffix(".lock")
    log_path = manifest_dir / "run-log.jsonl"
    started = time.monotonic()

    try:
        acquire_lock(lock_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    log_event(log_path, run_id=f"{episode_id}-{int(time.time())}", episode_id=episode_id, stage="RUN", status="STARTED", render=args.render)
    try:
        if args.render:
            if manifest.get("approval_status") == "APPROVED":
                log_event(log_path, episode_id=episode_id, stage="RENDER", status="BLOCKED", reason="approved_episode")
                print("Refusing to overwrite an APPROVED episode. Create a new version.", file=sys.stderr)
                return 2
            try:
                subprocess.run([
                    sys.executable,
                    str(ROOT / "render_mars_final.py"),
                    "--manifest",
                    str(manifest_path),
                ], check=True, timeout=1200)
                output = (manifest_dir / manifest["output"]["path"]).resolve()
                music = (manifest_dir / manifest["mix"]["music_path"]).resolve()
                manifest["output"]["sha256"] = sha256(output)
                manifest["mix"]["music_sha256"] = sha256(music)
                manifest["status"] = "RENDERED"
                manifest["gates"]["export_valid"] = False
                write_json_atomic(manifest_path, manifest)
                log_event(log_path, episode_id=episode_id, stage="RENDER", status="COMPLETED", output_sha256=manifest["output"]["sha256"])
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                manifest["status"] = "FAILED"
                manifest["gates"]["export_valid"] = False
                write_json_atomic(manifest_path, manifest)
                log_event(log_path, episode_id=episode_id, stage="RENDER", status="FAILED", error_class=type(exc).__name__, reason=str(exc))
                print(f"Render failed: {exc}", file=sys.stderr)
                return 1

        report_path = manifest_dir / f"{episode_id}-validation.json"
        result = subprocess.run([
            sys.executable,
            str(ROOT / "validate_episode.py"),
            "--manifest",
            str(manifest_path),
            "--report",
            str(report_path),
        ], check=False, timeout=600)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if result.returncode == 0:
            manifest["status"] = "TECH_VALIDATED"
            manifest["gates"]["export_valid"] = True
            log_event(log_path, episode_id=episode_id, stage="VALIDATE", status="TECH_VALIDATED", report=str(report_path))
        else:
            manifest["status"] = "FAILED"
            manifest["gates"]["export_valid"] = False
            log_event(log_path, episode_id=episode_id, stage="VALIDATE", status="FAILED", report=str(report_path))
        write_json_atomic(manifest_path, manifest)
        return result.returncode
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        log_event(log_path, episode_id=episode_id, stage="RUN", status="FINISHED", duration_ms=round((time.monotonic() - started) * 1000, 1))


if __name__ == "__main__":
    raise SystemExit(main())
