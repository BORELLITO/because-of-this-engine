"""Autonomous, evidence-bound scoped stock video rights decision gate (V2.1).

Decision is deterministic, based on inspected media receipts and approved provider
policy: APPROVE when safe, BLOCK when evidence or contextual safeguards are missing.
Never grants permissions for a publisher, an identifiable person or copyright
holder; final-render and publication gates remain independent.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from production.visual_rights_consistency_v21 import _read_json
from production.scene_disclosures_v21 import ACTOR_ID, NASA_ID, SCENE_PATH, validate_disclosure

APPROVED_STATUS = "AUTO_APPROVED_EVIDENCE_BOUND_V21"
PENDING_STATUS = "PENDING_INDEPENDENT_RENDER_RIGHTS"
REVIEW_REPORT = "reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json"
EXPECTED_POLICY_URL = {
    "pexels": "https://www.pexels.com/license/",
    "pixabay": "https://pixabay.com/service/terms/",
    "nasa": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
}
PROVIDER_DOMAINS = {"pexels": "www.pexels.com", "pixabay": "pixabay.com", "nasa": "svs.gsfc.nasa.gov"}


def _asset_map(values: Any, key: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        raise ValueError("expected list of asset evidence")
    index: dict[str, Mapping[str, Any]] = {}
    for val in values:
        if not isinstance(val, Mapping):
            raise ValueError("asset evidence not an object")
        ident = str(val.get(key) or "").strip()
        if not ident or ident in index:
            raise ValueError(f"missing or duplicate {key}:{ident}")
        index[ident] = val
    return index


def _provider_url_is_genuine(url: Any, provider: str) -> bool:
    try:
        data = urlparse(str(url))
        return data.scheme == "https" and data.hostname == PROVIDER_DOMAINS[provider]
    except (KeyError, ValueError):
        return False


def decide_one(
    right: Mapping[str, Any],
    candidate: Mapping[str, Any] | None,
    asset: Mapping[str, Any] | None,
    evidence: Mapping[str, Any] | None,
    *,
    verified_disclosure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    asset_id = str(right.get("asset_id") or "")
    reasons: list[str] = []
    if not candidate or not asset or not evidence:
        return {"asset_id": asset_id, "decision": "BLOCKED_MISSING_EVIDENCE",
                "reasons": ["plan, scene asset or independent review evidence missing"],
                "allow_scoped_render": False}
    provider = str(right.get("provider") or "")
    if provider not in EXPECTED_POLICY_URL:
        reasons.append("provider not supported by V2.1 rights policy")
    elif (not _provider_url_is_genuine(right.get("source_url"), provider)
            or evidence.get("reviewed_source_license_policy") != EXPECTED_POLICY_URL[provider]):
        reasons.append("official provider item/license URL not verified")
    if (right.get("asset_id") != asset.get("candidate_id")
            or right.get("asset_id") != candidate.get("candidate_id")
            or right.get("asset_id") != evidence.get("asset_id")):
        reasons.append("asset identifiers disagree")
    if (right.get("source_url") != asset.get("source_page_url")
            or right.get("source_url") != candidate.get("source_page_url")
            or right.get("source_url") != evidence.get("source_page_url")):
        reasons.append("source URLs disagree")
    if (right.get("sha256") != asset.get("sha256")
            or right.get("sha256") != (candidate.get("intake_artifact") or {}).get("sha256")
            or right.get("sha256") != evidence.get("verified_source_sha256")):
        reasons.append("actual source SHA-256 evidence mismatched")
    if (right.get("perceptual_fingerprint") != asset.get("perceptual_hash")
            or right.get("perceptual_fingerprint") != (candidate.get("intake_artifact") or {}).get("perceptual_hash")
            or right.get("perceptual_fingerprint") != evidence.get("verified_source_perceptual_fingerprint")):
        reasons.append("actual source perceptual identity mismatched")
    if (evidence.get("content_archive_id") != (candidate.get("intake_artifact") or {}).get("artifact_id")
            or not evidence.get("original_video_sha256_verified_from_recovered_zip")
            or evidence.get("content_qa_method") != "FIVE_FRAMES_NATIVE_AND_9X16_OR_EQUIVALENT"
            or evidence.get("content_review_status") != "VISUAL_EVIDENCE_INSPECTED_2026_11_07"):
        reasons.append("real media sample review and immutable intake evidence absent")
    if evidence.get("visual_brand_class") != "none_observed":
        reasons.append("logo or brand clearance is not established")
    if evidence.get("visual_person_class") not in {"none", "hands_only_unidentifiable"}:
        if not (asset_id == ACTOR_ID and isinstance(verified_disclosure, Mapping)
                and verified_disclosure.get("not_actual_stanislav_petrov") is True
                and verified_disclosure.get("no_actor_endorsement") is True
                and verified_disclosure.get("overlay_render_sample_verified") is True):
            reasons.append("identifiable person or depiction risk unresolved")
    if evidence.get("editorial_truth_class") != asset.get("truth_class"):
        reasons.append("footage truth class mismatch")
    if (evidence.get("source_audio_policy") != "strip"
            or not evidence.get("nonarchival_context_required")
            or not evidence.get("permitted_narrative_framing")):
        reasons.append("required stock-fidelity or source-audio context missing")
    if (candidate.get("rights_status") != "APPROVED_FOR_MANIFEST_ONLY"
            or (candidate.get("qa") or {}).get("human_approval") != "APPROVED_FOR_MANIFEST"
            or asset.get("rights_status") != "APPROVED_FOR_MANIFEST_ONLY"):
        reasons.append("scene continuity/editorial intake QA not complete")
    coll= (candidate.get("intake_artifact") or {})
    if any(coll.get(k) is True for k in ("global_sha256_collision", "global_perceptual_collision", "global_source_collision")):
        reasons.append("detected global media reuse")
    if not evidence.get("official_item_page_verified"):
        reasons.append("source item page has not been verified")
    if provider == "nasa":
        # The final release cannot yet be certified, but a VERIFIED source
        # preview can be cleared for scoped *nonpublishing* video rendering
        # when actual in-scene model labels and description credits are locked.
        credits_sample_locked = (
            asset_id == NASA_ID
            and isinstance(verified_disclosure, Mapping)
            and verified_disclosure.get("overlay_render_sample_verified") is True
            and verified_disclosure.get("no_nasa_endorsement") is True
            and verified_disclosure.get("final_assembled_video_metadata_verified") is False
        )
        if (not evidence.get("nasa_required_credits")
                or not evidence.get("nasa_required_truth_notice")
                or not credits_sample_locked):
            reasons.append("NASA source credits and truthful 2020 model disclosure not verified in source QA")
    return {
        "asset_id": asset_id,
        "decision": "AUTO_APPROVED_FOR_SCOPED_RENDER" if not reasons else "BLOCKED_PENDING_SAFEGUARDS",
        "reasons": reasons,
        "allow_scoped_render": not reasons,
        "license_scope": "ONE_FACTUAL_EDITORIAL_VIDEO_ON_YOUTUBE_AND_TIKTOK_WITH_GUARDS",
        "independent_publication_authorization": False,
        "frame_scope": "SOURCE_AND_SAMPLED_FRAMES_NOT_FULL_PUBLISHED_MASTER",
    }


def audit(record: Mapping[str, Any], plan: Mapping[str, Any],
          scene: Mapping[str, Any], evidence: Mapping[str, Any],
          disclosure_contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    problems: list[str] = []
    try:
        candidates = _asset_map(plan.get("candidates"), "candidate_id")
        assets = _asset_map(scene.get("assets"), "candidate_id")
        rights = _asset_map(record.get("rights_ledger"), "asset_id")
        reviews = _asset_map(evidence.get("reviewed_assets"), "asset_id")
    except ValueError as exc:
        return {"gate": "RIGHTS_AUTONOMY_V21", "status": "BLOCKED",
                "failures": [str(exc)], "decisions": []}
    expected_episode = str(record.get("episode_id") or "")
    if (evidence.get("episode_id") != expected_episode or plan.get("episode_id") != expected_episode
            or scene.get("episode_id") != expected_episode):
        problems.append("rights decision episode identity does not match scene and record")
    verified_disclosures: dict[str, Mapping[str, Any]] = {}
    if disclosure_contract is not None:
        disclosure_report = validate_disclosure(scene, disclosure_contract)
        if disclosure_report["status"] == "PASS":
            verified_disclosures = {
                str(item["asset_id"]): item
                for item in disclosure_contract.get("disclosures", [])
                if isinstance(item, Mapping) and item.get("asset_id")
            }
        else:
            problems.append("scene disclaimer contract failed: " + "; ".join(disclosure_report["failures"]))
    decisions = []
    for asset_id in sorted(reviews):
        current = rights.get(asset_id)
        if current is None:
            problems.append(f"{asset_id}: audited rights entry missing from active record")
            continue
        result = decide_one(
            current, candidates.get(asset_id), assets.get(asset_id),
            reviews[asset_id], verified_disclosure=verified_disclosures.get(asset_id),
        )
        decisions.append(result)
        should_be_approved = result["allow_scoped_render"]
        if should_be_approved:
            if not (current.get("rights_status") == "APPROVED"
                    and current.get("approved_for_render") is True
                    and current.get("commercial_use") is True
                    and current.get("approval_scope") == f"{expected_episode}-render"
                    and current.get("render_approval_status") == APPROVED_STATUS
                    and set(current.get("platform_scope") or []) >= {"youtube_shorts", "tiktok"}
                    and (expected_episode in (current.get("used_by") or []))):
                problems.append(f"{asset_id}: engine-approved evidence not reflected in scoped rights ledger")
        elif (current.get("rights_status") != PENDING_STATUS
              or current.get("approved_for_render") is not False
              or current.get("commercial_use") is not False):
            problems.append(f"{asset_id}: unsafe attempt to approve unresolved media rights")
    for asset_id, val in rights.items():
        if val.get("render_approval_status") == APPROVED_STATUS and asset_id not in reviews:
            problems.append(f"{asset_id}: auto-approved rights lack source evidence review")
    return {
        "gate": "RIGHTS_AUTONOMY_V21", "status": "PASS" if not problems else "BLOCKED",
        "failures": problems, "decisions": decisions,
        "auto_approved_count": sum(1 for x in decisions if x["allow_scoped_render"]),
        "blocked_count": sum(1 for x in decisions if not x["allow_scoped_render"]),
        "render_executed": False, "publication_executed": False,
        "notes": "PASS asserts decision/ledger alignment, not release eligibility. Other gates still apply.",
    }


def audit_repository(record: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    path = record.get("autonomous_rights_evidence_path")
    if not path:
        if any(e.get("render_approval_status") == APPROVED_STATUS for e in record.get("rights_ledger", [])
               if isinstance(e, Mapping)):
            return {"gate": "RIGHTS_AUTONOMY_V21", "status": "BLOCKED",
                    "failures": ["auto-approved rights without audit file"], "decisions": []}
        return {"gate": "RIGHTS_AUTONOMY_V21", "status": "PASS",
                "failures": [], "decisions": [], "scope": "NO_AUTONOMOUS_RIGHTS_DECLARED"}
    try:
        scene = _read_json(repo_root, str(record.get("visual_manifest_reference") or ""))
        plan = _read_json(repo_root, str(scene.get("source_plan") or ""))
        evidence = _read_json(repo_root, str(path))
        disclosure = None
        sensitive_ids = {str(x.get("candidate_id")) for x in scene.get("assets", [])
                         if isinstance(x, Mapping)} & {ACTOR_ID, NASA_ID}
        if sensitive_ids:
            if scene.get("scene_disclosure_contract") != SCENE_PATH:
                return {"gate": "RIGHTS_AUTONOMY_V21", "status": "BLOCKED",
                        "failures": ["S01/S12 source disclaimer contract missing"],
                        "decisions": []}
            disclosure = _read_json(repo_root, SCENE_PATH)
        return audit(record, plan, scene, evidence, disclosure_contract=disclosure)
    except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        return {"gate": "RIGHTS_AUTONOMY_V21", "status": "BLOCKED",
                "failures": [f"unreadable evidence:{exc}"], "decisions": []}


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--record",required=True)
    args=p.parse_args()
    root=args.repo_root.resolve()
    result=audit_repository(_read_json(root,args.record),repo_root=root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["status"]=="PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
