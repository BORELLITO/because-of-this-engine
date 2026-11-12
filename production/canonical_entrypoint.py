"""Canonical V2.1 read-only orchestration entrypoint.

This is the only normal runtime entrypoint for the candidate. It validates a
complete production record and never calls TTS, media generation, rendering,
Drive writes or publication.
"""
from __future__ import annotations
import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from production.ledgers_v21 import RegistryError, load_registry, validate_no_reuse, validate_rights_ledger, validate_source_ledger
from production.package_gate_pre import evaluate_package_gate
from production.tts_contract_v21 import validate_tts_contract
from production.media_contract_v21 import validate_adapter_wiring, validate_audio_contract, validate_captions_contract, validate_drive_contract, validate_render_contract
from production.thumbnail_contract_v21 import validate_thumbnail_concept, validate_thumbnail_files, validate_thumbnail_manifest
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
from production.audio_history_audit_v21 import audit as audit_audio_history
from production.historical_receipt_recovery_v21 import build_recovery_report
from production.drive_evidence_reconciliation_v21 import build_reconciliation_report
from production.rights_autonomy_v21 import audit_repository as audit_autonomous_rights
from production.scene_disclosures_v21 import audit_repository as audit_scene_disclosures

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "production-record-3.1.0.json"

def _schema_error(record: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    failures.extend(f"missing:{field}" for field in schema.get("required", []) if field not in record)
    for field, rules in schema.get("properties", {}).items():
        if field not in record:
            continue
        value = record[field]
        expected = rules.get("type")
        if expected == "string" and not isinstance(value, str):
            failures.append(f"{field} must be string")
        elif expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            failures.append(f"{field} must be integer")
        elif expected == "array" and not isinstance(value, list):
            failures.append(f"{field} must be array")
        elif expected == "object" and not isinstance(value, dict):
            failures.append(f"{field} must be object")
        if isinstance(value, str) and "minLength" in rules and len(value) < rules["minLength"]:
            failures.append(f"{field} must not be empty")
        if "const" in rules and value != rules["const"]:
            failures.append(f"{field} must equal {rules['const']!r}")
        if "enum" in rules and value not in rules["enum"]:
            failures.append(f"{field} has invalid value:{value}")
        if "minimum" in rules and isinstance(value, int) and value < rules["minimum"]:
            failures.append(f"{field} is below minimum:{rules['minimum']}")
        if "maximum" in rules and isinstance(value, int) and value > rules["maximum"]:
            failures.append(f"{field} is above maximum:{rules['maximum']}")
    return failures

def validate_production_schema(record: Mapping[str, Any], schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"gate": "PRODUCTION_RECORD_SCHEMA", "status": "BLOCKED", "failures": [f"schema unavailable:{exc}"]}
    failures = _schema_error(record, schema)
    return {"gate": "PRODUCTION_RECORD_SCHEMA", "status": "PASS" if not failures else "BLOCKED", "failures": failures, "schema": schema.get("$id")}

def evaluate(manifest: dict[str, Any], *, registry: list[dict[str, Any]] | None = None, repo_root: Path | None = None) -> dict[str, Any]:
    schema = validate_production_schema(manifest)
    package = evaluate_package_gate(manifest)
    source = validate_source_ledger(manifest)
    rights = validate_rights_ledger(manifest)
    reuse = validate_no_reuse(manifest, registry)
    concept = validate_thumbnail_concept(manifest)
    tts = validate_tts_contract(manifest)
    audio = validate_audio_contract(manifest)
    captions = validate_captions_contract(manifest)
    render = validate_render_contract(manifest)
    drive = validate_drive_contract(manifest)
    adapter_wiring = validate_adapter_wiring(manifest, repo_root)
    thumbnail_manifest = manifest.get("thumbnail_manifest")
    thumbnail = validate_thumbnail_manifest(thumbnail_manifest) if isinstance(thumbnail_manifest, dict) else {"gate": "THUMBNAIL_QA", "status": "BLOCKED", "failures": ["thumbnail_manifest is mandatory"]}
    checks = [schema, package, source, rights, reuse, concept, tts, audio, captions, render, drive, adapter_wiring, thumbnail]
    if repo_root is not None and thumbnail["status"] == "PASS":
        checks.append(validate_thumbnail_files(thumbnail_manifest, repo_root))
    # A structurally valid rights ledger cannot certify a different media
    # manifest. This check is mandatory for real repository-backed records.
    if repo_root is not None:
        checks.append(validate_visual_rights_consistency(manifest, repo_root=repo_root))
        audio_history = audit_audio_history(repo_root)
        # Keep the public blocking contract consolidated under
        # AUDIO_HISTORY_COVERAGE while attaching the stricter recovery
        # inventory as a nested, fail-closed sub-audit.
        recovery_registry_path = repo_root / "episodes" / "audio-rendered-master-registry.json"
        recovery_report_path = repo_root / "reports" / "historical-receipt-recovery-v21.json"
        if recovery_registry_path.exists() and recovery_report_path.exists():
            try:
                recovery_registry = json.loads(recovery_registry_path.read_text(encoding="utf-8"))
                recovery = build_recovery_report(recovery_registry)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                recovery = {
                    "gate": "AUDIO_HISTORY_RECEIPT_RECOVERY",
                    "status": "BLOCKED",
                    "failures": [f"recovery inventory unavailable or invalid:{exc}"],
                }
            audio_history = dict(audio_history)
            audio_history["historical_receipt_recovery"] = recovery
            if recovery.get("status") != "PASS":
                audio_history["failures"] = list(audio_history.get("failures", []))
                audio_history["failures"].append("historical receipt recovery gate is blocked")
                audio_history["historical_receipt_recovery_status"] = "BLOCKED"
            else:
                audio_history["historical_receipt_recovery_status"] = "PASS"
        drive_evidence_path = repo_root / "reports" / "drive-evidence-reconciliation-v21.json"
        if drive_evidence_path.exists():
            try:
                drive_evidence = json.loads(drive_evidence_path.read_text(encoding="utf-8"))
                drive_reconciliation = build_reconciliation_report(recovery_registry, drive_evidence)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                drive_reconciliation = {
                    "gate": "AUDIO_HISTORY_DRIVE_EVIDENCE_RECONCILIATION",
                    "status": "BLOCKED",
                    "promotion_status": "BLOCKED",
                    "blocking_reasons": [f"Drive evidence reconciliation unavailable or invalid:{exc}"],
                }
            audio_history["drive_evidence_reconciliation"] = drive_reconciliation
            audio_history["drive_evidence_reconciliation_status"] = drive_reconciliation.get("status", "BLOCKED")
            if drive_reconciliation.get("status") != "PASS":
                audio_history["failures"] = list(audio_history.get("failures", []))
                audio_history["failures"].append("historical Drive evidence reconciliation is blocked")
        checks.append(audio_history)
        checks.append(audit_autonomous_rights(manifest, repo_root=repo_root))
        checks.append(audit_scene_disclosures(manifest, repo_root=repo_root))
    blocking = [item.get("gate") or item.get("ledger") for item in checks if item["status"] not in {"PASS", "PACKAGE_GATE_PASS"}]
    return {"implementation_id": manifest.get("implementation_id"), "audit_id": manifest.get("audit_id"), "status": "PASS" if not blocking else "BLOCKED", "production_enablement": False, "media_generation": "NOT_RUN", "tts": "NOT_RUN", "render": "NOT_RUN", "publication": "MANUAL_ONLY_NOT_RUN", "checks": checks, "blocking_gates": blocking, "next_action": "human_story_approval" if not blocking else "resolve:" + ",".join(blocking)}

def run_manifest(manifest_path: Path, *, repo_root: Path, report_path: Path | None = None, registry_path: Path | None = None) -> int:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"status": "BLOCKED", "production_enablement": False, "media_generation": "NOT_RUN", "tts": "NOT_RUN", "render": "NOT_RUN", "publication": "MANUAL_ONLY_NOT_RUN", "blocking_gates": ["CANONICAL_ENTRYPOINT"], "next_action": f"resolve:CANONICAL_ENTRYPOINT:{exc}"}
    else:
        try:
            registry = load_registry(registry_path or (repo_root / "episodes" / "asset-memory-registry.json"))
            report = evaluate(manifest, registry=registry, repo_root=repo_root)
        except RegistryError as exc:
            report = evaluate(manifest, registry=[], repo_root=repo_root)
            report["registry_error"] = str(exc)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    return run_manifest(args.manifest.resolve(), repo_root=args.repo_root.resolve(), report_path=args.report.resolve() if args.report else None, registry_path=args.registry.resolve() if args.registry else None)

if __name__ == "__main__":
    raise SystemExit(main())
