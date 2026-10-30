#!/usr/bin/env python3
"""Canonical V7.2 Charon orchestration and fail-closed gate evaluation.

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
from production.cloud_tts import (
    CloudTTSError,
    build_ssml,
    chunks_from_manifest,
    cloud_credentials_configured,
    profile_from_manifest,
)
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

ENGINE_BUNDLE_ID = "because-of-this-v7.2-charon-cloud-tts-7.2"
SAFE_MANIFEST = re.compile(r"^episodes/[^/]+/(?:manifest|preview-manifest)\.json$")
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


def _story_gate(manifest: dict[str, Any], *, manifest_dir: Path | None = None, require_coverage: bool = False) -> dict[str, Any]:
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
    if missing:
        return _status(False, f"missing story requirements: {', '.join(missing)}")
    if require_coverage and manifest_dir is not None:
        runtime = manifest.get("runtime_artifacts") if isinstance(manifest.get("runtime_artifacts"), dict) else {}
        hashes = manifest.get("runtime_artifact_hashes") if isinstance(manifest.get("runtime_artifact_hashes"), dict) else {}
        relative = str(runtime.get("narration_coverage") or "rendered/narration-coverage.json").strip()
        coverage_path = (manifest_dir / relative).resolve()
        if coverage_path == manifest_dir or manifest_dir not in coverage_path.parents:
            return _status(False, "narration coverage path escapes episode directory")
        if not coverage_path.is_file():
            return _status(False, f"narration coverage report is missing: {relative}")
        try:
            coverage_report = json.loads(coverage_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return _status(False, "narration coverage report is not valid JSON")
        if not isinstance(coverage_report, dict) or coverage_report.get("status") != "STORY_INTELLIGENCE_PASS":
            return _status(False, "narration coverage report is not a STORY_INTELLIGENCE_PASS artifact")
        declared = str(hashes.get("narration_coverage", "")).lower()
        if declared and (not re.fullmatch(r"[0-9a-f]{64}", declared) or hashlib.sha256(coverage_path.read_bytes()).hexdigest() != declared):
            return _status(False, "narration coverage report sha256 evidence is invalid")
    return _status(True, "story graph and narration coverage contain person, risk, decision, wound, loss, emotional curve and reveal")


def _rights_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    truth_mode = str(manifest.get("truth_mode") or (manifest.get("story") or {}).get("truth_mode") or "")
    disclosure = str(manifest.get("disclosure") or (manifest.get("rights_originality") or {}).get("disclosure") or "").strip()
    rules = manifest.get("visual_rules") or (manifest.get("rights_originality") or {}).get("visual_rules") or {}
    no_reuse = rules.get("no_reused_clips") is True
    no_derived_reuse = rules.get("no_derived_clip_reuse") is True
    fiction_ok = truth_mode == "DECLARED_FICTION" and bool(disclosure)
    passed = fiction_ok and no_reuse and no_derived_reuse
    return _status(passed, "declared fiction disclosure and clip/derivation non-reuse rules are explicit" if passed else "fiction disclosure and clip/derivation non-reuse controls are incomplete")


def _visual_gate(
    manifest: dict[str, Any],
    *,
    require_assets: bool,
    manifest_dir: Path | None = None,
    allow_preview_only: bool = False,
) -> dict[str, Any]:
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return _status(False, "no visual scenes are registered")
    problems: list[str] = []
    seen_ids: set[str] = set()
    seen_assets: set[str] = set()
    total_duration = 0.0
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            problems.append(f"scene {index} is not an object")
            continue
        scene_id = str(scene.get("scene_id") or f"scene-{index}")
        if scene_id in seen_ids:
            problems.append(f"duplicate scene_id={scene_id}")
        seen_ids.add(scene_id)
        try:
            duration = float(scene.get("duration", 0))
        except (TypeError, ValueError):
            duration = 0.0
        if duration <= 0:
            problems.append(f"{scene_id}: duration must be positive")
        total_duration += duration
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
                asset_id = str(asset.get("asset_id", "")).strip()
                if asset_id and asset_id in seen_assets:
                    problems.append(f"{scene_id}: asset_id={asset_id} is reused")
                if asset_id:
                    seen_assets.add(asset_id)
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(asset.get("sha256", ""))):
                    problems.append(f"{scene_id}: asset.sha256 must be a 64-character digest")
                if not str(asset.get("perceptual_hash", "")).strip():
                    problems.append(f"{scene_id}: asset.perceptual_hash missing")
                if manifest_dir is not None:
                    asset_path = (manifest_dir / str(asset.get("path", ""))).resolve()
                    if asset_path != manifest_dir and manifest_dir not in asset_path.parents:
                        problems.append(f"{scene_id}: asset.path escapes episode directory")
                    elif not asset_path.is_file():
                        problems.append(f"{scene_id}: hydrated asset file is missing")
                approved = asset.get("rights_status") == "APPROVED" and asset.get("approved_for_render") is True
                preview_candidate = (
                    allow_preview_only
                    and asset.get("rights_status") == "PREVIEW_ONLY"
                    and asset.get("approved_for_render") is False
                    and asset.get("preview_only") is True
                    and str(asset.get("preview_only_reason", "")).strip()
                )
                if not approved and not preview_candidate:
                    problems.append(f"{scene_id}: asset rights approval missing for this mode")
                if asset.get("reuse_status", "FRESH") not in {"FRESH", "RESERVED"}:
                    problems.append(f"{scene_id}: asset reuse status is not fresh/reserved")
                if asset.get("derived_from"):
                    problems.append(f"{scene_id}: derived clip reuse is forbidden")
    if not 60.0 <= total_duration <= 75.0:
        problems.append(f"scene duration total {total_duration:.3f}s is outside the 60–75s contract")
    message = (
        "all scene beats have direct semantic anchors and mode-valid unique assets"
        if not problems
        else "; ".join(problems)
    )
    return _status(not problems, message)


def _tts_gate(manifest: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    try:
        profile = profile_from_manifest(manifest)
        beats = chunks_from_manifest(manifest, "")
        if not beats or any(not str(beat.get("text", "")).strip() for beat in beats):
            raise CloudTTSError("narration beats must contain non-empty text")
        for beat in beats:
            build_ssml(
                str(beat["text"]),
                break_before_ms=int(beat.get("break_before_ms", 0) or 0),
                substitutions=beat.get("substitutions"),
            )
        if dry_run:
            return _status(
                True,
                f"Google Cloud TTS Charon SSML dry-run passed for {len(beats)} beat(s), voice={profile['voice_name']}",
            )
        if not cloud_credentials_configured():
            return _status(
                False,
                "Google Cloud TTS credentials are not configured; provide OAuth refresh-token or ADC credentials",
            )
        return _status(
            True,
            f"Google Cloud TTS Charon credentials are configured for {profile['voice_name']}; preflight must verify voice availability",
        )
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


def _audio_gate(manifest: dict[str, Any], *, require_approved: bool, manifest_dir: Path | None = None) -> dict[str, Any]:
    music = manifest.get("music")
    if not isinstance(music, dict):
        return _status(False, "music object is missing")
    required = ("path", "license", "track_id")
    missing = [key for key in required if not str(music.get(key, "")).strip()]
    if not isinstance(music.get("commercial_use"), bool):
        missing.append("commercial_use")
    if music.get("complete_track_reuse") != "forbidden":
        missing.append("complete_track_reuse=forbidden")
    if music.get("sidechain_enabled") is not True:
        missing.append("sidechain_enabled=true")
    if manifest_dir is not None and str(music.get("path", "")).strip():
        music_path = (manifest_dir / str(music["path"])).resolve()
        if music_path != manifest_dir and manifest_dir not in music_path.parents:
            missing.append("music.path escapes episode directory")
        elif not music_path.is_file():
            missing.append("music file is missing")
    if require_approved and (music.get("commercial_use") is not True or str(music.get("license_status", "")).upper() != "APPROVED"):
        missing.append("approved commercial-use music license")
    return _status(not missing, "voice-first mix, sidechain, licensed music and non-reuse policy are complete" if not missing else f"audio mix blockers: {', '.join(missing)}")


def _artifact_gate(manifest: dict[str, Any], manifest_dir: Path, keys: tuple[str, ...], label: str, *, blocking: bool) -> dict[str, Any]:
    """Check only artifacts explicitly named by the manifest.

    This keeps the gate evidence reproducible and prevents a directory scan
    from accidentally accepting a stale artifact from an earlier attempt.
    """
    artifact_paths = manifest.get("runtime_artifacts") if isinstance(manifest.get("runtime_artifacts"), dict) else {}
    artifact_hashes = manifest.get("runtime_artifact_hashes") if isinstance(manifest.get("runtime_artifact_hashes"), dict) else {}
    problems: list[str] = []
    for key in keys:
        relative = str(artifact_paths.get(key, "")).strip()
        if not relative:
            problems.append(f"{key}: path missing")
            continue
        candidate = (manifest_dir / relative).resolve()
        if candidate != manifest_dir and manifest_dir not in candidate.parents:
            problems.append(f"{key}: path escapes episode directory")
            continue
        if blocking and not candidate.is_file():
            problems.append(f"{key}: file missing")
            continue
        declared = str(artifact_hashes.get(key, "")).lower()
        if blocking and not re.fullmatch(r"[0-9a-f]{64}", declared):
            problems.append(f"{key}: sha256 evidence missing")
            continue
        if blocking:
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if actual != declared:
                problems.append(f"{key}: sha256 mismatch")
    return _status(not problems, f"{label} artifacts exist with matching hashes" if not problems else "; ".join(problems), blocking=blocking)


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


def evaluate(manifest: dict[str, Any], *, repo_root: Path, manifest_dir: Path, mode: str, check_cloud_tts: bool = False) -> dict[str, Any]:
    if mode not in {"contract", "dry-run", "draft-preview", "preflight", "preview", "production"}:
        raise OrchestratorError(f"unsupported orchestration mode: {mode}")
    validate_prompt_and_schema(repo_root)
    require_assets = mode in {"draft-preview", "preflight", "preview", "production"}
    allow_preview_only = mode == "draft-preview"
    contract = validate_manifest(manifest, source_label="manifest", require_production=require_assets)
    checks: dict[str, dict[str, Any]] = {
        "G0": _status(True, f"V7.2 prompt/schema/profile contract passed: {CANONICAL_PROFILE_ID}"),
        "G1": _story_gate(manifest, manifest_dir=manifest_dir, require_coverage=require_assets),
        "G2": _rights_gate(manifest),
        "G3": _visual_gate(
            manifest,
            require_assets=require_assets,
            manifest_dir=manifest_dir,
            allow_preview_only=allow_preview_only,
        ),
        "G4": _tts_gate(manifest, dry_run=(mode in {"contract", "dry-run"} or not check_cloud_tts)),
        "G5": _audio_gate(
            manifest,
            require_approved=mode in {"preflight", "preview", "production"},
            manifest_dir=manifest_dir,
        ),
        "G6": _artifact_gate(manifest, manifest_dir, ("final_audio", "captions", "alignment"), "final audio/caption/alignment", blocking=(mode in {"draft-preview", "preview", "production"})),
        "G7": _packaging_gate(manifest),
        "G8": _artifact_gate(manifest, manifest_dir, ("preview", "preview_approval") if mode == "production" else ("preview",), "preview", blocking=(mode in {"draft-preview", "preview", "production"})),
        "G9": _artifact_gate(manifest, manifest_dir, ("render", "technical_qa"), "render and technical QA", blocking=(mode in {"draft-preview", "preview", "production"})),
        "G10": _status(bool((manifest.get("human_approval") or {}).get("status") == "PASS"), "human approval record is present" if (manifest.get("human_approval") or {}).get("status") == "PASS" else "human approval is required and has not been recorded", blocking=(mode == "production")),
        "G11": _status(False, "post-publication verification is manual and deferred", blocking=False),
    }
    if mode == "contract":
        for gate_id in ("G3", "G5", "G6", "G8", "G9", "G10"):
            checks[gate_id] = _status(False, "deferred in contract-only validation", blocking=False)
    if mode == "dry-run":
        for gate_id in ("G3", "G5", "G6", "G8", "G9", "G10"):
            checks[gate_id] = _status(False, "deferred in deterministic dry-run", blocking=False)
    blocking = [gate_id for gate_id, check in checks.items() if check["blocking"]]
    record = new_record(manifest, engine_bundle_id=ENGINE_BUNDLE_ID)
    record["engine_bundle"]["state"] = "active"
    record["gates"] = {gate_id: _gate_record(gate_id, checks[gate_id]) for gate_id in GATE_ORDER}
    record["hashes"] = {
        "manifest_sha256": _canonical_hash(manifest),
        "config_fingerprint": CANONICAL_PROFILE_FINGERPRINT,
        "idempotency_key": _canonical_hash({"manifest": manifest, "engine": CANONICAL_PROFILE_FINGERPRINT, "mode": mode}),
    }
    record["production"]["state"] = "blocked" if blocking else "preflight"
    record["next_action"] = "resolve:" + ",".join(blocking) if blocking else "G0_PREFLIGHT_COMPLETE"
    validate_record(record)
    return {
        "status": "V7_PREFLIGHT_BLOCKED" if blocking else "V7_PREFLIGHT_PASS",
        "mode": mode,
        "video_id": manifest.get("video_id"),
        "engine_profile": CANONICAL_PROFILE_ID,
        "engine_version": "7.2",
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
    report = evaluate(manifest, repo_root=repo_root, manifest_dir=manifest_path.parent, mode=args.mode, check_cloud_tts=args.check_cloud_tts)
    report_path = args.report.resolve() if args.report else manifest_path.parent / "rendered" / f"v7-{args.mode}.json"
    _write_json(report_path, {key: value for key, value in report.items() if key != "record"})
    record_path = args.record.resolve() if args.record else manifest_path.parent / ".engine" / "production-record-7.2.json"
    write_record(record_path, report["record"])
    print(json.dumps({"status": report["status"], "report": str(report_path), "record": str(record_path), "blocking_gates": report["blocking_gates"]}, ensure_ascii=False))
    return 0 if not report["blocking_gates"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("contract", "preflight", "dry-run", "draft-preview", "preview", "production"), default="preflight")
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
