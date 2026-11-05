#!/usr/bin/env python3
"""Fail-closed structural contract for Episode 005 visual acquisition.

This validator does not approve media for render. It checks that the
search-v2 plan, partial manifest, rights evidence and no-reuse assignments
remain internally consistent before any manual media batch is dispatched.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MIXKIT_LICENSE = "Mixkit Stock Video Free License"
CANDIDATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
SHOT_ID_PATTERN = re.compile(r"^S[0-9]{2}$")


class VisualPlanContractError(ValueError):
    """Raised when the visual plan or manifest is structurally inconsistent."""


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def validate_visual_plan(plan: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    strategy = plan.get("search_strategy")
    if not isinstance(strategy, dict):
        errors.append("search_strategy is required")
        strategy = {}

    if strategy.get("mode") != "BATCH_SHORTLIST_THEN_INTAKE":
        errors.append("search_strategy.mode must be BATCH_SHORTLIST_THEN_INTAKE")
    if strategy.get("version") != "search-v2":
        errors.append("search_strategy.version must be search-v2")

    batch = strategy.get("discovery_batch")
    if not isinstance(batch, dict):
        errors.append("search_strategy.discovery_batch is required")
        batch = {}
    for field in ("candidates_per_unresolved_shot", "shortlist_size_per_shot"):
        if not isinstance(batch.get(field), int) or batch[field] <= 0:
            errors.append(f"discovery_batch.{field} must be a positive integer")
    if batch.get("shortlist_size_per_shot", 0) > batch.get("candidates_per_unresolved_shot", 0):
        errors.append("shortlist_size_per_shot cannot exceed candidates_per_unresolved_shot")

    weights = strategy.get("scoring_weights")
    if not isinstance(weights, dict) or sum(weights.values()) != 100:
        errors.append("scoring_weights must be numeric and sum to 100")

    thresholds = strategy.get("score_thresholds")
    if not isinstance(thresholds, dict):
        errors.append("score_thresholds is required")
        thresholds = {}
    hard_reject = thresholds.get("hard_reject_below")
    shortlist = thresholds.get("shortlist_for_intake")
    approval = thresholds.get("request_manifest_approval")
    if not all(isinstance(item, (int, float)) for item in (hard_reject, shortlist, approval)):
        errors.append("all score thresholds must be numeric")
    elif not hard_reject < shortlist <= approval:
        errors.append("score thresholds must satisfy hard_reject < shortlist <= approval")

    queue = strategy.get("unresolved_shot_queue", [])
    queue_ids = [
        str(item.get("shot_id"))
        for item in queue
        if isinstance(item, dict) and item.get("shot_id")
    ]
    if _duplicates(queue_ids):
        errors.append(f"duplicate unresolved shot IDs: {_duplicates(queue_ids)}")
    if any(not SHOT_ID_PATTERN.fullmatch(shot_id) for shot_id in queue_ids):
        errors.append("unresolved shot IDs must use the S## format")

    candidates = [
        item for item in plan.get("candidates", [])
        if isinstance(item, dict)
    ]
    candidate_ids = [str(item.get("candidate_id", "")) for item in candidates]
    if not all(CANDIDATE_ID_PATTERN.fullmatch(candidate_id) for candidate_id in candidate_ids):
        errors.append("all candidate IDs must use safe filename characters")
    if _duplicates(candidate_ids):
        errors.append(f"duplicate candidate IDs: {_duplicates(candidate_ids)}")

    source_pages = [
        str(item["source_page_url"])
        for item in candidates
        if item.get("source_page_url")
    ]
    media_urls = [
        str(item["media_url"])
        for item in candidates
        if item.get("media_url")
    ]
    if _duplicates(source_pages):
        errors.append(f"duplicate source pages: {_duplicates(source_pages)}")
    if _duplicates(media_urls):
        errors.append(f"duplicate media URLs: {_duplicates(media_urls)}")

    approved_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id", ""))
        status = str(candidate.get("rights_status", ""))
        if status == "APPROVED_FOR_MANIFEST_ONLY":
            approved_ids.add(candidate_id)
            required = ("source_page_url", "media_url", "license_name", "intake_artifact", "qa")
            for field in required:
                if not candidate.get(field):
                    errors.append(f"{candidate_id}: approved candidate missing {field}")
            if candidate.get("provider") == "mixkit" and candidate.get("license_name") != MIXKIT_LICENSE:
                errors.append(f"{candidate_id}: Mixkit license is not the approved commercial license")
            if candidate.get("approved_for_render") is True:
                errors.append(f"{candidate_id}: approved manifest candidate cannot approve render")
            if candidate.get("global_catalog_updated") is True:
                errors.append(f"{candidate_id}: plan candidate cannot mutate global catalog")

        if (
            candidate.get("provider") == "mixkit"
            and candidate.get("media_url")
            and not status.startswith("REJECTED")
        ):
            license_name = candidate.get("license_name")
            if license_name != MIXKIT_LICENSE:
                errors.append(f"{candidate_id}: Mixkit media candidate has invalid or missing license")

    if manifest.get("episode_id") != plan.get("episode_id"):
        errors.append("manifest episode_id does not match plan episode_id")
    if manifest.get("source_plan") != "episodes/episode-005/visual/asset-acquisition-plan.json":
        errors.append("manifest source_plan is not the canonical acquisition plan")

    assets = [
        item for item in manifest.get("assets", [])
        if isinstance(item, dict)
    ]
    manifest_ids = [str(item.get("candidate_id", "")) for item in assets]
    if _duplicates(manifest_ids):
        errors.append(f"duplicate manifest candidate IDs: {_duplicates(manifest_ids)}")
    if not set(manifest_ids).issubset(approved_ids):
        errors.append("manifest contains a candidate not approved for manifest-only use")

    for asset in assets:
        candidate_id = str(asset.get("candidate_id", ""))
        if asset.get("approved_for_render") is not False:
            errors.append(f"{candidate_id}: manifest asset must keep approved_for_render=false")
        if asset.get("global_catalog_updated") is not False:
            errors.append(f"{candidate_id}: manifest asset must keep global_catalog_updated=false")
        if asset.get("drive_written") is not False:
            errors.append(f"{candidate_id}: manifest asset must keep drive_written=false")
        if asset.get("rights_status") != "APPROVED_FOR_MANIFEST_ONLY":
            errors.append(f"{candidate_id}: manifest rights status is not manifest-only")

    assignments: dict[str, list[str]] = {}
    for shot in manifest.get("shot_assignments", []):
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id", ""))
        assignment = shot.get("assignment")
        if not assignment:
            continue
        candidate_id = str(assignment.get("candidate_id", ""))
        assignments.setdefault(candidate_id, []).append(shot_id)
    reused = {candidate_id: shots for candidate_id, shots in assignments.items() if len(shots) > 1}
    if reused:
        errors.append(f"candidate assigned to multiple shots: {reused}")

    unresolved = set(str(item) for item in manifest.get("unresolved_shots", []))
    assigned_shots = {
        str(shot.get("shot_id"))
        for shot in manifest.get("shot_assignments", [])
        if isinstance(shot, dict) and shot.get("assignment")
    }
    if unresolved & assigned_shots:
        errors.append(f"shots cannot be both unresolved and assigned: {sorted(unresolved & assigned_shots)}")

    if errors:
        raise VisualPlanContractError("; ".join(errors))

    return {
        "status": "VISUAL_PLAN_CONTRACT_PASS",
        "episode_id": plan.get("episode_id"),
        "candidate_count": len(candidates),
        "approved_manifest_candidate_count": len(approved_ids),
        "manifest_asset_count": len(assets),
        "assigned_shot_count": len(assigned_shots),
        "unresolved_shot_count": len(unresolved),
        "promotion_allowed": False,
        "render_allowed": False,
        "global_catalog_updated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = validate_visual_plan(plan, manifest)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
