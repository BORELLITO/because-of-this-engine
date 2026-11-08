"""BECAUSE OF THIS V2.1 — fail-closed *incremental* monetary cost gate.

No unverified API free tier, spending account, quota, token or API key may
authorize a potentially charged network call. Existing Charon files may be
reused offline. This guard cannot inspect provider billing/account settings:
when a provider cannot prove a hard $0 cap via an independently enforceable
mechanism, the call is BLOCKED rather than risk a charge.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POLICY_PATH = Path(__file__).resolve().parent / "active_engine_policy.json"

OFFLINE_OPERATIONS = frozenset({
    "existing_charon_audio_reuse",
    "ffmpeg_local_mix",
    "offline_media_qa",
    "music_rights_read_only_audit",
    "source_fingerprint_local",
    "offline_python_tests",
})
KNOWN_EXTERNAL_OPERATIONS = frozenset({
    "gemini_tts_generate_content",
    "gemini_batch_generate",
    "paid_stock_purchase",
    "paid_render_api",
    "cloud_paid_render",
    "unverified_external_api",
})


class ZeroCostViolation(RuntimeError):
    pass


def evaluate_cost(operation: str, *, policy: dict[str, Any] | None = None,
                  policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    reasons = []
    try:
        if policy is None:
            policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        if not isinstance(policy, dict):
            raise ValueError("cost policy document must be an object")
        cost = policy.get("zero_additional_cost_policy")
        if not isinstance(cost, dict):
            raise ValueError("zero_additional_cost_policy missing")
        if (cost.get("mode") != "ABSOLUTE_ZERO_ADDITIONAL_SPEND"
                or cost.get("max_incremental_spend_usd") != 0
                or cost.get("allow_paid_apis") is not False
                or cost.get("allow_new_unverified_tts_calls") is not False
                or cost.get("external_spend_hard_cap_verified") is not False
                or cost.get("default_for_unknown_external_cost") != "BLOCK"):
            raise ValueError("frozen no-cost restrictions invalid")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        reasons.append("no-cost policy unreadable or unsafe: " + str(exc))

    if operation in OFFLINE_OPERATIONS:
        # Even offline use is blocked when a trusted financial policy is absent.
        status = "PASS" if not reasons else "BLOCKED"
    else:
        status = "BLOCKED"
        if operation in KNOWN_EXTERNAL_OPERATIONS:
            reasons.append("provider/account billing cannot be proven hard-capped at $0")
        else:
            reasons.append("unknown or potentially billable action is denied by default")

    return {
        "gate": "ABSOLUTE_ZERO_INCREMENTAL_COST_V21",
        "operation": operation,
        "status": status,
        "failures": reasons,
        "external_request_authorized": False,
        "new_charge_authorized": False,
        "publication_authorized": False,
        "note": ("Provider free-tier price lists, API keys, self-declared flags and "
                 "GitHub public repository status are NOT account-level billing proofs."),
    }


def assert_zero_cost(operation: str, *, policy_path: Path = POLICY_PATH) -> None:
    result = evaluate_cost(operation, policy_path=policy_path)
    if result["status"] != "PASS":
        raise ZeroCostViolation("; ".join(result["failures"]))


def audit_repository(repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    errors = []
    for operation in ("existing_charon_audio_reuse", "offline_media_qa",
                      "ffmpeg_local_mix"):
        check = evaluate_cost(
            operation, policy_path=root / "production" / "active_engine_policy.json")
        if check["status"] != "PASS":
            errors.append(operation + ": " + "; ".join(check["failures"]))

    for operation in KNOWN_EXTERNAL_OPERATIONS:
        check = evaluate_cost(
            operation, policy_path=root / "production" / "active_engine_policy.json")
        if check["status"] != "BLOCKED":
            errors.append(operation + ": forbidden charge path was opened")
    for ep in ("005", "006"):
        workflow = root / ".github" / "workflows" / (
            "episode" + ep + "-gemini-charon-narration.yml")
        if not workflow.is_file() or (
                "python -m production.zero_cost_v21 --operation gemini_tts_generate_content"
                not in workflow.read_text(encoding="utf-8")):
            errors.append("episode" + ep + " Gemini workflow lacks no-cost preflight")
    tts = root / "production" / "gemini_tts.py"
    if not tts.is_file() or 'assert_zero_cost("gemini_tts_generate_content")' not in tts.read_text(encoding="utf-8"):
        errors.append("Gemini network call site lacks the mandatory absolute zero-cost gate")

    return {
        "gate": "ABSOLUTE_ZERO_INCREMENTAL_COST_V21",
        "status": "PASS" if not errors else "BLOCKED",
        "failures": errors,
        "production_enablement": False,
        "external_tts_calls_enabled": False,
        "note": "Verifies this canonical code surface, not billing settings of third-party accounts.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=str, default="gemini_tts_generate_content")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--audit-repository", action="store_true")
    a = parser.parse_args()
    result = (audit_repository(a.repo_root) if a.audit_repository
              else evaluate_cost(a.operation))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
