#!/usr/bin/env python3
"""Small local orchestrator for one independent episode.

It intentionally stays local and deterministic. It refuses to render over an
APPROVED episode and records the new output hash before the fail-closed gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "mars-climate-orbiter-episode.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and validate one independent BECAUSE OF THIS episode.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--render", action="store_true", help="Run the local FFmpeg render before validation.")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.render:
        if manifest.get("approval_status") == "APPROVED":
            print("Refusing to overwrite an APPROVED episode. Create a new version.", file=sys.stderr)
            return 2
        subprocess.run([sys.executable, str(ROOT / "render_mars_final.py")], check=True)
        output = ROOT / manifest["output"]["path"]
        manifest["output"]["sha256"] = sha256(output)
        manifest["status"] = "RENDERED"
        manifest["gates"]["export_valid"] = False
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_path = ROOT / f"{manifest['episode_id']}-validation.json"
    result = subprocess.run([
        sys.executable,
        str(ROOT / "validate_episode.py"),
        "--manifest",
        str(manifest_path),
        "--report",
        str(report_path),
    ], check=False)
    if result.returncode == 0:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "TECH_VALIDATED"
        manifest["gates"]["export_valid"] = True
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
