#!/usr/bin/env python3
"""Download and hash the human-approved Episode 005 V2.1 preview visuals."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "curl", "--fail", "--location", "--retry", "2",
            "--retry-delay", "2", "--connect-timeout", "20",
            "--max-time", "180", "--max-filesize", "200M",
            url, "--output", str(target),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    assets = manifest.get("assets")
    if not isinstance(assets, list) or len(assets) != 16:
        raise SystemExit("Episode 005 preview requires exactly 16 manifest assets.")

    downloaded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise SystemExit("Every preview asset must be an object.")
        candidate_id = str(asset.get("candidate_id", "")).strip()
        media_url = str(asset.get("media_url", "")).strip()
        expected_sha = str(asset.get("sha256", "")).strip().lower()
        if not candidate_id or candidate_id in seen_ids:
            raise SystemExit(f"Invalid or duplicate candidate_id: {candidate_id!r}")
        if not media_url.startswith("https://"):
            raise SystemExit(f"Preview media URL must be HTTPS: {candidate_id}")
        if len(expected_sha) != 64:
            raise SystemExit(f"Preview asset has no valid SHA-256: {candidate_id}")
        seen_ids.add(candidate_id)
        target = args.output_root / candidate_id / "candidate.mp4"
        if target.is_file() and sha256_file(target) == expected_sha:
            state = "cached"
        else:
            if target.exists():
                target.unlink()
            download(media_url, target)
            actual_sha = sha256_file(target)
            if actual_sha != expected_sha:
                raise SystemExit(
                    f"SHA-256 mismatch for {candidate_id}: expected {expected_sha}, got {actual_sha}"
                )
            state = "downloaded"
        downloaded.append({
            "candidate_id": candidate_id,
            "path": str(target),
            "sha256": expected_sha,
            "state": state,
        })

    report = {
        "status": "V21_PREVIEW_VISUAL_INTAKE_PASS",
        "episode_id": "episode-005",
        "asset_count": len(downloaded),
        "assets": downloaded,
        "promotion": "PREVIEW_ONLY_NOT_PROMOTED",
        "global_catalog_updated": False,
        "drive_written": False,
    }
    report_path = args.output_root / "download-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
