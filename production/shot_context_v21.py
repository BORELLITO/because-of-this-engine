"""V2.1 actual-shot safety gate and documentary attribution preflight.

Uses executable scene->asset assignments, never stale candidate.role fields.
Prepares external-credit requirements without claiming delivery, audio, render,
publication, source ownership, or human approval.
"""
from __future__ import annotations

import json
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from production.visual_rights_consistency_v21 import _read_json

NASA_ID = "nasa-svs-geos5-clouds-no-labels-4819"
NASA_PAGE = "https://svs.gsfc.nasa.gov/4819/"
NASA_CREDIT = "NASA Scientific Visualization Studio"
NASA_DISCLOSURE = "Illustrative GEOS-5 modeled cloud cover (2020); not 1983 Soviet satellite data."
RECONSTRUCTION_NOTE = "Illustrative reenactment/stock footage; not authentic 1983 incident footage."

def _ids(values: Any, field: str, label: str, failures: list[str]) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        failures.append(f"{label} must be an array")
        return {}
    out = {}
    for i, item in enumerate(values):
        if not isinstance(item, Mapping):
            failures.append(f"{label}[{i}] must be an object")
            continue
        ident = str(item.get(field) or "").strip()
        if not ident or ident in out:
            failures.append(f"{label}[{i}] missing or duplicate {field}")
        else:
            out[ident] = item
    return out

def inspect(record: Mapping[str, Any], manifest: Mapping[str, Any],
            evidence: Mapping[str, Any] | None,
            delivery: Mapping[str, Any] | None) -> dict[str, Any]:
    failures: list[str] = []
    notices: list[str] = []
    assets = _ids(manifest.get("assets"),"candidate_id","assets",failures)
    shots = _ids(manifest.get("shot_assignments"),"shot_id","shot_assignments",failures)
    rights = _ids(record.get("rights_ledger"),"asset_id","rights_ledger",failures)
    review = _ids((evidence or {}).get("reviewed_assets",[]),"asset_id","reviewed_assets",failures)
    assigned: dict[str, str] = {}
    for shot_id, shot in shots.items():
        assignment = shot.get("assignment")
        asset_id = str(assignment.get("candidate_id") or "").strip() if isinstance(assignment,Mapping) else ""
        if not asset_id or asset_id not in assets:
            failures.append(f"{shot_id}: selected source not in active visual assets")
        else:
            assigned[shot_id] = asset_id
    if len(assigned)!=len(assets) or set(assigned.values())!=set(assets):
        failures.append("scene assignments must match selected asset identities exactly")
    if len(set(assigned.values()))!=len(assigned):
        failures.append("scene asset must not be reused without explicit policy")

    # The earlier visual plan contained stale source_role references. Never
    # assume a clip is shown in S03 merely because its plan role says S03.
    actual: dict[str, list[str]]={}
    for shot, asset_id in assigned.items():
        actual.setdefault(asset_id,[]).append(shot)

    risk_shots: list[dict[str, Any]]=[]
    for asset_id, uses in sorted(actual.items()):
        asset = assets[asset_id]
        item = review.get(asset_id)
        right = rights.get(asset_id)
        source_role = str(asset.get("source_role") or "")
        if source_role and source_role.upper() not in uses and "," not in source_role:
            notices.append(f"{asset_id}: source_role {source_role} != actual assignment {','.join(uses)}")
        if item and item.get("visual_person_class") == "identifiable":
            failures.append(f"{asset_id}: identifiable actor at actual scene {','.join(uses)}; do not misrepresent as historical person")
            risk_shots.append({"source":asset_id,"actual_shots":uses,"risk":"IDENTIFIABLE_REENACTMENT_ACTOR","status":"BLOCKED"})
        if not right:
            failures.append(f"{asset_id}: no rights record for actual shot {','.join(uses)}")
        elif right.get("approved_for_render") is not True:
            failures.append(f"{asset_id}: selected shot {','.join(uses)} has no scoped render authorization")
        if item and item.get("editorial_truth_class") == "REPRESENTATIONAL":
            notices.append(f"{asset_id}: stock footage is illustrative, not authentic archival material")

    actual_nasa_shots=actual.get(NASA_ID,[])
    if actual_nasa_shots:
        if not delivery:
            failures.append("NASA S12: delivery metadata with attribution and factual labeling not generated")
        else:
            details=delivery.get("nasa_svs_4819")
            if not isinstance(details,Mapping):
                failures.append("NASA S12: specific source metadata absent")
            else:
                if details.get("source_url")!=NASA_PAGE or details.get("credit")!=NASA_CREDIT:
                    failures.append("NASA S12: source URL or NASA SVS attribution incorrect")
                if details.get("disclosure")!=NASA_DISCLOSURE:
                    failures.append("NASA S12: modeled 2020 vs archival 1983 disclosure missing")
                if details.get("mode")!="ILLUSTRATIVE_NON_ARCHIVAL":
                    failures.append("NASA S12: truth class must not claim archival sensor footage")
                if details.get("ready_for_publication") is not False:
                    failures.append("NASA S12: unsigned sidecar cannot authorize publication")
                if details.get("delivery_verified") is not True:
                    failures.append("NASA S12: draft credit has not been verified in rendered/on-platform delivery")
        risk_shots.append({"source":NASA_ID,"actual_shots":actual_nasa_shots,
                           "risk":"2020_GEOS5_MODEL_NOT_1983_SENSOR","status":"BLOCKED_UNTIL_DELIVERY_EVIDENCE"})
    return {
        "gate":"SHOT_CONTEXT_V21",
        "status":"PASS" if not failures else "BLOCKED",
        "failures":failures,"notices":notices,
        "actual_assignments":assigned,
        "risk_shots":risk_shots,
        "render":"NOT_RUN","publication":"NOT_RUN"
    }

def inspect_repository(record:Mapping[str,Any],*,repo_root:Path)->dict[str,Any]:
    try:
        scene=_read_json(repo_root,str(record.get("visual_manifest_reference") or ""))
        ep=record.get("autonomous_rights_evidence_path")
        reviews=_read_json(repo_root,str(ep)) if ep else None
        delivery_path=record.get("delivery_credits_manifest_path")
        delivery=_read_json(repo_root,str(delivery_path)) if delivery_path else None
        result=inspect(record,scene,reviews,delivery)
        # An editable JSON boolean is NEVER sufficient to prove that a NASA
        # disclosure actually reached the final encoded video and description.
        # Require a real local output with an exact hash, source attribution
        # description file, and independent frame-level verification report.
        # These files intentionally do not exist while production is disabled.
        nasa = (delivery or {}).get("nasa_svs_4819",{})
        if isinstance(nasa,Mapping) and nasa.get("delivery_verified") is True:
            failures=result["failures"]
            media_rel=nasa.get("final_video_path")
            digest=str(nasa.get("final_video_sha256") or "")
            description_rel=nasa.get("final_description_path")
            receipt_rel=nasa.get("visual_credit_qa_receipt_path")
            if (not isinstance(media_rel,str) or not isinstance(description_rel,str)
                    or not isinstance(receipt_rel,str) or len(digest)!=64):
                failures.append("NASA S12: delivery proof missing source media, description, verified frame receipt or SHA-256")
            else:
                try:
                    root=repo_root.resolve()
                    def checked_file(value:str)->Path:
                        p=(root/value).resolve()
                        p.relative_to(root)
                        if not p.is_file():
                            raise ValueError("file not found")
                        return p
                    video=checked_file(media_rel)
                    desc=checked_file(description_rel)
                    receipt=checked_file(receipt_rel)
                    video_digest=hashlib.sha256(video.read_bytes()).hexdigest()
                    if video_digest!=digest:
                        failures.append("NASA S12: final media hash not verified")
                    description=desc.read_text(encoding="utf-8")
                    if NASA_CREDIT not in description or NASA_DISCLOSURE not in description:
                        failures.append("NASA S12: actual delivery description lacks source credit or model disclaimer")
                    proof=json.loads(receipt.read_text(encoding="utf-8"))
                    if (proof.get("final_video_sha256")!=digest
                            or proof.get("nasa_credit_onscreen_verified") is not True
                            or proof.get("nasa_disclosure_onscreen_verified") is not True
                            or proof.get("inspection_method")!="FRAME_LEVEL_FINISHED_RENDER"
                            or proof.get("frame_count_inspected",0)<1):
                        failures.append("NASA S12: independent final-frame inspection evidence missing")
                except (ValueError,OSError,TypeError,UnicodeDecodeError,json.JSONDecodeError) as exc:
                    failures.append(f"NASA S12: final delivered artifact verification failed: {exc}")
            result["status"]="BLOCKED" if failures else "PASS"
        return result
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError) as exc:
        return {"gate":"SHOT_CONTEXT_V21","status":"BLOCKED","failures":[f"unavailable scene or delivery evidence:{exc}"],
                "actual_assignments":{},"risk_shots":[],"render":"NOT_RUN","publication":"NOT_RUN"}
