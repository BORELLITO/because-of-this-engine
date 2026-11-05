"""Thumbnail concept and delivery-manifest validation for V2.1."""
from __future__ import annotations
from collections.abc import Mapping

REQUIRED_FINAL_FIELDS = ("episode_id","story_id","incident_id","title_variant","thumbnail_text","hero_asset_id","visual_truth_class","source_url","rights_status","sha256","dimensions","safe_margin_status","mobile_legibility_status","human_review_status","youtube_thumbnail_mode","tiktok_cover_mode","final_status")

def validate_thumbnail_concept(record: Mapping) -> dict:
    concept = record.get("thumbnail_concept"); failures = []
    if not isinstance(concept,Mapping): failures.append("thumbnail_concept is required at PACKAGE_GATE_PRE")
    else:
        for field in ("concept_id","title_alignment","hero_visual","thumbnail_text","visual_truth_class"):
            if not concept.get(field): failures.append(f"thumbnail_concept missing:{field}")
        if concept.get("visual_truth_class") == "DOCUMENTARY_EVIDENCE" and not concept.get("source_url"): failures.append("documentary thumbnail evidence requires source_url")
    return {"gate":"THUMBNAIL_CONCEPT","status":"PASS" if not failures else "BLOCKED","failures":failures}

def validate_thumbnail_manifest(manifest: Mapping) -> dict:
    failures = [f"missing:{field}" for field in REQUIRED_FINAL_FIELDS if manifest.get(field) in (None,"",[])]
    if manifest.get("dimensions") not in ("1080x1920",[1080,1920],{"width":1080,"height":1920}): failures.append("dimensions must be 1080x1920")
    if manifest.get("safe_margin_status") != "PASS": failures.append("safe_margin_status must be PASS")
    if manifest.get("mobile_legibility_status") != "PASS": failures.append("mobile_legibility_status must be PASS")
    if manifest.get("human_review_status") != "APPROVED": failures.append("human_review_status must be APPROVED")
    if manifest.get("final_status") != "APPROVED": failures.append("final_status must be APPROVED")
    if manifest.get("rights_status") != "APPROVED": failures.append("hero rights must be APPROVED")
    if manifest.get("visual_truth_class") == "DOCUMENTARY_EVIDENCE" and not manifest.get("source_url"): failures.append("documentary evidence needs source_url")
    return {"gate":"THUMBNAIL_QA","status":"PASS" if not failures else "BLOCKED","failures":failures}

def platform_status(manifest: Mapping) -> dict[str,str]:
    return {"youtube_shorts":str(manifest.get("youtube_thumbnail_mode","PENDING")),"tiktok":str(manifest.get("tiktok_cover_mode","PENDING"))}
