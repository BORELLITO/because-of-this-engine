#!/usr/bin/env python3
"""V1.1 READ_ONLY preflight. No media calls, renders, Drive changes or publication."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

TARGET_PROVIDER = "google_cloud_tts"
TARGET_DURATION = (50, 70)
ASSET_FIELDS = ("source_page_url", "license", "sha256", "rights_status", "drive_file_id")


def _load(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"Expected object in {path}")
    return result


def inspect(root: Path, candidate: Path | None = None) -> dict:
    root = root.resolve()
    issues = []

    def add(code: str, priority: str, detail: str) -> None:
        issues.append({"code": code, "priority": priority, "detail": detail})

    try:
        policy = _load(root / "production/active_engine_policy.json")
    except (OSError, ValueError) as exc:
        add("ACTIVE_POLICY_UNREADABLE", "P0", str(exc))
        policy = {}

    provider = policy.get("voice_provider")
    if provider != TARGET_PROVIDER:
        add("VOICE_PROVIDER_CONFLICT", "P0", f"target={TARGET_PROVIDER}; active={provider!r}")
    if policy.get("publication_policy") != "manual_only":
        add("AUTOMATIC_PUBLICATION_RISK", "P0", "manual_only is required")
    render = policy.get("render_contract") or {}
    if (render.get("duration_min_seconds"), render.get("duration_max_seconds")) != TARGET_DURATION:
        add("DURATION_LEGACY_UNVALIDATED", "P2", f"current={render}; target still candidate")
    canonical = root / "production/canonical_config.py"
    if canonical.is_file():
        match = re.search(r'^CANONICAL_ENGINE_VERSION\s*=\s*["\x27]([^"\x27]+)', canonical.read_text(encoding="utf-8"), re.M)
        if match and match.group(1) != policy.get("active_engine_version"):
            add("ENGINE_CONFIG_DRIFT", "P0", f"policy={policy.get('active_engine_version')}; config={match.group(1)}")
    else:
        add("CANONICAL_CONFIG_MISSING", "P0", "canonical config absent")
    readme = root / "README_PT.md"
    if readme.is_file() and "Piper TTS" in readme.read_text(encoding="utf-8") and provider != "piper_tts_local":
        add("LEGACY_README_DRIFT", "P2", "README_PT claims Piper as the active engine")
    final_workflow = root / ".github/workflows/episode-004-final-release.yml"
    if final_workflow.is_file() and not (root / "episodes/video-004/preview-manifest.json").is_file():
        add("FINAL_WORKFLOW_MANIFEST_NOT_IN_MAIN", "P0", "Default manifest is not on this branch")
    add("PLATFORM_SAFE_ZONE_NOT_EVIDENCED", "P1", "Requires rendered UI-overlaid TikTok and Shorts verification")
    add("HISTORICAL_MEDIA_CATALOG_NOT_EVIDENCED", "P0", "Require consumed asset registry across Git branches and Drive")
    add("WORK_EXECUTION_NOT_EVIDENCED", "P1", "Actions success is not proof of the Work interface")
    if candidate is not None:
        try:
            manifest = _load(candidate)
        except (OSError, ValueError) as exc:
            add("CANDIDATE_MANIFEST_UNREADABLE", "P0", str(exc))
            manifest = {}
        if manifest:
            if manifest.get("truth_mode") != "DECLARED_FICTION":
                add("NEW_STORY_TRUTH_MODE", "P1", "New Investigative Funeral Horror must be declared fiction")
            if manifest.get("lifecycle_status") in ("FINAL_APPROVED", "manually_published"):
                add("CANDIDATE_PREAPPROVED", "P0", "New story requires independent human approval")
            for i, scene in enumerate(manifest.get("scenes") or [], 1):
                asset = scene.get("asset") or {}
                missing = [f for f in ASSET_FIELDS if not asset.get(f)]
                if missing or asset.get("rights_status") != "APPROVED":
                    add("CANDIDATE_RIGHTS_MISSING", "P0", f"scene {i}: missing={missing}")
                if asset.get("perceptual_hash") and asset.get("perceptual_hash") == asset.get("sha256"):
                    add("SUSPECT_PERCEPTUAL_FINGERPRINT", "P1", f"scene {i}: verify real visual fingerprint")

    result = "BLOCKED" if any(i["priority"] in ("P0", "P1") for i in issues) else ("PARTIAL" if issues else "PASS")
    return {"audit_version": "1.1", "mode": "READ_ONLY", "status": result,
            "active_engine": policy.get("active_engine_version", "UNKNOWN"),
            "active_provider": provider or "UNKNOWN", "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = inspect(args.root, args.candidate)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return int(args.strict and report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
