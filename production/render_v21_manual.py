"""Manual-only V2.1 render gate.

This module is the active render boundary for the candidate. It performs only
fail-closed preflight validation until the policy and the episode production
record explicitly authorize execution. It never falls back to the archived
renderer, never publishes, and never writes Drive.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from production.thumbnail_contract_v21 import (
    validate_thumbnail_files,
    validate_thumbnail_manifest,
)

POLICY_PATH = Path(__file__).resolve().parent / "active_engine_policy.json"
EXPECTED_ENTRYPOINT = "production/canonical_entrypoint.py"
EXPECTED_RENDER_ENTRYPOINT = "production/render_v21_manual.py"
RENDER_MODES = {"preview", "final"}


class ManualRenderGateError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManualRenderGateError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManualRenderGateError(f"JSON object required: {path}")
    return value


def _policy(policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = _read_json(policy_path)
    if policy.get("active_engine_version") != "2.1":
        raise ManualRenderGateError("active policy is not V2.1")
    if policy.get("canonical_entrypoint") != EXPECTED_ENTRYPOINT:
        raise ManualRenderGateError("canonical entrypoint mismatch")
    configured = policy.get("manual_render_entrypoint", EXPECTED_RENDER_ENTRYPOINT)
    if configured != EXPECTED_RENDER_ENTRYPOINT:
        raise ManualRenderGateError("manual render entrypoint mismatch")
    if policy.get("publication_policy") != "manual_only":
        raise ManualRenderGateError("publication must remain manual_only")
    return policy


def validate_request(
    record: dict[str, Any],
    *,
    repo_root: Path,
    mode: str = "preview",
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    if mode not in RENDER_MODES:
        raise ManualRenderGateError(f"unsupported render mode: {mode}")
    policy = _policy(policy_path)
    failures: list[str] = []

    if policy.get("production_enablement") is not True:
        failures.append("active policy production_enablement=false")
    if record.get("production_enablement") is not True:
        failures.append("production record production_enablement=false")
    authorization = record.get("render_authorization")
    if not isinstance(authorization, dict) or authorization.get("status") != "APPROVED":
        failures.append("explicit render_authorization.status=APPROVED is required")
    contract = record.get("render_contract")
    if not isinstance(contract, dict):
        failures.append("render_contract is required")
    else:
        expected = {"width": 1080, "height": 1920, "fps": 60}
        for field, value in expected.items():
            if contract.get(field) != value:
                failures.append(f"render_contract.{field} must equal {value}")
        if contract.get("render_executed") is not False:
            failures.append("render_contract.render_executed must be false before dispatch")

    thumbnail = record.get("thumbnail_manifest")
    if not isinstance(thumbnail, dict):
        failures.append("final thumbnail_manifest is required before render")
    else:
        report = validate_thumbnail_manifest(thumbnail)
        if report["status"] != "PASS":
            failures.extend(f"thumbnail:{item}" for item in report["failures"])
        else:
            files = validate_thumbnail_files(thumbnail, repo_root)
            if files["status"] != "PASS":
                failures.extend(f"thumbnail_files:{item}" for item in files["failures"])

    return {
        "status": "V21_MANUAL_RENDER_PREFLIGHT_PASS" if not failures else "V21_MANUAL_RENDER_BLOCKED",
        "mode": mode,
        "production_enablement": policy.get("production_enablement") is True,
        "render": "NOT_RUN",
        "publication": "MANUAL_ONLY_NOT_RUN",
        "failures": failures,
        "next_action": "execute_manual_render_after_all_gates_pass" if not failures else "resolve:" + ",".join(failures),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--mode", choices=sorted(RENDER_MODES), default="preview")
    args = parser.parse_args(argv)
    try:
        record = _read_json(args.record.resolve())
        report = validate_request(record, repo_root=args.repo_root.resolve(), mode=args.mode)
    except (ManualRenderGateError, OSError, ValueError) as exc:
        report = {
            "status": "V21_MANUAL_RENDER_BLOCKED",
            "render": "NOT_RUN",
            "publication": "MANUAL_ONLY_NOT_RUN",
            "failures": [str(exc)],
            "next_action": "resolve:MANUAL_RENDER_GATE",
        }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "V21_MANUAL_RENDER_PREFLIGHT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
