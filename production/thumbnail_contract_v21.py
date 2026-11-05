"""Thumbnail concept and delivery-manifest validation for V2.1."""
from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REQUIRED_FINAL_FIELDS = ("episode_id", "story_id", "incident_id", "title_variant", "thumbnail_text", "hero_asset_id", "visual_truth_class", "source_url", "rights_status", "sha256", "dimensions", "safe_margin_status", "mobile_legibility_status", "human_review_status", "youtube_thumbnail_mode", "tiktok_cover_mode", "final_status", "delivery_paths")
REQUIRED_DELIVERY_PATHS = ("thumbnail_master_9x16_png", "thumbnail_master_9x16_jpg", "thumbnail_source_frame", "thumbnail_preview_mobile", "platform_cover_record")

def validate_thumbnail_concept(record: Mapping[str, Any]) -> dict[str, Any]:
    concept = record.get("thumbnail_concept")
    failures: list[str] = []
    if not isinstance(concept, Mapping):
        failures.append("thumbnail_concept is required at PACKAGE_GATE_PRE")
    else:
        for field in ("concept_id", "title_alignment", "hero_visual", "thumbnail_text", "visual_truth_class"):
            if not concept.get(field):
                failures.append(f"thumbnail_concept missing:{field}")
        if concept.get("visual_truth_class") == "DOCUMENTARY_EVIDENCE" and not concept.get("source_url"):
            failures.append("documentary thumbnail evidence requires source_url")
    return {"gate": "THUMBNAIL_CONCEPT", "status": "PASS" if not failures else "BLOCKED", "failures": failures}

def validate_thumbnail_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    failures = [f"missing:{field}" for field in REQUIRED_FINAL_FIELDS if manifest.get(field) in (None, "", [])]
    paths = manifest.get("delivery_paths")
    if not isinstance(paths, Mapping):
        failures.append("delivery_paths must be an object")
    else:
        failures.extend(f"delivery_paths missing:{field}" for field in REQUIRED_DELIVERY_PATHS if not paths.get(field))
    if manifest.get("dimensions") not in ([1080, 1920], (1080, 1920), "1080x1920"):
        failures.append("thumbnail dimensions must be 1080x1920")
    if manifest.get("safe_margin_status") != "PASS":
        failures.append("safe_margin_status must be PASS")
    if manifest.get("mobile_legibility_status") != "PASS":
        failures.append("mobile_legibility_status must be PASS")
    if manifest.get("human_review_status") != "APPROVED":
        failures.append("human_review_status must be APPROVED")
    if manifest.get("final_status") != "APPROVED":
        failures.append("final_status must be APPROVED")
    if manifest.get("rights_status") != "APPROVED":
        failures.append("hero rights must be APPROVED")
    if manifest.get("visual_truth_class") == "DOCUMENTARY_EVIDENCE" and not manifest.get("source_url"):
        failures.append("documentary evidence needs source_url")
    return {"gate": "THUMBNAIL_QA", "status": "PASS" if not failures else "BLOCKED", "failures": failures}

def validate_thumbnail_files(manifest: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    paths = manifest.get("delivery_paths") or {}
    for key in REQUIRED_DELIVERY_PATHS:
        raw = paths.get(key)
        if not isinstance(raw, str) or not raw.strip():
            failures.append(f"{key} path is missing")
            continue
        candidate = (repo_root / raw).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            failures.append(f"{key} path escapes repository")
            continue
        if not candidate.is_file():
            failures.append(f"{key} file does not exist:{raw}")
    for key in ("thumbnail_master_9x16_png", "thumbnail_master_9x16_jpg", "thumbnail_preview_mobile"):
        raw = paths.get(key)
        if not raw:
            continue
        candidate = (repo_root / raw).resolve()
        if not candidate.is_file():
            continue
        try:
            from PIL import Image
            with Image.open(candidate) as image:
                if image.size != (1080, 1920):
                    failures.append(f"{key} dimensions are {image.size}, expected (1080, 1920)")
        except Exception as exc:
            failures.append(f"{key} cannot be inspected:{exc}")
    return {"gate": "THUMBNAIL_FILES", "status": "PASS" if not failures else "BLOCKED", "failures": failures}

def platform_status(manifest: Mapping[str, Any]) -> dict[str, str]:
    return {"youtube_shorts": str(manifest.get("youtube_thumbnail_mode", "PENDING")), "tiktok": str(manifest.get("tiktok_cover_mode", "PENDING"))}
