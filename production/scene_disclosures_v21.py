"""Exact-source scientific model disclosure contract for V2.1 footage.

Fail closed if a 2020 NASA GEOS-5 visualization is shown without an
on-screen model notice and platform description credits. Contract PASS means
delivery metadata has been PREPARED, not that a final video was rendered.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections.abc import Mapping
from typing import Any
from production.visual_rights_consistency_v21 import _read_json

NASA_ID="nasa-svs-geos5-clouds-no-labels-4819"
NASA_SHOT="S12"
NASA_URL="https://svs.gsfc.nasa.gov/4819/"
NASA_SHA256="306a8c1b97ddb3699a84f3d35f6a0c9c3cbc593f13f9a35aef13d72a55f323d0"
NASA_LINE1="NASA GEOS-5 MODEL (2020)"
NASA_LINE2="Illustration - NOT 1983 sensor footage"
SCENE_CONTRACT="scene-disclosures-v21.json"
REQUIRED_CREDIT_NAMES=("NASA's Scientific Visualization Studio","Greg Shirah","Trent L. Schindler","Ryan Fitzgibbons")

def _has_nasa(visual_manifest: Mapping[str,Any])->bool:
    return any(isinstance(x,Mapping) and x.get("candidate_id")==NASA_ID
               for x in visual_manifest.get("assets",[]))

def validate_disclosure(visual_manifest:Mapping[str,Any],contract:Mapping[str,Any])->dict[str,Any]:
    problems=[]
    if not _has_nasa(visual_manifest):
        return {"gate":"SCENE_DISCLOSURES_V21","status":"PASS",
                "failures":[],"scope":"NO_NASA_VISUAL","final_video_verified":False}
    if (contract.get("episode_id") != visual_manifest.get("episode_id")
            or contract.get("episode_id") != "episode-005"):
        problems.append("episode ID differs in scientific model disclosure")
    if contract.get("publication_policy")!="manual_only" or contract.get("production_enablement") is not False:
        problems.append("publication/production restrictions missing")
    all_items=contract.get("disclosures")
    if not isinstance(all_items,list) or len(all_items)!=1 or not isinstance(all_items[0],Mapping):
        problems.append("exactly one valid NASA disclosure required")
        return {"gate":"SCENE_DISCLOSURES_V21","status":"BLOCKED","failures":problems,
                "final_video_verified":False}
    item=all_items[0]
    assets=[a for a in visual_manifest.get("assets",[]) if isinstance(a,Mapping) and a.get("candidate_id")==NASA_ID]
    shots=[a for a in visual_manifest.get("shot_assignments",[]) if isinstance(a,Mapping) and (a.get("assignment") or {}).get("candidate_id")==NASA_ID]
    if len(assets)!=1 or len(shots)!=1 or shots[0].get("shot_id")!=NASA_SHOT:
        problems.append("NASA media must map to exactly the known S12 shot")
    if item.get("asset_id")!=NASA_ID or item.get("shot_id")!=NASA_SHOT:
        problems.append("NASA credit must bind exact visual identity")
    if item.get("sha256")!=NASA_SHA256 or not assets or assets[0].get("sha256")!=NASA_SHA256:
        problems.append("NASA credit source SHA-256 does not bind approved media")
    if item.get("source_url")!=NASA_URL or not assets or assets[0].get("source_page_url")!=NASA_URL:
        problems.append("NASA item URL not official or changed")
    if item.get("source_release_date")!="2020-04-20" or item.get("not_actual_soviet_sensor_1983") is not True:
        problems.append("GEOS-5 release year or model-vs-archive truth caveat absent")
    if item.get("scientific_truth_class")!="ILLUSTRATIVE_MODEL_NOT_ARCHIVAL":
        problems.append("NASA media falsely classified as literal historical evidence")
    if (item.get("source_audio_usage")!="STRIP"
            or item.get("no_nasa_endorsement") is not True
            or item.get("needs_manual_publication_qa") is not True):
        problems.append("NASA audio, nonendorsement or manual publishing gate absent")
    overlay=item.get("overlay")
    if not isinstance(overlay,Mapping):
        problems.append("on-screen disclosure absent")
    else:
        if (overlay.get("line_1")!=NASA_LINE1
                or overlay.get("line_2")!=NASA_LINE2
                or overlay.get("hold_full_scene") is not True
                or overlay.get("background_plate") is not True
                or overlay.get("anchor")!="upper_mid_below_brand"
                or int(overlay.get("minimum_font_px") or 0)<31
                or int(overlay.get("max_text_width_px") or 1100)>970
                or overlay.get("y1")!=370 or overlay.get("y2")!=440):
            problems.append("NASA fact notice does not meet locked readable safe-area")
    credit=item.get("credits")
    if not isinstance(credit,Mapping):
        problems.append("NASA credits object absent")
    elif (credit.get("primary")!=REQUIRED_CREDIT_NAMES[0]
          or set(credit.get("visualizers") or [])!={REQUIRED_CREDIT_NAMES[1],REQUIRED_CREDIT_NAMES[2]}
          or credit.get("producer")!=REQUIRED_CREDIT_NAMES[3]):
        problems.append("NASA official SVS artist/producer credit names incomplete")
    footer=item.get("delivery_description_footer")
    if not isinstance(footer,str) or any(x not in footer for x in REQUIRED_CREDIT_NAMES):
        problems.append("NASA credit footer not complete for platform descriptions")
    elif (("2020" not in footer or "1983" not in footer)
            or "NOT" not in footer or NASA_URL not in footer or "does not endorse" not in footer):
        problems.append("NASA footer must explicitly distinguish modeled 2020 from 1983 imagery")
    if set(item.get("platforms") or [])!={"youtube_shorts","tiktok"}:
        problems.append("both platform descriptions must include source credits")
    if item.get("overlay_renderer_required") is not True:
        problems.append("preview renderer must burn 2020 model disclosure")
    return {"gate":"SCENE_DISCLOSURES_V21",
            "status":"PASS" if not problems else "BLOCKED",
            "failures":problems,
            "source_notice_prepared":not problems,
            "final_video_verified":False,
            "publication_authorized":False,
            "requires_on_frame_sample_verification":True,
            "description_footer":footer if not problems else None}


def audit_repository(record:Mapping[str,Any],*,repo_root:Path)->dict[str,Any]:
    try:
        manifest=_read_json(repo_root,str(record.get("visual_manifest_reference") or ""))
        if not _has_nasa(manifest):
            return validate_disclosure(manifest,{})
        rel=manifest.get("scene_disclosure_contract")
        expected="episodes/episode-005/visual/"+SCENE_CONTRACT
        if rel!=expected:
            return {"gate":"SCENE_DISCLOSURES_V21","status":"BLOCKED",
                    "failures":["scene disclosure contract missing or wrong path"],"final_video_verified":False}
        contract=_read_json(repo_root,rel)
        return validate_disclosure(manifest,contract)
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
        return {"gate":"SCENE_DISCLOSURES_V21","status":"BLOCKED",
                "failures":[str(exc)],"final_video_verified":False}


def ffmpeg_nasa_overlay(item:Mapping[str,Any])->str:
    """Validated text only; no arbitrary user strings fed into FFmpeg filters."""
    p=item.get("overlay") if isinstance(item,Mapping) else None
    if (not isinstance(p,Mapping) or p.get("line_1")!=NASA_LINE1
        or p.get("line_2")!=NASA_LINE2 or p.get("y1")!=370 or p.get("y2")!=440):
        raise ValueError("NASA disclosure must be validated before overlay")
    return (
       ",drawtext=font='DejaVu Sans':text='NASA GEOS-5 MODEL (2020)'"
       ":fontsize=38:fontcolor=white:box=1:boxcolor=black@0.73:boxborderw=12"
       ":x=(w-text_w)/2:y=370"
       ",drawtext=font='DejaVu Sans':text='Illustration - NOT 1983 sensor footage'"
       ":fontsize=31:fontcolor=white:box=1:boxcolor=black@0.73:boxborderw=12"
       ":x=(w-text_w)/2:y=440"
    )


def load_for_preview(scene_manifest_path:Path,manifest:Mapping[str,Any])->dict[str,Mapping[str,Any]]:
    if not _has_nasa(manifest):
        return {}
    expected="episodes/episode-005/visual/"+SCENE_CONTRACT
    if manifest.get("scene_disclosure_contract")!=expected:
        raise ValueError("NASA disclosure path must be canonical")
    path=scene_manifest_path.parent/SCENE_CONTRACT
    data=json.loads(path.read_text(encoding="utf-8"))
    checked=validate_disclosure(manifest,data)
    if checked["status"]!="PASS":
        raise ValueError("NASA disclaimer contract blocked: "+",".join(checked["failures"]))
    return {NASA_ID:data["disclosures"][0]}
