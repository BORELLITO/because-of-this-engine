#!/usr/bin/env python3
"""Executable V7.1 prompt, schema, manifest and gate contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from production.canonical_config import (
    CANONICAL_ENGINE_VERSION,
    CANONICAL_PROFILE_FINGERPRINT,
    CANONICAL_PROFILE_ID,
    CANONICAL_SCHEMA_ID,
    CanonicalConfigError,
    validate_canonical_manifest,
)
from production.production_record_v7 import (
    GATE_NAMES,
    GATE_ORDER,
    ProductionRecordError,
    validate_record,
)

PROMPT_VERSION = "7.1"
PROMPT_PATH = Path("docs/PROMPT_MESTRE_BECAUSE_OF_THIS_V7_1_EDGE_TTS_INTEGRADO.txt")
SCHEMA_PATH = Path("production/schemas/production-record-3.0.0.json")
PROMPT_SHA256 = "9bd5a8854436418c5e9e2e449eca04b0052802a9585fc9f189d9d253adb51e80"


class V7ContractError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise V7ContractError(f"{path} must contain a JSON object")
    return value


def validate_prompt_and_schema(repo_root: Path) -> dict[str, Any]:
    prompt = repo_root / PROMPT_PATH
    schema_path = repo_root / SCHEMA_PATH
    if not prompt.is_file():
        raise V7ContractError(f"missing canonical V7.1 prompt: {PROMPT_PATH}")
    actual_hash = sha256_file(prompt)
    if actual_hash != PROMPT_SHA256:
        raise V7ContractError(f"V7.1 prompt hash mismatch: expected {PROMPT_SHA256}, got {actual_hash}")
    if not schema_path.is_file():
        raise V7ContractError(f"missing canonical schema: {SCHEMA_PATH}")
    schema = load_json(schema_path)
    if schema.get("$id") != CANONICAL_SCHEMA_ID:
        raise V7ContractError("schema $id is not production-record/3.0.0")
    if schema.get("properties", {}).get("schema_version", {}).get("const") != "3.0.0":
        raise V7ContractError("schema is not version 3.0.0")
    text = prompt.read_text(encoding="utf-8")
    markers = (
        "GOOGLE CLOUD TEXT-TO-SPEECH",
        "because-of-this://schemas/production-record/3.0.0",
        "G0 preflight",
        "G11 post_publication",
        "A publicação nunca é automática",
        "O mesmo clipe ou derivação dele nunca pode aparecer em outro vídeo",
    )
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise V7ContractError(f"V7.1 prompt is incomplete: {missing}")
    return {
        "status": "V7_PROMPT_SCHEMA_PASS",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": actual_hash,
        "schema_id": CANONICAL_SCHEMA_ID,
        "engine_profile": CANONICAL_PROFILE_ID,
        "engine_version": CANONICAL_ENGINE_VERSION,
        "profile_fingerprint": CANONICAL_PROFILE_FINGERPRINT,
        "gates": list(GATE_ORDER),
    }


def validate_manifest(manifest: dict[str, Any], *, source_label: str = "manifest", require_production: bool = False) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise V7ContractError(f"{source_label} must be an object")
    required = ("schema_version", "video_id", "title", "language", "engine_profile", "engine_profile_fingerprint", "master_prompt_version", "master_prompt_sha256", "production_schema", "human_approval_required")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise V7ContractError(f"{source_label} is missing required V7 fields: {missing}")
    if manifest.get("schema_version") not in {"3.0.0", "3.0"}:
        raise V7ContractError(f"{source_label} must declare schema_version 3.0.0")
    if manifest.get("master_prompt_version") != PROMPT_VERSION:
        raise V7ContractError(f"{source_label} must declare master_prompt_version 7.1")
    if manifest.get("master_prompt_sha256") != PROMPT_SHA256:
        raise V7ContractError(f"{source_label} has the wrong V7.1 prompt hash")
    if manifest.get("production_schema") != CANONICAL_SCHEMA_ID:
        raise V7ContractError(f"{source_label} must declare production-record/3.0.0")
    if manifest.get("human_approval_required") is not True:
        raise V7ContractError(f"{source_label} must require human approval")
    try:
        canonical = validate_canonical_manifest(manifest, source_label=source_label)
    except CanonicalConfigError as exc:
        raise V7ContractError(str(exc)) from exc
    story = manifest.get("story") or manifest.get("story_profile")
    if not isinstance(story, dict):
        raise V7ContractError(f"{source_label} requires a structured story object")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list):
        raise V7ContractError(f"{source_label} requires scenes as an array")
    if require_production and not scenes:
        raise V7ContractError(f"{source_label} cannot enter production without visual scenes")
    narrative = manifest.get("narration") or {}
    if require_production:
        if narrative.get("provider") != "microsoft_edge_tts":
            raise V7ContractError("production narration provider must be microsoft_edge_tts")
        if not isinstance(narrative.get("beats"), list) or not narrative["beats"]:
            raise V7ContractError("production narration requires recoverable beat chunks")
        story_graph = manifest.get("story_graph")
        if not isinstance(story_graph, dict):
            raise V7ContractError("production manifest requires story_graph")
        if not isinstance(story_graph.get("entities"), list) or not story_graph["entities"]:
            raise V7ContractError("story_graph.entities must be non-empty")
        if not isinstance(story_graph.get("beats"), list) or len(story_graph["beats"]) != len(scenes):
            raise V7ContractError("story_graph.beats must cover every visual scene")
        music = manifest.get("music")
        if not isinstance(music, dict):
            raise V7ContractError("production manifest requires a music object")
        for key in ("path", "license", "track_id"):
            if not str(music.get(key, "")).strip():
                raise V7ContractError(f"production music requires {key}")
        if not isinstance(music.get("commercial_use"), bool):
            raise V7ContractError("production music requires a boolean commercial_use field")
    return {"status": "V7_MANIFEST_PASS", "source": source_label, "canonical": canonical, "scene_count": len(scenes), "gates": list(GATE_NAMES.values())}


def validate_production_record_file(path: Path) -> dict[str, Any]:
    return validate_record(load_json(path))


def audit_repo(repo_root: Path, manifest_paths: list[Path]) -> dict[str, Any]:
    prompt = validate_prompt_and_schema(repo_root)
    manifests = []
    for relative in manifest_paths:
        path = (repo_root / relative).resolve()
        value = load_json(path)
        if value.get("lifecycle_status") == "ARCHIVED_HISTORICAL":
            continue
        manifests.append(validate_manifest(value, source_label=str(relative)))
    return {"status": "V7_ENGINE_CONTRACT_PASS", "prompt": prompt, "manifests": manifests, "publication": "MANUAL_ONLY", "legacy_execution_source": "BLOCKED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", action="append", type=Path)
    parser.add_argument("--require-production", action="store_true")
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        report = validate_prompt_and_schema(root)
        if args.manifest:
            report["manifests"] = [
                validate_manifest(load_json((root / path).resolve()), source_label=str(path), require_production=args.require_production)
                for path in args.manifest
            ]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, V7ContractError, ProductionRecordError) as exc:
        print(f"V7 CONTRACT BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
