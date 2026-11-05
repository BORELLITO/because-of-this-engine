"""Fail-closed audit of the V2.1 singleton runtime policy."""
from __future__ import annotations
import json
from pathlib import Path

FORBIDDEN_PRODUCTION_FALLBACKS = ("piper_tts", "edge_tts", "cloud_tts", "production/v7_orchestrator.py", "production/v7_contract.py", "production/render_video_episode.py", "production/gemini_tts.py")
EXEMPT_WORKFLOWS = {"v21-integration-readonly.yml", "video-engine-ci.yml", "github-housekeeping.yml"}

def audit(repo_root: Path) -> dict:
    root = repo_root.resolve()
    failures: list[str] = []
    policy_path = root / "production" / "active_engine_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("active_engine_version") != "2.1":
        failures.append("active policy is not V2.1")
    if policy.get("canonical_entrypoint") != "production/canonical_entrypoint.py":
        failures.append("canonical_entrypoint mismatch")
    if policy.get("production_enablement") is not False:
        failures.append("production_enablement must remain false in candidate")
    if policy.get("legacy_policy", {}).get("status") != "legacy_rollback_only":
        failures.append("legacy policy missing")
    workflow_root = root / ".github" / "workflows"
    workflows = sorted(workflow_root.glob("*.yml")) if workflow_root.exists() else []
    for path in workflows:
        if path.name in EXEMPT_WORKFLOWS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(token in text for token in FORBIDDEN_PRODUCTION_FALLBACKS):
            failures.append(f"legacy/provider reference requires reconciliation:{path.relative_to(root).as_posix()}")
    if not (workflow_root / "v21-integration-readonly.yml").is_file():
        failures.append("canonical V2.1 workflow is missing")
    return {"status": "V21_SINGLETON_PASS" if not failures else "V21_SINGLETON_BLOCKED", "canonical_entrypoint": policy.get("canonical_entrypoint"), "failures": failures, "workflow_count": len(workflows)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    result = audit(parser.parse_args().repo_root.resolve())
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"].endswith("PASS") else 1)
