#!/usr/bin/env python3
"""V6 master-prompt contract and fail-closed integration gate.

This module makes the uploaded V6 prompt executable as a repository contract.
It does not render or publish media. It verifies that the prompt, schema,
canonical engine and lifecycle model are present and that every production
manifest carries the active contract identity.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

MASTER_PROMPT_VERSION = "6.0"
MASTER_PROMPT_PATH = Path("docs/PROMPT_MESTRE_BECAUSE_OF_THIS_FINAL_V6_EXECUTAVEL.txt")
MASTER_PROMPT_SHA256 = "6792a1b3a85b4069c100f9b49cc04b7a169e92cc3a54d9abdf690c78efad74ed"
SCHEMA_ID = "because-of-this://schemas/production-record/2.1.0"
SCHEMA_PATH = Path("production/schemas/production-record-2.1.0.json")
GATE_ORDER = tuple(code for code, _ in (
    ("G0", "PRE_FLIGHT"),
    ("G1", "SCRIPT_SUSPENSE"),
    ("G2", "RIGHTS_ORIGINALITY_FICTION"),
    ("G3", "VISUAL_CLIPS"),
    ("G4", "NARRATION"),
    ("G5", "AUDIO_MIX"),
    ("G6", "CAPTIONS_KARAOKE"),
    ("G7", "PACKAGING"),
    ("G8", "PREVIEW"),
    ("G9", "RENDER_TECHNICAL"),
    ("G10", "HUMAN_APPROVAL"),
    ("G11", "POST_PUBLICATION"),
))
GATE_NAMES = {
    "G0": "PRE_FLIGHT",
    "G1": "SCRIPT_SUSPENSE",
    "G2": "RIGHTS_ORIGINALITY_FICTION",
    "G3": "VISUAL_CLIPS",
    "G4": "NARRATION",
    "G5": "AUDIO_MIX",
    "G6": "CAPTIONS_KARAOKE",
    "G7": "PACKAGING",
    "G8": "PREVIEW",
    "G9": "RENDER_TECHNICAL",
    "G10": "HUMAN_APPROVAL",
    "G11": "POST_PUBLICATION",
}
GATE_STATES = {"pending","running","passed","failed","blocked"}
PRODUCTION_STATES = {"draft","in_production","pending_validation","human_review","approved_for_publication","manually_published","blocked","canceled"}
COMPONENT_STATES = {"draft","generated","pending_validation","approved","needs_correction","rejected","archived","corrupted","legally_removed"}
INCIDENT_STATES = {"open","contained","recovering","resolved","rollback_required","safe_mode"}
ENGINE_VERSION_STATES = {"candidate","active","stable","rollback_eligible","unstable","archived"}

class MasterPromptContractError(ValueError):
    """Raised when the V6 contract is absent, altered or incomplete."""

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MasterPromptContractError(f"{path} must contain a JSON object.")
    return value

def validate_master_prompt(repo_root: Path) -> dict[str, Any]:
    prompt_path, schema_path = repo_root / MASTER_PROMPT_PATH, repo_root / SCHEMA_PATH
    if not prompt_path.is_file():
        raise MasterPromptContractError(f"missing master prompt: {MASTER_PROMPT_PATH}")
    actual_hash = _sha256(prompt_path)
    if actual_hash != MASTER_PROMPT_SHA256:
        raise MasterPromptContractError(f"master prompt hash mismatch: expected {MASTER_PROMPT_SHA256}, got {actual_hash}")
    if not schema_path.is_file():
        raise MasterPromptContractError(f"missing production schema: {SCHEMA_PATH}")
    schema = _load_json(schema_path)
    if schema.get("$id") != SCHEMA_ID or schema.get("properties",{}).get("schema_version",{}).get("const") != "2.1.0":
        raise MasterPromptContractError("production schema is not the canonical 2.1.0 schema")
    text = prompt_path.read_text(encoding="utf-8")
    required_markers = ("G0 — Pré-voo","G11 — Verificação pós-publicação","because-of-this://schemas/production-record/2.1.0","Mantenha duas versões estáveis disponíveis para rollback.","Nenhum vídeo pode ser publicado automaticamente.")
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise MasterPromptContractError(f"master prompt is incomplete: {missing}")
    return {"status":"MASTER_PROMPT_V6_PASS","version":MASTER_PROMPT_VERSION,"sha256":actual_hash,"schema_id":SCHEMA_ID,"gates":list(GATE_ORDER)}

def validate_manifest_contract(manifest: dict[str, Any], *, source_label: str = "manifest") -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise MasterPromptContractError(f"{source_label} must be a JSON object.")
    if manifest.get("master_prompt_version") != MASTER_PROMPT_VERSION:
        raise MasterPromptContractError(f"{source_label} must declare master_prompt_version={MASTER_PROMPT_VERSION!r}")
    if manifest.get("master_prompt_sha256") != MASTER_PROMPT_SHA256:
        raise MasterPromptContractError(f"{source_label} has an invalid master prompt hash")
    if manifest.get("production_schema") != SCHEMA_ID:
        raise MasterPromptContractError(f"{source_label} must declare production_schema={SCHEMA_ID!r}")
    if manifest.get("human_approval_required") is not True:
        raise MasterPromptContractError(f"{source_label} must require human approval")
    return {"status":"MANIFEST_V6_CONTRACT_PASS","source":source_label,"master_prompt_version":MASTER_PROMPT_VERSION,"production_schema":SCHEMA_ID,"human_approval_required":True}

def validate_production_record(record: dict[str, Any]) -> dict[str, Any]:
    required = ("schema_version","schema_id","story_id","engine_bundle_id","engine_version","production_id","production_version","states","gates","artifacts","next_action")
    missing = [key for key in required if key not in record]
    if missing:
        raise MasterPromptContractError(f"production record missing fields: {missing}")
    if record.get("schema_version") != "2.1.0" or record.get("schema_id") != SCHEMA_ID:
        raise MasterPromptContractError("production record must use schema 2.1.0")
    if not isinstance(record.get("states"), dict) or not isinstance(record.get("gates"), dict):
        raise MasterPromptContractError("production record states and gates must be objects")
    required_collections = (
        "module_ids", "scene_ids", "beat_ids", "attempts", "fixes", "approvals",
        "incidents", "rollbacks", "hashes", "origins", "licenses",
    )
    missing_collections = [key for key in required_collections if key not in record]
    if missing_collections:
        raise MasterPromptContractError(f"production record missing audit collections: {missing_collections}")
    if not all(isinstance(record[key], (list, dict)) for key in required_collections):
        raise MasterPromptContractError("production record audit collections must be arrays or objects")
    if tuple(record["gates"]) != GATE_ORDER:
        raise MasterPromptContractError("production record gates must contain the exact ordered G0-G11 contract")
    for gate, value in record["gates"].items():
        if not isinstance(value, dict) or value.get("name") != GATE_NAMES[gate]:
            raise MasterPromptContractError(f"{gate} has the wrong canonical gate name")
        state = value.get("state")
        if state not in GATE_STATES:
            raise MasterPromptContractError(f"{gate} has invalid gate state")
        if not isinstance(value.get("evidence"), str) or not value["evidence"].strip():
            raise MasterPromptContractError(f"{gate} must contain evidence")
    for artifact in record["artifacts"]:
        if not isinstance(artifact, dict):
            raise MasterPromptContractError("every artifact must be an object")
        for key in ("artifact_id", "kind", "sha256", "origin"):
            if not isinstance(artifact.get(key), str) or not artifact[key].strip():
                raise MasterPromptContractError(f"artifact missing {key}")
    return {"status":"PRODUCTION_RECORD_SCHEMA_PASS","schema_id":SCHEMA_ID,"gate_order":list(GATE_ORDER)}

def audit_repo(repo_root: Path, manifest_paths: list[Path]) -> dict[str, Any]:
    prompt_report = validate_master_prompt(repo_root)
    manifests = []
    for relative in manifest_paths:
        path = (repo_root / relative).resolve()
        manifests.append(validate_manifest_contract(_load_json(path), source_label=str(relative)))
    return {"status":"V6_ENGINE_CONTRACT_PASS","prompt":prompt_report,"manifests":manifests,"gate_order":list(GATE_ORDER),"state_models":{"production":sorted(PRODUCTION_STATES),"component":sorted(COMPONENT_STATES),"gate":sorted(GATE_STATES),"incident":sorted(INCIDENT_STATES),"engine_version":sorted(ENGINE_VERSION_STATES)},"publication":"MANUAL_ONLY","legacy_execution_source":"BLOCKED"}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    parser.add_argument("--manifest",action="append",type=Path)
    args = parser.parse_args()
    try:
        root=args.repo_root.resolve()
        report=audit_repo(root,args.manifest or []) if args.manifest else validate_master_prompt(root)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    except (OSError,UnicodeError,json.JSONDecodeError,MasterPromptContractError) as exc:
        print(f"V6 ENGINE CONTRACT BLOCKED: {exc}")
        return 1
if __name__ == "__main__":
    raise SystemExit(main())
