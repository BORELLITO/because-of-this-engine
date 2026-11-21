"""Single operational Runflow for the Because Of This V2.1 engine.

The Runflow is an orchestration contract, not a replacement engine. It binds
the approved episode package to the canonical V2.1 gates and emits one
machine-readable plan for GitHub Actions. It deliberately has no knowledge of
other projects and never performs TTS, publication or Drive writes itself.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

EPISODE_ID = re.compile(r"episode-[0-9]{3}")
FORBIDDEN_SCOPE_MARKERS = (
    "verbo-no-chao",
    "verbo_no_chao",
    "corte-fino",
    "corte_fino",
    "captapronto",
    "vacina",
    "editor-prime",
    "fidelity-lock",
)
REQUIRED_EPISODE_FILES = (
    "production-record.json",
    "story-architecture.json",
    "visual/scene-asset-manifest.json",
)


class RunflowError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunflowError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RunflowError(f"JSON object required: {path}")
    return value


def _scope_guard(repo_root: Path, request: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    root_text = repo_root.resolve().as_posix().lower()
    request_text = json.dumps(request, ensure_ascii=False).lower()
    for marker in FORBIDDEN_SCOPE_MARKERS:
        if marker in root_text or marker in request_text:
            failures.append(f"foreign project marker detected:{marker}")
    if repo_root.name != "because-of-this-engine":
        failures.append("Runflow must execute from the because-of-this-engine repository")
    return failures


def load_request(path: Path, *, repo_root: Path) -> dict[str, Any]:
    request = _read_json(path)
    episode_id = str(request.get("episode_id") or "").strip()
    if not EPISODE_ID.fullmatch(episode_id):
        raise RunflowError("episode_id must match episode-NNN")
    mode = str(request.get("mode") or "preview").strip().lower()
    if mode not in {"preview", "final"}:
        raise RunflowError("mode must be preview or final")
    source_run_id = str(request.get("source_run_id") or "").strip()
    source_artifact_name = str(request.get("source_artifact_name") or "").strip()
    failures = _scope_guard(repo_root, request)
    if failures:
        raise RunflowError("; ".join(failures))
    if not source_run_id or not source_artifact_name:
        evidence_path = repo_root / "episodes" / episode_id / "production-record.json"
        evidence = _read_json(evidence_path).get("caption_artifact_evidence") or {}
        source_run_id = source_run_id or str(evidence.get("workflow_run_id") or "").strip()
        source_artifact_name = source_artifact_name or str(evidence.get("artifact_name") or "").strip()
    if not source_run_id.isdigit():
        raise RunflowError("source_run_id is missing and no approved caption checkpoint is recorded")
    if not source_artifact_name:
        raise RunflowError("source_artifact_name is missing and no approved caption checkpoint is recorded")
    request["episode_id"] = episode_id
    request["mode"] = mode
    request["source_run_id"] = source_run_id
    request["source_artifact_name"] = source_artifact_name
    return request


def build_plan(request: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    episode_id = request["episode_id"]
    episode_root = repo_root / "episodes" / episode_id
    failures: list[str] = []
    files: dict[str, str] = {}
    for relative in REQUIRED_EPISODE_FILES:
        path = episode_root / relative
        files[relative] = path.as_posix()
        if not path.is_file():
            failures.append(f"missing episode package file:{path.relative_to(repo_root).as_posix()}")

    record_path = episode_root / "production-record.json"
    record: dict[str, Any] = {}
    if record_path.is_file():
        try:
            record = _read_json(record_path)
        except RunflowError as exc:
            failures.append(str(exc))
    if record:
        if record.get("episode_id") != episode_id:
            failures.append("production record episode_id mismatch")
        if record.get("canonical_engine_version", 2.1) != 2.1:
            failures.append("episode package is not V2.1")
    captioned_artifact = {
        "run_id": request["source_run_id"],
        "name": request["source_artifact_name"],
        "required_files": ["narration.wav", "narration.ass", "voice-profile.json"],
    }
    stages = [
        {"id": "package", "agent": "canonical_package_gate", "command": "production/canonical_entrypoint.py"},
        {"id": "visual_intake", "agent": "visual_asset_intake_and_rights", "command": "production/fetch_v21_visuals.py"},
        {"id": "caption_lock", "agent": "audio_caption_evidence", "command": "production/recolor_karaoke_ass.py"},
        {"id": "render", "agent": "canonical_v21_renderer", "command": "production/render_v21_preview.py"},
        {"id": "technical_qa", "agent": "quality_gates_and_media_contract", "command": "production/v21_singleton_guard.py"},
        {"id": "delivery_artifact", "agent": "github_artifact_delivery", "command": "actions/upload-artifact@v4"},
    ]
    if request["mode"] == "final":
        stages.insert(4, {"id": "final_audio_qa", "agent": "independent_audio_postflight", "command": "production/render_v21_final.py"})
        stages.insert(6, {"id": "drive_delivery", "agent": "verified_drive_delivery", "command": "production/google_drive_delivery.py"})
    return {
        "schema_version": "because-of-this-runflow-1.0",
        "status": "RUNFLOW_BLOCKED" if failures else "RUNFLOW_READY",
        "project": "BECAUSE OF THIS",
        "repository": "BORELLITO/because-of-this-engine",
        "episode_id": episode_id,
        "mode": request["mode"],
        "source_checkpoint": captioned_artifact,
        "episode_files": files,
        "stages": stages,
        "execution_policy": {
            "single_entrypoint": True,
            "legacy_engines_allowed": False,
            "other_projects_allowed": False,
            "new_tts_call": False,
            "publication": "manual_only",
            "drive_write": request["mode"] == "final",
            "fail_closed": True,
        },
        "failures": failures,
        "next_action": "resolve:" + ",".join(failures) if failures else "execute_github_runflow",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.repo_root.resolve()
        request = load_request(args.request.resolve(), repo_root=root)
        report = build_plan(request, repo_root=root)
    except (RunflowError, OSError, ValueError) as exc:
        report = {
            "schema_version": "because-of-this-runflow-1.0",
            "status": "RUNFLOW_BLOCKED",
            "project": "BECAUSE OF THIS",
            "failures": [str(exc)],
            "next_action": "resolve:RUNFLOW_INPUT",
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "RUNFLOW_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
