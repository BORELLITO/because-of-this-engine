"""Read-only cross-ledger gate for V2.1 visual release.

Fail closed when the acquisition plan, scene manifest, production rights ledger
and scoped human authorization disagree. Does not grant render/publication.
"""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _read_json(root: Path, path: str) -> dict[str, Any]:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("visual path is absent")
    root = root.resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("visual path escapes repository") from exc
    value = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("visual JSON must be an object")
    return value


def _ids(items: Any, key: str, label: str, failures: list[str]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    if not isinstance(items, list):
        failures.append(f"{label}: not a list")
        return result
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            failures.append(f"{label}[{index}]: not an object")
            continue
        identity = str(item.get(key) or "").strip()
        if not identity:
            failures.append(f"{label}[{index}]: missing {key}")
        elif identity in result:
            failures.append(f"{label}: duplicate ID {identity}")
        else:
            result[identity] = item
    return result


def _url(value: Any) -> str:
    return str(value or "").strip().rstrip("/")


def validate_visual_rights_consistency(
    record: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    report: dict[str, Any] = {
        "gate": "VISUAL_RIGHTS_CONSISTENCY",
        "status": "BLOCKED",
        "failures": failures,
        "render": "NOT_RUN",
        "publication": "NOT_RUN",
    }
    try:
        scene = _read_json(repo_root, str(record.get("visual_manifest_reference") or ""))
        plan = _read_json(repo_root, str(scene.get("source_plan") or ""))
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        failures.append(f"visual evidence unavailable: {exc}")
        return report

    episode_id = str(record.get("episode_id") or "")
    if not episode_id or scene.get("episode_id") != episode_id or plan.get("episode_id") != episode_id:
        failures.append("episode identity differs between production record, visual manifest and plan")

    assets = _ids(scene.get("assets"), "candidate_id", "scene.assets", failures)
    candidates = _ids(plan.get("candidates"), "candidate_id", "plan.candidates", failures)
    ledger = _ids(record.get("rights_ledger"), "asset_id", "record.rights_ledger", failures)
    if not assets or not ledger:
        failures.append("visual assets or rights ledger empty")
    missing = sorted(set(assets) - set(ledger))
    stale = sorted(set(ledger) - set(assets))
    if missing:
        failures.append("visual assets missing render rights: " + ",".join(missing))
    if stale:
        failures.append("rights entries refer to inactive visual assets: " + ",".join(stale))

    assignments = scene.get("shot_assignments")
    if not isinstance(assignments, list) or not assignments:
        failures.append("shot assignments missing")
    else:
        assigned_ids: list[str] = []
        shot_ids: list[str] = []
        for shot in assignments:
            if not isinstance(shot, Mapping):
                failures.append("invalid shot assignment")
                continue
            sid = str(shot.get("shot_id") or "")
            assignment = shot.get("assignment")
            aid = str((assignment or {}).get("candidate_id") or "") if isinstance(assignment, Mapping) else ""
            if not aid or not sid:
                failures.append("incomplete shot assignment")
                continue
            assigned_ids.append(aid)
            shot_ids.append(sid)
        if len(shot_ids) != len(set(shot_ids)):
            failures.append("duplicate shot IDs")
        if set(assigned_ids) != set(assets):
            failures.append("assigned asset set differs from visual manifest")
        if len(assigned_ids) != len(set(assigned_ids)):
            failures.append("asset reused in more than one shot")

    authorization = record.get("render_authorization")
    if not isinstance(authorization, Mapping) or authorization.get("status") != "APPROVED":
        failures.append("scoped render authorization absent")
    for asset_id, asset in assets.items():
        candidate = candidates.get(asset_id)
        right = ledger.get(asset_id)
        if candidate is None:
            failures.append(f"{asset_id}: missing acquisition candidate")
            continue
        if candidate.get("rights_status") != "APPROVED_FOR_MANIFEST_ONLY" or (candidate.get("qa") or {}).get("human_approval") != "APPROVED_FOR_MANIFEST":
            failures.append(f"{asset_id}: plan does not record human manifest approval")
        if asset.get("rights_status") != "APPROVED_FOR_MANIFEST_ONLY" or asset.get("human_approval") != "APPROVED_FOR_MANIFEST":
            failures.append(f"{asset_id}: manifest approval invalid")
        if asset.get("approved_for_render") is not False:
            failures.append(f"{asset_id}: manifest must not promote render permission")
        intake = candidate.get("intake_artifact") or {}
        for field, actual, expected in (
            ("source page", _url(asset.get("source_page_url")), _url(candidate.get("source_page_url"))),
            ("SHA-256", asset.get("sha256"), intake.get("sha256")),
            ("perceptual identity", asset.get("perceptual_hash"), intake.get("perceptual_hash")),
            ("license", asset.get("license_name"), candidate.get("license_name")),
        ):
            if not actual or not expected or actual != expected:
                failures.append(f"{asset_id}: manifest {field} differs from approved acquisition")
        if right is None:
            continue
        for field, actual, expected in (
            ("source URL", _url(right.get("source_url")), _url(asset.get("source_page_url"))),
            ("SHA-256", right.get("sha256"), asset.get("sha256")),
            ("perceptual identity", right.get("perceptual_fingerprint"), asset.get("perceptual_hash")),
            ("license", right.get("license_name"), asset.get("license_name")),
        ):
            if not actual or not expected or actual != expected:
                failures.append(f"{asset_id}: render rights {field} mismatch")
        if right.get("rights_status") != "APPROVED" or right.get("approved_for_render") is not True:
            failures.append(f"{asset_id}: render rights not independently approved")
        if right.get("approval_scope") != f"{episode_id}-render":
            failures.append(f"{asset_id}: incorrect render approval scope")
        if episode_id not in (right.get("used_by") or []):
            failures.append(f"{asset_id}: rights ledger does not list episode use")

    report["asset_count"] = len(assets)
    report["rights_entry_count"] = len(ledger)
    report["status"] = "PASS" if not failures else "BLOCKED"
    return report
