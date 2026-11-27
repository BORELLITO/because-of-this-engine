"""Fail-closed preflight for the staged Brazil Files Episode 001 case.

This preflight validates the selected case brief and reports missing editorial
artifacts before any Runflow preparation. It intentionally uses the staging
namespace because the legacy `episodes/episode-001` namespace is occupied.
It never researches URLs, calls providers, starts the engine or writes media.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from production.brazil_files_orchestrator import (
    BrazilFilesOrchestratorError,
    build_preparation_plan,
    validate_case_brief,
    validate_clip_selection_dossier,
    validate_flow_receipts,
)


STAGING_CASE_ROOT = Path("episodes/brazil-files/episode-001")
BRIEF_PATH = STAGING_CASE_ROOT / "case-brief.json"
DOSSIER_PATH = STAGING_CASE_ROOT / "clip-selection-dossier.json"
RECEIPTS_PATH = STAGING_CASE_ROOT / "flow-receipts.json"
LEGACY_NAMESPACE_ROOT = Path("episodes/episode-001")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_preflight(repo_root: Path = Path(".")) -> dict[str, Any]:
    """Evaluate the real staged case without inventing missing evidence."""

    root = repo_root.resolve()
    errors: list[str] = []
    evidence: dict[str, Any] = {
        "brief_path": str(BRIEF_PATH),
        "dossier_path": str(DOSSIER_PATH),
        "receipts_path": str(RECEIPTS_PATH),
        "legacy_namespace_path": str(LEGACY_NAMESPACE_ROOT),
    }

    brief_report: dict[str, Any]
    try:
        brief = _load_json(root / BRIEF_PATH)
        brief_report = validate_case_brief(brief)
        if brief_report["status"] != "PASS":
            errors.extend(f"brief:{error}" for error in brief_report["errors"])
        else:
            build_preparation_plan(brief)
    except (OSError, ValueError, json.JSONDecodeError, BrazilFilesOrchestratorError) as exc:
        brief_report = {"status": "BLOCKED", "errors": [str(exc)]}
        errors.append(f"brief:{exc}")

    dossier_path = root / DOSSIER_PATH
    if dossier_path.is_file():
        try:
            dossier_report = validate_clip_selection_dossier(_load_json(dossier_path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            dossier_report = {"status": "BLOCKED", "errors": [str(exc)]}
        if dossier_report["status"] != "PASS":
            errors.extend(f"dossier:{error}" for error in dossier_report.get("errors", []))
    else:
        dossier_report = {
            "status": "BLOCKED",
            "errors": ["16-beat clip-selection dossier is missing"],
        }
        errors.extend(f"dossier:{error}" for error in dossier_report["errors"])

    receipts_path = root / RECEIPTS_PATH
    if receipts_path.is_file():
        try:
            receipts_report = validate_flow_receipts(_load_json(receipts_path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            receipts_report = {"status": "FLOW_BLOCKED", "failed_blocks": [str(exc)]}
        if receipts_report["status"] != "FLOW_PASS":
            errors.extend(
                f"receipts:{block}"
                for block in receipts_report.get("failed_blocks", [])
            )
    else:
        receipts_report = {
            "status": "FLOW_BLOCKED",
            "failed_blocks": ["all 11 Brazil Files blocks; receipts file is missing"],
        }
        errors.extend(f"receipts:{block}" for block in receipts_report["failed_blocks"])

    legacy_manifest = root / LEGACY_NAMESPACE_ROOT / "manifest.json"
    namespace_collision = legacy_manifest.is_file()
    if namespace_collision:
        errors.append(
            "namespace:episodes/episode-001 is occupied by the preserved legacy package; "
            "staging namespace must remain episodes/brazil-files/episode-001"
        )

    return {
        "status": "BRAZIL_FILES_PREFLIGHT_PASS" if not errors else "BRAZIL_FILES_PREFLIGHT_BLOCKED",
        "case_id": brief_report.get("case_id"),
        "brief": brief_report,
        "dossier": dossier_report,
        "receipts": receipts_report,
        "namespace_collision": namespace_collision,
        "errors": errors,
        "evidence": evidence,
        "production_started": False,
        "runflow_handoff": "READY_FOR_RUNFLOW_PREPARATION_GATE" if not errors else "BLOCKED",
        "next_action": "resolve:" + ",".join(errors) if errors else "human_story_approval",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    result = evaluate_preflight(parser.parse_args().repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "BRAZIL_FILES_PREFLIGHT_PASS" else 1)
