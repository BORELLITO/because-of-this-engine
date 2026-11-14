#!/usr/bin/env python3
"""Fail-closed integrity guard for the Because Of This immutable core."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

POLICY_RELATIVE = Path("production/immutable_core_policy_v1.json")
AUTHORIZATION_MARKER = "AUTHORIZED-IMMUTABLE-CORE-UPDATE"


class ImmutableCoreError(ValueError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ImmutableCoreError(f"unreadable JSON: {path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ImmutableCoreError(f"JSON object required: {path}")
    return value


def _literal_assignments(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    result: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            result[target.id] = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            continue
    return result


def _check(failures: list[str], actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def audit(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    failures: list[str] = []
    try:
        policy = _load_json(root / POLICY_RELATIVE)
    except ImmutableCoreError as exc:
        return {"status": "IMMUTABLE_CORE_BLOCKED", "failures": [str(exc)]}

    _check(failures, policy.get("policy_id"), "because-of-this-immutable-core-v1", "policy_id")
    _check(failures, policy.get("status"), "LOCKED", "policy.status")
    _check(failures, policy.get("default_action_on_drift"), "BLOCK", "policy.default_action_on_drift")
    _check(failures, policy.get("default_change_mode"), "NO_SILENT_MUTATION", "policy.default_change_mode")

    authorization = policy.get("explicit_authorization")
    if not isinstance(authorization, dict):
        failures.append("explicit_authorization is missing")
    else:
        _check(failures, authorization.get("required"), True, "explicit_authorization.required")
        _check(failures, authorization.get("change_request_marker"), AUTHORIZATION_MARKER, "authorization.marker")
        _check(failures, authorization.get("human_review_required"), True, "authorization.human_review_required")
        _check(failures, authorization.get("direct_main_changes"), "FORBIDDEN", "authorization.direct_main_changes")

    for authority in policy.get("authority_files", []):
        if not isinstance(authority, dict):
            failures.append("authority_files contains a non-object")
            continue
        relative = str(authority.get("path", "")).strip()
        expected = str(authority.get("git_blob_sha1", "")).strip()
        path = root / relative
        if not relative or not expected:
            failures.append("authority file entry is incomplete")
        elif not path.is_file():
            failures.append(f"authority file missing:{relative}")
        else:
            try:
                actual = git_blob_sha1(path)
            except OSError as exc:
                failures.append(f"authority file unreadable:{relative}:{exc}")
            else:
                if actual != expected:
                    failures.append(f"authority file drift:{relative}:expected {expected}, got {actual}")

    try:
        active = _load_json(root / "production/active_engine_policy.json")
        runtime = policy["immutable_contract"]["runtime"]
        for key in (
            "active_engine_version",
            "active_engine_profile",
            "canonical_entrypoint",
            "voice_provider",
            "publication_policy",
            "production_enablement",
            "missing_dependency_policy",
        ):
            _check(failures, active.get(key), runtime[key], f"active_engine_policy.{key}")
        voice = active.get("voice_policy") if isinstance(active.get("voice_policy"), dict) else {}
        _check(failures, voice.get("voice_name"), runtime["voice_name"], "voice_policy.voice_name")
        _check(failures, voice.get("model"), runtime["voice_model"], "voice_policy.model")
        _check(failures, voice.get("provider_fallback"), runtime["provider_fallback"], "voice_policy.provider_fallback")
        _check(failures, voice.get("creative_claw_allowed"), runtime["creative_claw_allowed"], "voice_policy.creative_claw_allowed")
        render = policy["immutable_contract"]["render"]
        for key in ("width", "height", "fps"):
            _check(failures, active.get("render_contract", {}).get(key), render[key], f"render_contract.{key}")
    except (KeyError, TypeError) as exc:
        failures.append(f"immutable contract malformed:{exc}")

    try:
        captions = _load_json(root / "production/caption_policy_v21.json")
        contract = policy["immutable_contract"]["captions"]
        layout = captions.get("layout") if isinstance(captions.get("layout"), dict) else {}
        alignment = captions.get("alignment") if isinstance(captions.get("alignment"), dict) else {}
        _check(failures, alignment.get("source"), contract["alignment_source"], "caption_policy.alignment.source")
        _check(failures, layout.get("max_lines"), contract["max_lines"], "caption_policy.layout.max_lines")
        _check(failures, layout.get("margin_v"), contract["margin_v"], "caption_policy.layout.margin_v")
        _check(failures, alignment.get("active_word_color"), contract["active_word_color"], "caption_policy.alignment.active_word_color")
        _check(failures, captions.get("forbidden_caption_characters"), contract["forbidden_characters"], "caption_policy.forbidden_caption_characters")
    except (KeyError, TypeError) as exc:
        failures.append(f"caption contract malformed:{exc}")

    try:
        assignments = _literal_assignments((root / "production/render_v21_preview.py").read_text(encoding="utf-8"))
        branding = policy["immutable_contract"]["branding"]
        render = policy["immutable_contract"]["render"]
        baseline = policy["immutable_contract"]["v21_preview_regression_baseline"]
        for name, expected in (
            ("FPS", render["fps"]),
            ("WIDTH", render["width"]),
            ("HEIGHT", render["height"]),
            ("IN_VIDEO_LOGO_Y", branding["logo_y"]),
            ("IN_VIDEO_LOGO_WIDTH", branding["logo_width"]),
            ("OUTRO_SECONDS", baseline["outro_seconds"]),
        ):
            _check(failures, assignments.get(name), expected, f"render_v21_preview.{name}")
    except (OSError, SyntaxError, KeyError, TypeError) as exc:
        failures.append(f"preview render contract unavailable:{exc}")

    try:
        final_source = (root / "production/render_v21_final.py").read_text(encoding="utf-8")
        if 'scene_count") != 16' not in final_source:
            failures.append("render_v21_final.scene_count guard is not locked to 16")
        if 'caption_margin_v") != 650' not in final_source:
            failures.append("render_v21_final.caption_margin_v guard is not locked to 650")
    except OSError as exc:
        failures.append(f"final render contract unavailable:{exc}")

    return {
        "status": "IMMUTABLE_CORE_PASS" if not failures else "IMMUTABLE_CORE_BLOCKED",
        "policy": str(POLICY_RELATIVE),
        "authority_file_count": len(policy.get("authority_files", [])),
        "failures": failures,
        "next_action": "continue" if not failures else "stop_and_review_authority_drift",
    }


def validate_episode_surface_lock(manifest: dict[str, Any], lock: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if lock.get("status") != "APPROVED_LOCKED":
        failures.append("episode surface lock must have status APPROVED_LOCKED")
    if not str(lock.get("approved_by", "")).strip():
        failures.append("episode surface lock requires approved_by")
    if not str(lock.get("approved_at", "")).strip():
        failures.append("episode surface lock requires approved_at")
    if manifest.get("episode_id") != lock.get("episode_id"):
        failures.append("episode_id mismatch")

    manifest_shots = manifest.get("shot_assignments")
    lock_shots = lock.get("shot_assignments")
    if not isinstance(manifest_shots, list) or not isinstance(lock_shots, list):
        failures.append("shot_assignments must exist in manifest and lock")
    else:
        def normalize(items: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
            normalized = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                assignment = item.get("assignment") if isinstance(item.get("assignment"), dict) else item
                normalized.append((
                    str(item.get("shot_id", "")),
                    str(assignment.get("candidate_id", "")),
                    str(assignment.get("sha256", "")),
                ))
            return normalized

        if normalize(manifest_shots) != normalize(lock_shots):
            failures.append("approved clip assignments or hashes changed")

    branding = lock.get("branding") if isinstance(lock.get("branding"), dict) else {}
    captions = lock.get("captions") if isinstance(lock.get("captions"), dict) else {}
    if branding.get("logo_y") != 190 or branding.get("logo_width") != 360:
        failures.append("episode branding drifted from canonical logo geometry")
    if captions.get("margin_v") != 650:
        failures.append("episode captions drifted from canonical margin_v")

    return {
        "status": "EPISODE_SURFACE_LOCK_PASS" if not failures else "EPISODE_SURFACE_LOCK_BLOCKED",
        "episode_id": lock.get("episode_id"),
        "failures": failures,
        "render_allowed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--episode-manifest", type=Path)
    parser.add_argument("--surface-lock", type=Path)
    args = parser.parse_args()
    report = audit(args.repo_root)

    if report["status"] == "IMMUTABLE_CORE_PASS" and args.episode_manifest and args.surface_lock:
        try:
            manifest = _load_json(args.episode_manifest)
            lock = _load_json(args.surface_lock)
            episode_report = validate_episode_surface_lock(manifest, lock)
        except ImmutableCoreError as exc:
            report["status"] = "IMMUTABLE_CORE_BLOCKED"
            report["failures"].append(str(exc))
        else:
            report["episode_surface_lock"] = episode_report
            if episode_report["status"] != "EPISODE_SURFACE_LOCK_PASS":
                report["status"] = "IMMUTABLE_CORE_BLOCKED"
                report["failures"].extend(episode_report["failures"])

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "IMMUTABLE_CORE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
