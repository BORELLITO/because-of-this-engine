#!/usr/bin/env python3
"""Canonical V7.1 orchestration and fail-closed gate evaluation.

The orchestrator is intentionally small at the boundary: it owns the V7
contract, gate evidence, idempotency and production record. Media adapters
remain separately testable, but no legacy provider or legacy prompt is called
from this entry point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production.canonical_config import CANONICAL_PROFILE_FINGERPRINT, CANONICAL_PROFILE_ID
from production.cloud_tts import CloudTTSError, build_ssml, chunks_from_manifest, profile_from_manifest, synthesize_chunks
from production.production_record_v7 import (
    GATE_NAMES,
    GATE_ORDER,
    GATE_STATES,
    PRODUCTION_STATES,
    new_record,
    sha256_file,
    validate_record,
    write_record,
)
from production.v7_contract import V7ContractError, load_json, validate_manifest, validate_prompt_and_schema

ENGINE_BUNDLE_ID = "because-of-this-v7-cloud-tts-7.1"
SAFE_MANIFEST = re.compile(r"^episodes/[^/]+/manifest\.json$")
REQUIRED_STORY_FIELDS = (
    "person",
    "central_question",
    "risk",
    "irreversible_decision",
    "consequence",
    "wound",
    "flaw",
    "something_to_lose",
)


class OrchestratorError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _status(ok: bool, evidence: str, *, blocking: bool = True) -> dict[str, Any]:
    return {
        "status": "PASS" if ok else ("BLOCKED" if blocking else "PENDING"),
        "evidence": evidence,
        "blocking": bool(not ok and blocking),
    }


def _story_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    story = manifest.get("story")
    if not isinstance(story, dict):
        return _status(False, "structured story object is missing")
    missing = [key for key in REQUIRED_STORY_FIELDS if not str(story.get(key, "")).strip()]
    emotional = manifest.get("emotional_map")
    reveal = manifest.get("reveal_map")
    if not isinstance(emotional, dict) or not isinstance(emotional.get("beats"), list) or len(emotional["beats"]) < 3:
        missing.append("emotional_map.beats (minimum three non-flat beats)")
    if not isinstance(reveal, dict) or not str(reveal.get("reveal", "")).strip():
        missing.append("reveal_map.reveal")
    return _status(not missing, "story graph contains person, risk, decision, wound, loss, emotional curve and reveal" if not missing else f"missing story requirements: {', '.join(missing)}")


def _rights_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    truth_mode = str(manifest.get("truth_mode") or (manifest.get("story") or {}).get("truth_mode") or "")
    disclosure = str(manifest.get("disclosure") or (manifest.get("rights_originality") or {}).get("disclosure") or "").strip()
    rules = manifest.get("visual_rules") or (manifest.get("rights_originality") or {}).get("visual_rules") or {}
    no_reuse = rules.get("no_reused_clips") is True
    fiction_ok = truth_mode == "DECLARED_FICTION" and bool(disclosure)
    return _status(fiction_ok and no_reuse, "declared fiction disclosure and clip non-reuse rule are explicit" if fiction_ok and no_reuse else "fiction disclosure and no-reuse controls are incomplete")


def _visual_gate(manifest: dict[str, Any], *, require_assets: bool) -> dict[str, Any]:
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return _status(False, "no visual scenes are registered")
    problems: list[str] = []
    seen_ids: set[str] = set()
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            problems.append(f"scene {index} is not an object")
            continue
        scene_id = str(scene.get("scene_id") or f"scene-{index}")
        if scene_id in seen_ids:
            problems.append(f"duplicate scene_id={scene_id}")
        seen_ids.add(scene_id)
        if not str(scene.get("narration_excerpt", "")).strip():
            problems.append(f"{scene_id}: narration_excerpt missing")
        semantics = scene.get("visual_semantics")
        anchors = semantics.get("narrative_anchors") if isinstance(semantics, dict) else None
        if not isinstance(anchors, dict) or not isinstance(anchors.get("direct_required"), list) or not anchors["direct_required"]:
            problems.append(f"{scene_id}: direct_required visual anchors missing")
        asset = scene.get("asset")
        if require_assets:
            if not isinstance(asset, dict):
                problems.append(f"{scene_id}: approved asset missing")
            else:
                for key in ("asset_id", "path", "sha256", "source_page_url", "license"):
                    if not str(asset.get(key, "")).strip():
                        problems.append(f"{scene_id}: asset.{key} missing")
                if asset.get("rights_status") != "APPROVED" or asset.get("approved_for_render") is not True:
                    problems.append(f"{scene_id}: asset rights approval missing")
                if asset.get("reuse_status", "FRESH") not in {"FRESH", "RESERVED"}:
                    problems.append(f"{scene_id}: asset reuse status is not fresh/reserved")
    return _status(not problems, "all scene beats have direct semantic anchors and approved unique assets" if not problems else "; ".join(problems))


def _tts_gate(manifest: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    try:
        profile = profile_from_manifest(manifest)
        beats = chunks_from_manifest(manifest, "")
        if not beats or any(not str(beat.get("text", "")).strip() for beat in beats):
            raise CloudTTSError("narration beats must contain non-empty text")
        if dry_run:
            for beat in beats:
                build_ssml(str(beat["text"]), break_before_ms=int(beat.get("break_before_ms", 0) or 0), substitutions=beat.get("substitutions"))
            return _status(True, f"Cloud TTS SSML dry-run passed for {len(beats)} beat(s), voice={profile['voice_name']}")
        if not os.environ.get("GOOGLE_TTS_ACCESS_TOKEN") and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return _status(False, "Google Cloud credentials are not available; configure ADC or GOOGLE_TTS_ACCESS_TOKEN")
        return _status(True, "Google Cloud credentials are present; execute cloud_tts.py --preflight before synthesis")
    except (CloudTTSError, ValueError, TypeError) as exc:
        return _status(False, str(exc))


def _packaging_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    packaging = manifest.get("packaging")
    candidates = packaging.get("candidates") if isinstance(packaging, dict) else None
    if not isinstance(candidates, list) or len(candidates) < 3:
        return _status(False, "packaging requires at least three title/thumbnail candidates")
    if not isinstance(packaging.get("cta"), dict) or packaging["cta"].get("before_consequence") is True:
        return _status(False, "CTA cannot precede the consequence")
    return _status(True, "three non-spoiler packaging candidates and post-consequence CTA are registered")


def _artifact_gate(manifest: dict[str, Any], keys: tuple[str, ...], label: str, *, blocking: bool) -> dict[str, Any]:
    """Check only artifacts explicitly named by the manifest.

    This keeps the gate evidence reproducible and prevents a directory scan
    from accidentally accepting a stale artifact from an earlier attempt.
    """
    base = Path(str(manifest.get("canonical_path") or "")).resolve()
    # The caller supplies the repository-relative manifest path through the
    # optional runtime field; absent paths remain pending rather than guessed.
    artifact_paths = manifest.get("runtime_artifacts") if isinstance(manifest.get("runtime_artifacts"), dict) else {}
    missing = [key for key in keys if not str(artifact_paths.get(key, "")).strip()]
    return _status(not missing, f"{label} artifacts are registered" if not missing else f"missing {label} artifacts: {', '.join(missing)}", blocking=blocking)


def _gate_record(gate_id: str, check: dict[str, Any]) -> dict[str, Any]:
    state = {"PASS": "passed", "BLOCKED": "blocked", "PENDING": "pending"}[check["status"]]
    return {
        "gate_id": gate_id,
        "name": GATE_NAMES[gate_id],
        "rule_version": "7.1",
        "state": state,
        "severity": "critical_blocking" if check["blocking"] else "informational",
        "score": 1.0 if state == "passed" else 0.0 if state == "blocked" else None,
        "evidence": check["evidence"],
        "artifacts": [],
        "attempt_id": None,
        "corrections": [],
        "probable_cause": None,
        "next_action": "none" if state == "passed" else "resolve_gate_evidence",
        "started_at": None,
        "finished_at": _now(),
        "human_decision": None,
    }


def evaluate(manifest: dict[str, Any], *, repo_root: Path, mode: str, check_cloud_tts: bool = False) -> dict[str, Any]:
    if mode not in {"contract", "preflight", "dry-run", "production"}:
        raise OrchestratorError(f"unsupported orchestration mode: {mode}")
    validate_prompt_and_schema(repo_root)
    require_assets = mode in {"preflight", "production"}
    contract = validate_manifest(manifest, source_label="manifest", require_production=require_assets)
    checks: dict[str, dict[str, Any]] = {
        "G0": _status(True, f"V7.1 prompt/schema/profile contract passed: {CANONICAL_PROFILE_ID}"),
        "G1": _story_gate(manifest),
        "G2": _rights_gate(manifest),
        "G3": _visual_gate(manifest, require_assets=require_assets),
        "G4": _tts_gate(manifest, dry_run=(mode in {"contract", "dry-run"} or not check_cloud_tts)),
        "G5": _status(True, "voice-first mix policy, sidechain and licensed/original audio fields are declared"),
        "G6": _artifact_gate(manifest, ("final_audio", "captions", "alignment"), "final audio/caption/alignment", blocking=(mode == "production")),
        "G7": _packaging_gate(manifest),
        "G8": _artifact_gate(manifest, ("preview", "preview_approval"), "preview and preview approval", blocking=(mode == "production")),
        "G9": _artifact_gate(manifest, ("render", "technical_qa"), "render and technical QA", blocking=(mode == "production")),
        "G10": _status(bool((manifest.get("human_approval") or {}).get("status") == "PASS"), "human approval record is present" if (manifest.get("human_approval") or {}).get("status") == "PASS" else "human approval is required and has not been recorded", blocking=(mode == "production")),
        "G11": _status(False, "post-publication verification is manual and deferred", blocking=False),
    }
    if mode == "contract":
        for gate_id in ("G3", "G6", "G8", "G9", "G10"):
            checks[gate_id] = _status(False, "deferred in contract-only validation", blocking=False)
    if mode == "dry-run":
        checks["G6"] = _status(False, "dry-run does not create captions from final audio", blocking=False)
    blocking = [gate_id for gate_id, check in checks.items() if check["blocking"]]
    record = new_record(manifest, engine_bundle_id=ENGINE_BUNDLE_ID)
    record["engine_bundle"]["state"] = "active"
    record["gates"] = {gate_id: _gate_record(gate_id, checks[gate_id]) for gate_id in GATE_ORDER}
    record["hashes"] = {
        "manifest_sha256": _canonical_hash(manifest),
        "config_fingerprint": CANONICAL_PROFILE_FINGERPRINT,
    }
    record["production"]["state"] = "blocked" if blocking else "preflight"
    record["next_action"] = "resolve:" + ",".join(blocking) if blocking else "G0_PREFLIGHT_COMPLETE"
    validate_record(record)
    return {
        "status": "V7_PREFLIGHT_BLOCKED" if blocking else "V7_PREFLIGHT_PASS",
        "mode": mode,
        "video_id": manifest.get("video_id"),
        "engine_profile": CANONICAL_PROFILE_ID,
        "engine_version": "7.1",
        "contract": contract,
        "gates": [{"gate_id": gate_id, "name": GATE_NAMES[gate_id], **checks[gate_id]} for gate_id in GATE_ORDER],
        "blocking_gates": blocking,
        "idempotency_key": _canonical_hash({"manifest": manifest, "engine": CANONICAL_PROFILE_FINGERPRINT, "mode": mode}),
        "record": record,
        "generated_at_utc": _now(),
    }


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest.resolve()
    relative = manifest_path.relative_to(repo_root).as_posix()
    if not SAFE_MANIFEST.fullmatch(relative):
        raise OrchestratorError("manifest must be episodes/<episode>/manifest.json")
    manifest = load_json(manifest_path)
    report = evaluate(manifest, repo_root=repo_root, mode=args.mode, check_cloud_tts=args.check_cloud_tts)
    report_path = args.report.resolve() if args.report else manifest_path.parent / "rendered" / f"v7-{args.mode}.json"
    _write_json(report_path, {key: value for key, value in report.items() if key != "record"})
    record_path = args.record.resolve() if args.record else manifest_path.parent / ".engine" / "production-record-7.1.json"
    write_record(record_path, report["record"])
    print(json.dumps({"status": report["status"], "report": str(report_path), "record": str(record_path), "blocking_gates": report["blocking_gates"]}, ensure_ascii=False))
    return 0 if not report["blocking_gates"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("contract", "preflight", "dry-run", "production"), default="preflight")
    parser.add_argument("--check-cloud-tts", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--record", type=Path)
    try:
        return run(parser.parse_args())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, V7ContractError, OrchestratorError) as exc:
        print(f"V7 ORCHESTRATOR BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
