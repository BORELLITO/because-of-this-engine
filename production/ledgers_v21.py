"""Source, rights and global no-reuse contracts for V2.1."""
from __future__ import annotations
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
def _text(value: Any) -> bool: return isinstance(value, str) and bool(value.strip())
def _status(name: str, passed: bool, failures: list[str], warnings: list[str]) -> dict[str, Any]:
    return {"ledger":name,"status":"PASS" if passed else "BLOCKED","failures":failures,"warnings":warnings}

def validate_source_ledger(record: Mapping[str, Any]) -> dict[str, Any]:
    entries = record.get("source_ledger"); failures: list[str] = []; warnings: list[str] = []
    if not isinstance(entries, list) or not entries: return _status("source_ledger",False,["source_ledger is absent or empty"],warnings)
    by_claim: dict[str,list[Mapping[str,Any]]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping): failures.append(f"entry[{index}] is not an object"); continue
        claim_id = entry.get("claim_id"); by_claim.setdefault(str(claim_id),[]).append(entry)
        required = ("claim_id","claim_text","source_url","source_type","publisher_or_author","publication_date","primary_or_secondary","reliability_notes","accessed_at","evidence_excerpt_or_note","fact_check_status")
        failures.extend(f"entry[{index}] missing:{field}" for field in required if not _text(entry.get(field)))
        if entry.get("fact_check_status") not in {"VERIFIED","PASS"}: failures.append(f"entry[{index}] fact_check_status is not verified")
    for claim_id, claim_entries in by_claim.items():
        verified = [x for x in claim_entries if x.get("fact_check_status") in {"VERIFIED","PASS"}]
        primary = [x for x in verified if x.get("primary_or_secondary") == "primary"]
        publishers = {str(x.get("publisher_or_author")).strip().lower() for x in verified if _text(x.get("publisher_or_author"))}
        corroboration = any(_text(x.get("corroboration_source")) for x in verified)
        if not (primary and corroboration) and len(publishers) < 2:
            failures.append(f"claim:{claim_id} requires primary+corroboration or two independent reliable sources")
    return _status("source_ledger",not failures,failures,warnings)

def validate_rights_ledger(record: Mapping[str, Any]) -> dict[str, Any]:
    entries = record.get("rights_ledger"); failures: list[str] = []; warnings: list[str] = []
    if not isinstance(entries, list) or not entries: return _status("rights_ledger",False,["rights_ledger is absent or empty"],warnings)
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping): failures.append(f"entry[{index}] is not an object"); continue
        required = ("asset_id","source_url","provider","author","license_name","commercial_use","platform_scope","download_date","license_evidence","sha256","perceptual_fingerprint","incident_id","used_by","rights_status","approved_for_render")
        failures.extend(f"entry[{index}] missing:{field}" for field in required if entry.get(field) in (None,"",[]))
        if not SHA256.fullmatch(str(entry.get("sha256",""))): failures.append(f"entry[{index}] sha256 is not a valid SHA-256")
        if str(entry.get("perceptual_fingerprint","")).lower() == str(entry.get("sha256","")).lower(): failures.append(f"entry[{index}] perceptual fingerprint copies SHA-256")
        if entry.get("rights_status") != "APPROVED" or entry.get("approved_for_render") is not True: failures.append(f"entry[{index}] is not independently approved for render")
        scope = entry.get("platform_scope")
        if not isinstance(scope,list) or not {"youtube_shorts","tiktok"}.issubset(set(scope)): failures.append(f"entry[{index}] must declare both platform scopes explicitly")
    return _status("rights_ledger",not failures,failures,warnings)

def _normal_url(value: Any) -> str: return str(value or "").strip().lower().rstrip("/")
def validate_no_reuse(record: Mapping[str, Any], registry: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    current = record.get("rights_ledger") or []; failures: list[str] = []; warnings: list[str] = []
    history = [item for item in registry if isinstance(item, Mapping)]; seen_current: dict[str,str] = {}
    for item in current:
        asset_id = str(item.get("asset_id","")); sha = str(item.get("sha256","")).lower(); url = _normal_url(item.get("source_url")); perceptual = str(item.get("perceptual_fingerprint","")).lower(); incident_id = str(item.get("incident_id",""))
        for key, value in (("asset_id",asset_id),("sha256",sha),("source_url",url),("perceptual_fingerprint",perceptual)):
            if not value: continue
            previous = seen_current.get(key+":"+value)
            if previous and previous != asset_id: failures.append(f"current collision:{key}:{value}")
            seen_current[key+":"+value] = asset_id
        for prior in history:
            if prior.get("asset_id") == asset_id: failures.append(f"historical asset_id collision:{asset_id}")
            if sha and str(prior.get("sha256","")).lower() == sha: failures.append(f"historical sha256 collision:{asset_id}")
            if url and _normal_url(prior.get("source_url")) == url: failures.append(f"historical source_url collision:{asset_id}")
            if perceptual and str(prior.get("perceptual_fingerprint","")).lower() == perceptual: failures.append(f"historical perceptual collision:{asset_id}")
            if incident_id and prior.get("incident_id") == incident_id: failures.append(f"incident_id already used:{incident_id}")
            if prior.get("derived_from") and prior.get("derived_from") == asset_id: failures.append(f"asset is derived from historical asset:{asset_id}")
    return _status("global_no_reuse",not failures,failures,warnings)

def load_registry(path: Path | None) -> list[Mapping[str,Any]]:
    if path is None or not path.exists(): return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, Mapping): value = value.get("assets",[])
    return value if isinstance(value,list) else []
