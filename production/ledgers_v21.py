"""Source, rights and global no-reuse contracts for V2.1."""
from __future__ import annotations
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)

class RegistryError(ValueError):
    """Raised when the global asset catalog is missing or incomplete."""

def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _status(name: str, passed: bool, failures: list[str], warnings: list[str]) -> dict[str, Any]:
    return {"ledger": name, "status": "PASS" if passed else "BLOCKED", "failures": failures, "warnings": warnings}

def validate_source_ledger(record: Mapping[str, Any]) -> dict[str, Any]:
    entries = record.get("source_ledger")
    failures: list[str] = []
    warnings: list[str] = []
    if not isinstance(entries, list) or not entries:
        return _status("source_ledger", False, ["source_ledger is absent or empty"], warnings)
    by_claim: dict[str, list[Mapping[str, Any]]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            failures.append(f"entry[{index}] is not an object")
            continue
        claim_id = entry.get("claim_id")
        by_claim.setdefault(str(claim_id), []).append(entry)
        required = ("claim_id", "claim_text", "source_url", "source_type", "publisher_or_author", "publication_date", "primary_or_secondary", "corroboration_source", "reliability_notes", "accessed_at", "evidence_excerpt_or_note", "visual_support", "fact_check_status")
        failures.extend(f"entry[{index}] missing:{field}" for field in required if not _text(entry.get(field)))
        if entry.get("fact_check_status") not in {"VERIFIED", "PASS"}:
            failures.append(f"entry[{index}] fact_check_status is not verified")
        if entry.get("primary_or_secondary") not in {"primary", "secondary"}:
            failures.append(f"entry[{index}] primary_or_secondary is invalid")
    for claim_id, claim_entries in by_claim.items():
        verified = [item for item in claim_entries if item.get("fact_check_status") in {"VERIFIED", "PASS"}]
        primary = [item for item in verified if item.get("primary_or_secondary") == "primary"]
        publishers = {str(item.get("publisher_or_author")).strip().lower() for item in verified if _text(item.get("publisher_or_author"))}
        corroboration = [item for item in verified if _text(item.get("corroboration_source"))]
        if not (primary and corroboration) and len(publishers) < 2:
            failures.append(f"claim:{claim_id} requires primary+corroboration or two independent reliable sources")
        if primary and corroboration and len(verified) < 2:
            failures.append(f"claim:{claim_id} declares corroboration without a second verified ledger entry")
    return _status("source_ledger", not failures, failures, warnings)

def validate_rights_ledger(record: Mapping[str, Any]) -> dict[str, Any]:
    entries = record.get("rights_ledger")
    failures: list[str] = []
    warnings: list[str] = []
    if not isinstance(entries, list) or not entries:
        return _status("rights_ledger", False, ["rights_ledger is absent or empty"], warnings)
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            failures.append(f"entry[{index}] is not an object")
            continue
        required = ("asset_id", "source_url", "provider", "author", "license_name", "commercial_use", "platform_scope", "download_date", "license_evidence", "sha256", "perceptual_fingerprint", "incident_id", "used_by", "rights_status", "approved_for_render")
        failures.extend(f"entry[{index}] missing:{field}" for field in required if entry.get(field) in (None, "", []))
        if entry.get("commercial_use") is not True:
            failures.append(f"entry[{index}] commercial_use must be true")
        if not SHA256.fullmatch(str(entry.get("sha256", ""))):
            failures.append(f"entry[{index}] sha256 is not a valid SHA-256")
        if str(entry.get("perceptual_fingerprint", "")).lower() == str(entry.get("sha256", "")).lower():
            failures.append(f"entry[{index}] perceptual fingerprint copies SHA-256")
        if entry.get("rights_status") != "APPROVED" or entry.get("approved_for_render") is not True:
            failures.append(f"entry[{index}] is not independently approved for render")
        scope = entry.get("platform_scope")
        if not isinstance(scope, list) or not {"youtube_shorts", "tiktok"}.issubset(set(scope)):
            failures.append(f"entry[{index}] must declare both platform scopes explicitly")
    return _status("rights_ledger", not failures, failures, warnings)

def _normal_url(value: Any) -> str:
    return str(value or "").strip().lower().rstrip("/")

def _normal_record(item: Mapping[str, Any]) -> dict[str, Any]:
    source_url = item.get("source_url") or item.get("canonical_source_url") or item.get("source_page_url")
    perceptual = item.get("perceptual_fingerprint") or item.get("perceptual_hash")
    used_by = item.get("used_by") or item.get("first_used_video_id")
    if isinstance(used_by, str):
        used_by = [used_by]
    return {"asset_id": item.get("asset_id"), "sha256": item.get("sha256"), "source_url": source_url, "provider": item.get("provider"), "source_id": item.get("source_id") or item.get("provider_asset_id") or item.get("source_asset_key"), "perceptual_fingerprint": perceptual, "incident_id": item.get("incident_id"), "story_id": item.get("story_id"), "used_by": used_by or [], "rejected_by": item.get("rejected_by") or [], "derived_from": item.get("derived_from")}

def _validate_registry_completeness(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        raise RegistryError("global asset registry must be a JSON object")
    if not value.get("schema_version"):
        raise RegistryError("global asset registry schema_version is missing")
    assets = value.get("assets")
    if not isinstance(assets, list) or not assets:
        raise RegistryError("global asset registry is absent or empty")
    required_keys = ("asset_id", "provider", "provider_asset_id", "canonical_source_url", "sha256", "perceptual_hash")
    normalized: list[Mapping[str, Any]] = []
    for index, item in enumerate(assets):
        if not isinstance(item, Mapping):
            raise RegistryError(f"global asset registry entry[{index}] is not an object")
        missing = [key for key in required_keys if key not in item]
        if missing:
            raise RegistryError(f"global asset registry entry[{index}] missing fields:{','.join(missing)}")
        if not _text(item.get("asset_id")) or not _text(item.get("provider_asset_id")):
            raise RegistryError(f"global asset registry entry[{index}] has an empty identity")
        if not SHA256.fullmatch(str(item.get("sha256", ""))):
            raise RegistryError(f"global asset registry entry[{index}] has invalid sha256")
        if not _text(item.get("perceptual_hash")):
            raise RegistryError(f"global asset registry entry[{index}] lacks an independent perceptual_hash")
        normalized.append(_normal_record(item))
    return normalized

def load_registry(path: Path | None) -> list[Mapping[str, Any]]:
    if path is None:
        raise RegistryError("global asset registry path is required")
    if not path.exists():
        raise RegistryError(f"global asset registry does not exist:{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"global asset registry cannot be read:{path}") from exc
    return _validate_registry_completeness(value)

def validate_no_reuse(record: Mapping[str, Any], registry: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    current = record.get("rights_ledger") or []
    failures: list[str] = []
    warnings: list[str] = []
    history = [_normal_record(item) for item in (registry or []) if isinstance(item, Mapping)]
    if not history:
        failures.append("global asset registry is absent, empty or not proven complete")
    seen_current: dict[str, str] = {}
    for item in current:
        if not isinstance(item, Mapping):
            failures.append("current rights ledger contains a non-object entry")
            continue
        normalized = _normal_record(item)
        asset_id = str(normalized.get("asset_id") or "")
        sha = str(normalized.get("sha256") or "").lower()
        url = _normal_url(normalized.get("source_url"))
        source_id = str(normalized.get("source_id") or "").lower()
        perceptual = str(normalized.get("perceptual_fingerprint") or "").lower()
        incident_id = str(normalized.get("incident_id") or "")
        story_id = str(normalized.get("story_id") or "")
        for key, value in (("asset_id", asset_id), ("sha256", sha), ("source_url", url), ("source_id", source_id), ("perceptual_fingerprint", perceptual)):
            if not value:
                continue
            previous = seen_current.get(f"{key}:{value}")
            if previous and previous != asset_id:
                failures.append(f"current collision:{key}:{value}")
            seen_current[f"{key}:{value}"] = asset_id
        for prior in history:
            if prior.get("asset_id") == asset_id:
                failures.append(f"historical asset_id collision:{asset_id}")
            if sha and str(prior.get("sha256") or "").lower() == sha:
                failures.append(f"historical sha256 collision:{asset_id}")
            if url and _normal_url(prior.get("source_url")) == url:
                failures.append(f"historical source_url collision:{asset_id}")
            if source_id and str(prior.get("source_id") or "").lower() == source_id:
                failures.append(f"historical source_id collision:{asset_id}")
            if perceptual and str(prior.get("perceptual_fingerprint") or "").lower() == perceptual:
                failures.append(f"historical perceptual collision:{asset_id}")
            if incident_id and prior.get("incident_id") == incident_id:
                failures.append(f"incident_id already used:{incident_id}")
            if story_id and prior.get("story_id") == story_id:
                failures.append(f"story_id already used:{story_id}")
            if prior.get("derived_from") and prior.get("derived_from") == asset_id:
                failures.append(f"asset is derived from historical asset:{asset_id}")
    return _status("global_no_reuse", not failures, failures, warnings)
