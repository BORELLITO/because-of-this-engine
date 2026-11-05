"""Audit the V2.1 singleton policy without executing media work."""
from __future__ import annotations
import json
from pathlib import Path

FORBIDDEN_PRODUCTION_FALLBACKS = ("piper_tts", "edge_tts", "cloud_tts", "v7_orchestrator.py", "v7_contract.py")
def audit(repo_root: Path) -> dict:
    policy=json.loads((repo_root/"production/active_engine_policy.json").read_text(encoding="utf-8"))
    failures=[]
    if policy.get("canonical_entrypoint") != "production/canonical_entrypoint.py": failures.append("canonical_entrypoint mismatch")
    if policy.get("production_enablement") is not False: failures.append("production_enablement must remain false in candidate")
    if policy.get("legacy_policy",{}).get("status") != "legacy_rollback_only": failures.append("legacy policy missing")
    workflows=list((repo_root/".github/workflows").glob("*.yml")) if (repo_root/".github/workflows").exists() else []
    for path in workflows:
        text=path.read_text(encoding="utf-8",errors="replace")
        if path.name == "v21-integration-readonly.yml": continue
        if any(token in text for token in FORBIDDEN_PRODUCTION_FALLBACKS):
            failures.append(f"legacy/provider reference requires reconciliation:{path.as_posix()}")
    return {"status":"V21_SINGLETON_PASS" if not failures else "V21_SINGLETON_BLOCKED","canonical_entrypoint":policy.get("canonical_entrypoint"),"failures":failures,"workflow_count":len(workflows)}
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",type=Path,default=Path("."))
    result=audit(parser.parse_args().repo_root.resolve()); print(json.dumps(result,ensure_ascii=False)); raise SystemExit(0 if result["status"].endswith("PASS") else 1)
