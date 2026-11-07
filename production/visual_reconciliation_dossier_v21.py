"""Read-only V2.1 evidence-driven reconciliation dossier for media rights.

This is a diagnostic and a *draft* record generator, never an approval path.
It must not mutate a production record, plan, manifest, registry or file.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from production.visual_rights_consistency_v21 import _read_json


def _index(items: Any, field: str, failures: list[str], category: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(items, list):
        failures.append(f"{category} must be a list")
        return result
    for n, entry in enumerate(items):
        if not isinstance(entry, dict):
            failures.append(f"{category}[{n}] is not a record")
            continue
        key = str(entry.get(field) or "").strip()
        if not key or key in result:
            failures.append(f"{category}[{n}] has missing or duplicate {field}:{key}")
        else:
            result[key] = entry
    return result


def build_dossier(
    record: Mapping[str, Any], plan: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    problems: list[str] = []
    assets = _index(manifest.get("assets"), "candidate_id", problems, "manifest")
    candidates = _index(plan.get("candidates"), "candidate_id", problems, "plan")
    rights = _index(record.get("rights_ledger"), "asset_id", problems, "rights")
    episode = str(record.get("episode_id") or "")
    if not episode or episode != plan.get("episode_id") or episode != manifest.get("episode_id"):
        problems.append("episode identity mismatch")
    missing = sorted(set(assets) - set(rights))
    stale = sorted(set(rights) - set(assets))
    approved_manifest_only: list[str] = []
    pending_visual: list[str] = []
    provenance_mismatches: list[str] = []
    draft_entries: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for asset_id, asset in sorted(assets.items()):
        candidate = candidates.get(asset_id, {})
        intake = candidate.get("intake_artifact") if isinstance(candidate.get("intake_artifact"), Mapping) else {}
        qa = candidate.get("qa") if isinstance(candidate.get("qa"), Mapping) else {}
        existing = rights.get(asset_id)
        provenance = bool(
            candidate
            and str(intake.get("sha256") or "") == str(asset.get("sha256") or "")
            and str(intake.get("perceptual_hash") or "") == str(asset.get("perceptual_hash") or "")
            and str(candidate.get("source_page_url") or "") == str(asset.get("source_page_url") or "")
            and str(candidate.get("license_name") or "") == str(asset.get("license_name") or "")
        )
        if not provenance:
            provenance_mismatches.append(asset_id)
        manifest_approved = bool(
            candidate.get("rights_status") == "APPROVED_FOR_MANIFEST_ONLY"
            and qa.get("human_approval") == "APPROVED_FOR_MANIFEST"
            and asset.get("rights_status") == "APPROVED_FOR_MANIFEST_ONLY"
            and asset.get("human_approval") == "APPROVED_FOR_MANIFEST"
        )
        if not manifest_approved:
            pending_visual.append(asset_id)
        if asset_id in missing and manifest_approved and provenance:
            approved_manifest_only.append(asset_id)
        render_rights_match = bool(
            existing
            and provenance
            and existing.get("rights_status") == "APPROVED"
            and existing.get("approved_for_render") is True
            and existing.get("approval_scope") == f"{episode}-render"
            and existing.get("sha256") == asset.get("sha256")
            and existing.get("perceptual_fingerprint") == asset.get("perceptual_hash")
            and existing.get("source_url") == asset.get("source_page_url")
        )
        if asset_id in missing:
            draft_entries.append({
                "asset_id": asset_id,
                "episode_id": episode,
                "source_url": candidate.get("source_page_url"),
                "provider": candidate.get("provider"),
                "license_name_claimed": candidate.get("license_name"),
                "source_sha256": intake.get("sha256"),
                "source_perceptual_fingerprint": intake.get("perceptual_hash"),
                "intake_workflow_run_id": intake.get("workflow_run_id"),
                "intake_artifact_id": intake.get("artifact_id"),
                "plan_human_approval": qa.get("human_approval"),
                "manifest_provenance_consistent": provenance,
                "verification_scope": "DOCUMENTED_METADATA_ONLY",
                "rights_status": "PENDING_INDEPENDENT_RENDER_RIGHTS",
                "approved_for_render": False,
                "license_and_third_party_review": "PENDING",
                "user_approval_inferred": False,
                "automated_promotion": False,
                "global_catalog_updated": False,
            })
        items.append({
            "asset_id": asset_id,
            "plan_manifest_approval": manifest_approved,
            "source_provenance_matched": provenance,
            "render_ledger_exists": existing is not None,
            "render_rights_matched": render_rights_match,
            "user_approval_inferred": False,
            "requires_manual_rights_reconciliation": not render_rights_match,
        })
    is_coherent = (
        not problems and not missing and not stale and not pending_visual
        and not provenance_mismatches and all(x["render_rights_matched"] for x in items)
    )
    return {
        "schema_version": "1.0",
        "gate": "VISUAL_RECONCILIATION_DOSSIER",
        "status": "EVIDENCE_CONSISTENT_NOT_RENDER_AUTHORIZED" if is_coherent else "RECONCILIATION_REQUIRED",
        "episode_id": episode,
        "asset_count": len(assets),
        "render_rights_matched_count": sum(bool(x["render_rights_matched"]) for x in items),
        "missing_render_rights": missing,
        "stale_render_rights": stale,
        "approved_manifest_only_pending_render_rights": sorted(approved_manifest_only),
        "pending_visual_approval": sorted(pending_visual),
        "source_provenance_mismatches": sorted(provenance_mismatches),
        "structural_issues": problems,
        "draft_pending_rights_not_canonical": draft_entries,
        "assets": items,
        "production_enablement": False,
        "media_generation": "NOT_RUN",
        "render": "NOT_RUN",
        "publication": "NOT_RUN",
        "warning": "A draft record, public license webpage or package PASS is not an independent render authorization.",
    }


def inspect_repo(repo_root: Path, record_path: str) -> dict[str, Any]:
    record = _read_json(repo_root, record_path)
    visual_path = str(record.get("visual_manifest_reference") or "")
    manifest = _read_json(repo_root, visual_path)
    plan = _read_json(repo_root, str(manifest.get("source_plan") or ""))
    return build_dossier(record, plan, manifest)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--record", type=str, required=True)
    a = p.parse_args()
    result = inspect_repo(a.repo_root.resolve(), a.record)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    # Expected blocked state is successful reporting; never authorizes media.
    return 0 if not result["structural_issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
