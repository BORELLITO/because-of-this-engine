"""Single V2.1 read-only contract entrypoint; never renders or publishes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
from production.ledgers_v21 import load_registry,validate_no_reuse,validate_rights_ledger,validate_source_ledger
from production.package_gate_pre import evaluate_package_gate
from production.thumbnail_contract_v21 import validate_thumbnail_concept,validate_thumbnail_manifest

def evaluate(manifest: dict[str,Any],*,registry: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    package=evaluate_package_gate(manifest); source=validate_source_ledger(manifest); rights=validate_rights_ledger(manifest); reuse=validate_no_reuse(manifest,registry or []); concept=validate_thumbnail_concept(manifest)
    checks=[package,source,rights,reuse,concept]
    if manifest.get("thumbnail_manifest"): checks.append(validate_thumbnail_manifest(manifest["thumbnail_manifest"]))
    blocking=[item["gate"] if "gate" in item else item["ledger"] for item in checks if not (item["status"] == "PASS" or (item.get("gate") == "PACKAGE_GATE_PRE" and item["status"] == "PACKAGE_GATE_PASS"))]
    return {"implementation_id":manifest.get("implementation_id"),"audit_id":manifest.get("audit_id"),"status":"PASS" if not blocking else "BLOCKED","production_enablement":False,"media_generation":"NOT_RUN","tts":"NOT_RUN","render":"NOT_RUN","publication":"MANUAL_ONLY_NOT_RUN","checks":checks,"blocking_gates":blocking,"next_action":"human_story_approval" if not blocking else "resolve:"+",".join(blocking)}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--manifest",type=Path,required=True); parser.add_argument("--registry",type=Path); parser.add_argument("--report",type=Path); args=parser.parse_args()
    try:
        report=evaluate(json.loads(args.manifest.read_text(encoding="utf-8")),registry=load_registry(args.registry))
        if args.report: args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False)); return 0 if report["status"]=="PASS" else 1
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(f"V2.1 ENTRYPOINT BLOCKED: {exc}"); return 1
if __name__=="__main__": raise SystemExit(main())
