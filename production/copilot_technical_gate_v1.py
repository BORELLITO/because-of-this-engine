"""Consolidated, read-only technical gate for the canonical copilot.

The gate combines scope, privacy, contract, compilation and regression checks.
It never starts the engine, writes project memory, calls TTS, renders media or
publishes anything.
"""
from __future__ import annotations

import argparse
import compileall
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


COPILOT_SCOPE_ALLOWLIST = frozenset(
    {
        ".github/workflows/copilot-technical-gate.yml",
        "docs/COPILOTO_CANONICO_V1.md",
        "production/copilot_contract_v1.json",
        "production/copilot_queue_v1.py",
        "production/copilot_technical_gate_v1.py",
        "tests/test_copilot_contract.py",
        "tests/test_copilot_levels.py",
        "tests/test_copilot_queue_v1.py",
    }
)


def scope_failures(changed_paths: list[str]) -> list[str]:
    return sorted({path for path in changed_paths if path not in COPILOT_SCOPE_ALLOWLIST})


def contract_failures(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    serialization = contract.get("serialization")
    if not isinstance(serialization, dict):
        return ["serialization contract is missing"]
    expected = {
        "mode": "GLOBAL_SINGLE_CANONICAL_ENGINE",
        "workflow_concurrency_group": "because-of-this-canonical-engine",
        "parallel_production_runs": False,
        "cancel_in_progress": False,
        "memory_sync_before_and_after": True,
        "max_mutating_subagents": 1,
        "subagent_dispatch": "SEQUENTIAL_ISOLATED_ARTIFACT",
    }
    for key, value in expected.items():
        if serialization.get(key) != value:
            failures.append(f"serialization.{key} drifted")
    activation = contract.get("production_activation")
    if not isinstance(activation, dict) or activation.get("enabled") is not False:
        failures.append("production activation must remain disabled")
    if isinstance(activation, dict) and activation.get("fallbacks_allowed") is not False:
        failures.append("fallbacks must remain disabled")
    agents = contract.get("subagents")
    if not isinstance(agents, list) or len(agents) != 8:
        failures.append("exactly eight canonical subagents are required")
    elif any(agent.get("can_start_engine") is not False for agent in agents if isinstance(agent, dict)):
        failures.append("a subagent can start the engine")
    levels = contract.get("levels")
    if not isinstance(levels, dict) or set(levels) != {"analysis", "technical_gate"}:
        failures.append("two-level copilot contract is missing")
    return failures


def _changed_paths(root: Path, base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _run_regressions(root: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_copilot_*.py", "-v"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output[-4000:]


def run_gate(root: Path, base_ref: str = "main") -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, Any]] = []

    try:
        changed = _changed_paths(root, base_ref)
        out_of_scope = scope_failures(changed)
        checks.append({"id": "scope", "status": "PASS" if not out_of_scope else "BLOCKED", "changed": changed, "failures": out_of_scope})
    except (OSError, subprocess.CalledProcessError) as exc:
        checks.append({"id": "scope", "status": "BLOCKED", "failures": [f"cannot inspect diff: {exc}"]})

    contract_path = root / "production" / "copilot_contract_v1.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        failures = contract_failures(contract)
        checks.append({"id": "contract", "status": "PASS" if not failures else "BLOCKED", "failures": failures})
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        checks.append({"id": "contract", "status": "BLOCKED", "failures": [f"unreadable contract: {exc}"]})

    compiled = compileall.compile_dir(str(root / "production"), quiet=1)
    checks.append({"id": "compilation", "status": "PASS" if compiled else "BLOCKED", "failures": [] if compiled else ["production compilation failed"]})

    try:
        from production.public_secret_guard import scan_paths

        privacy = scan_paths(root)
        checks.append({"id": "privacy", "status": "PASS" if privacy["status"] == "PUBLIC_SECRET_GUARD_PASS" else "BLOCKED", "failures": privacy["failures"]})
    except Exception as exc:  # pragma: no cover - defensive gate boundary
        checks.append({"id": "privacy", "status": "BLOCKED", "failures": [f"privacy guard unavailable: {exc}"]})

    regressions_pass, regression_output = _run_regressions(root)
    checks.append({"id": "regressions", "status": "PASS" if regressions_pass else "BLOCKED", "failures": [] if regressions_pass else [regression_output]})

    status = "COPILOT_TECHNICAL_GATE_PASS" if all(item["status"] == "PASS" for item in checks) else "COPILOT_TECHNICAL_GATE_BLOCKED"
    return {"status": status, "checks": checks, "production_started": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref", default="main")
    args = parser.parse_args()
    report = run_gate(args.repo_root, base_ref=args.base_ref)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "COPILOT_TECHNICAL_GATE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

