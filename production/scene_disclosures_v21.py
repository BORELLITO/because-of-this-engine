"""Mandatory nonfiction labels for exact sourced S01 actor and S12 NASA shot.

The gate validates bounded sample-receipts and complete future description copy.
It DOES NOT certify a finished composed video or permit publication.
Only known literal text is inserted into FFmpeg, never data-driven filter strings.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from production.visual_rights_consistency_v21 import _read_json

NASA_ID = "nasa-svs-geos5-clouds-no-labels-4819"
NASA_SHOT = "S12"
NASA_URL = "https://svs.gsfc.nasa.gov/4819/"
NASA_SHA256 = "306a8c1b97ddb3699a84f3d35f6a0c9c3cbc593f13f9a35aef13d72a55f323d0"
NASA_LINE1 = "NASA GEOS-5 MODEL (2020)"
NASA_LINE2 = "Illustration - NOT 1983 sensor footage"
NASA_SAMPLE_SHA256 = "6ca0255fa7a447052a84d9cad403d351de2f815e88e715f68b4a68804ba0d4bc"
NASA_FRAME_SHA256 = "51bf6cd9c08061f4143a1801f70fd5bd4b724c6a46bde5a92b5ebf0522cb1fd1"

ACTOR_ID = "pexels-11764431"
ACTOR_SHOT = "S01"
ACTOR_URL = "https://www.pexels.com/video/man-using-walkie-talkie-in-bunker-11764431/"
ACTOR_SHA256 = "9e2ad3951cafda341e656c9be49ffc55915326b0789e243e65aad65df1408f7b"
ACTOR_LINE = "DRAMATIZATION - NOT ARCHIVAL FOOTAGE"
ACTOR_SAMPLE_SHA256 = "c7a4a30bf8f108363759534598b9a4cddb79a5cc024a0caa3eab86721e47bbf7"
ACTOR_FRAME_SHA256 = "9d532e650e157818b7628225f93ff485033d3747c74c7631dbfed6f0fa9e803b"

SCENE_CONTRACT = "scene-disclosures-v21.json"
SCENE_PATH = "episodes/episode-005/visual/" + SCENE_CONTRACT
REQUIRED_CREDIT_NAMES = (
    "NASA's Scientific Visualization Studio", "Greg Shirah",
    "Trent L. Schindler", "Ryan Fitzgibbons",
)
SCENE_BINDINGS = {
    ACTOR_ID: (ACTOR_SHOT, ACTOR_SHA256, ACTOR_URL),
    NASA_ID: (NASA_SHOT, NASA_SHA256, NASA_URL),
}


def _items(scene: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    values = scene.get(key)
    if not isinstance(values, list):
        return []
    return [v for v in values if isinstance(v, Mapping)]


def _ids(scene: Mapping[str, Any]) -> set[str]:
    return {str(x.get("candidate_id")) for x in _items(scene, "assets")}


def _valid_overlay(overlay: Any, *, nasa: bool) -> bool:
    if not isinstance(overlay, Mapping):
        return False
    shared = (
        overlay.get("anchor") == "upper_mid_below_brand"
        and overlay.get("background_plate") is True
        and overlay.get("hold_full_scene") is True
        and overlay.get("y1") == 370
        and isinstance(overlay.get("minimum_font_px"), int)
        and overlay["minimum_font_px"] >= (31 if nasa else 29)
        and isinstance(overlay.get("max_text_width_px"), int)
        and overlay["max_text_width_px"] <= 970
    )
    if not shared:
        return False
    if nasa:
        return (
            overlay.get("line_1") == NASA_LINE1
            and overlay.get("line_2") == NASA_LINE2
            and overlay.get("y2") == 440
        )
    return overlay.get("line_1") == ACTOR_LINE and "line_2" not in overlay


def validate_disclosure(
    scene: Mapping[str, Any], contract: Mapping[str, Any],
) -> dict[str, Any]:
    problems: list[str] = []
    active = _ids(scene)
    needed = set(SCENE_BINDINGS) & active
    if not needed:
        return {
            "gate": "SCENE_DISCLOSURES_V21", "status": "PASS",
            "failures": [], "scope": "NO_SENSITIVE_DISCLOSURES",
            "final_video_verified": False,
        }
    if scene.get("episode_id") != "episode-005" or contract.get("episode_id") != scene.get("episode_id"):
        problems.append("scene and disclosure episode IDs do not match")
    if contract.get("production_enablement") is not False or contract.get("publication_policy") != "manual_only":
        problems.append("production disabled and manual publication must remain locked")
    entries = contract.get("disclosures")
    if not isinstance(entries, list) or any(not isinstance(x, Mapping) for x in entries):
        problems.append("disclosures must be a list of objects")
        entries = []
    by_asset: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        key = str(entry.get("asset_id") or "")
        if not key or key in by_asset:
            problems.append("duplicate or empty disclosure asset ID")
        else:
            by_asset[key] = entry
    if set(by_asset) != needed:
        problems.append("disclosure set must cover exactly the used sensitive source files")
    assets = _items(scene, "assets")
    shots = _items(scene, "shot_assignments")
    for asset_id in sorted(needed):
        expected_shot, expected_sha, expected_url = SCENE_BINDINGS[asset_id]
        item = by_asset.get(asset_id)
        if item is None:
            continue
        exact_assets = [a for a in assets if a.get("candidate_id") == asset_id]
        exact_shots = [
            s for s in shots if isinstance(s.get("assignment"), Mapping)
            and s["assignment"].get("candidate_id") == asset_id
        ]
        if (
            len(exact_assets) != 1 or len(exact_shots) != 1
            or exact_shots[0].get("shot_id") != expected_shot
        ):
            problems.append(f"{asset_id}: scene assignment must be exactly {expected_shot}")
        if (
            item.get("shot_id") != expected_shot or item.get("sha256") != expected_sha
            or item.get("source_url") != expected_url or not exact_assets
            or exact_assets[0].get("sha256") != expected_sha
            or exact_assets[0].get("source_page_url") != expected_url
        ):
            problems.append(f"{asset_id}: original media source or shot identity changed")
        if (
            item.get("source_audio_usage") != "STRIP"
            or item.get("needs_manual_publication_qa") is not True
            or item.get("overlay_renderer_required") is not True
            or item.get("label_visible_on_shot") is not True
            or set(item.get("platforms") or []) != {"youtube_shorts", "tiktok"}
        ):
            problems.append(f"{asset_id}: source audio / label / platform safety gate missing")
        if not _valid_overlay(item.get("overlay"), nasa=asset_id == NASA_ID):
            problems.append(f"{asset_id}: onscreen warning does not match locked readable safe area")
        footer = item.get("delivery_description_footer")
        if not isinstance(footer, str) or expected_url not in footer or len(footer) < 95:
            problems.append(f"{asset_id}: source attribution missing from platform description")
            footer = ""
        if item.get("overlay_render_sample_verified") is not True:
            problems.append(f"{asset_id}: no actual footage disclosure preview verified")
        if item.get("final_assembled_video_metadata_verified") is not False:
            problems.append(f"{asset_id}: cannot self-certify final assembled video")
        if item.get("final_publication_verified") is not False:
            problems.append(f"{asset_id}: publication has not occurred")
        if asset_id == NASA_ID:
            credit = item.get("credits")
            if not isinstance(credit, Mapping):
                problems.append("NASA: missing official SVS credits")
            elif (
                credit.get("primary") != REQUIRED_CREDIT_NAMES[0]
                or set(credit.get("visualizers") or []) != set(REQUIRED_CREDIT_NAMES[1:3])
                or credit.get("producer") != REQUIRED_CREDIT_NAMES[3]
            ):
                problems.append("NASA: official visualizers/producer names mismatch")
            if (
                item.get("scientific_truth_class") != "ILLUSTRATIVE_MODEL_NOT_ARCHIVAL"
                or item.get("not_actual_soviet_sensor_1983") is not True
                or item.get("source_release_date") != "2020-04-20"
                or item.get("no_nasa_endorsement") is not True
            ):
                problems.append("NASA: GEOS-5 model/1983 truth constraint missing")
            if (
                any(name not in footer for name in REQUIRED_CREDIT_NAMES)
                or "GEOS-5" not in footer
                or "2020" not in footer or "1983" not in footer
                or "NOT" not in footer or "does not endorse" not in footer
            ):
                problems.append("NASA: credits or truthful model nonendorsement missing from description")
            receipt = item.get("overlay_qa_receipt")
            if not isinstance(receipt, Mapping) or (
                receipt.get("sample_video_sha256") != NASA_SAMPLE_SHA256
                or receipt.get("sample_still_sha256") != NASA_FRAME_SHA256
                or receipt.get("source_sha256_verified") is not True
                or receipt.get("sample_review") != "PASS_LEGIBLE_MODEL_NOT_1983_NOTICE"
                or receipt.get("scope") != "QA_ONLY_NOT_FINAL_EPISODE"
            ):
                problems.append("NASA: real source frame sample hash/visual QA missing")
        else:
            if (
                item.get("provider") != "pexels"
                or item.get("source_creator") != "Said Gülüm"
                or item.get("not_actual_stanislav_petrov") is not True
                or item.get("not_archival_1983") is not True
                or item.get("no_actor_endorsement") is not True
                or item.get("original_source_truth") != "STOCK_ACTOR_NOT_HISTORICAL_PERSON"
            ):
                problems.append("S01: stock actor must never be attributed to Petrov")
            if "NOT Stanislav Petrov" not in footer or "NOT archival" not in footer:
                problems.append("S01: actor misrepresentation disclaimer missing in description")
            receipt = item.get("verification")
            if not isinstance(receipt, Mapping) or (
                receipt.get("source_footage_sha256") != ACTOR_SHA256
                or receipt.get("sample_video_sha256") != ACTOR_SAMPLE_SHA256
                or receipt.get("sample_still_sha256") != ACTOR_FRAME_SHA256
                or receipt.get("source_sha256_verified") is not True
                or receipt.get("sample_review") != "PASS_LABEL_VISIBLE_AND_FACE_STILL_IDENTIFIABLE_NOT_MASKED"
                or receipt.get("scope") != "QA_ONLY_NOT_FINAL_EPISODE"
            ):
                problems.append("S01: verified video source/frame/reenactment label proof missing")
    return {
        "gate": "SCENE_DISCLOSURES_V21",
        "status": "PASS" if not problems else "BLOCKED",
        "failures": problems,
        "scene_count": len(needed),
        "checked_shots": sorted(
            item.get("shot_id") for item in by_asset.values()
            if isinstance(item.get("shot_id"), str)
        ),
        "source_notice_prepared": not problems,
        "final_video_verified": False,
        "publication_authorized": False,
        "on_frame_sample_qa_pass": not problems,
        "description_footers": {
            key: by_asset[key].get("delivery_description_footer")
            for key in needed if key in by_asset
        } if not problems else {},
    }


def audit_repository(record: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    try:
        scene = _read_json(repo_root, str(record.get("visual_manifest_reference") or ""))
        if not (_ids(scene) & set(SCENE_BINDINGS)):
            return validate_disclosure(scene, {})
        if scene.get("scene_disclosure_contract") != SCENE_PATH:
            return {
                "gate": "SCENE_DISCLOSURES_V21", "status": "BLOCKED",
                "failures": ["missing canonical actor/NASA disclaimer contract"],
                "final_video_verified": False,
            }
        contract = _read_json(repo_root, SCENE_PATH)
        return validate_disclosure(scene, contract)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "gate": "SCENE_DISCLOSURES_V21", "status": "BLOCKED",
            "failures": [f"scene source disclaimer unreadable: {exc}"],
            "final_video_verified": False,
        }


def ffmpeg_nasa_overlay(item: Mapping[str, Any]) -> str:
    """No dynamic text interpolation into FFmpeg command: all tokens are frozen."""
    if not _valid_overlay(item.get("overlay"), nasa=True):
        raise ValueError("NASA source model disclaimer is not the locked contract")
    return (
        ",drawtext=font='DejaVu Sans':text='NASA GEOS-5 MODEL (2020)'"
        ":fontsize=38:fontcolor=white:box=1:boxcolor=black@0.73:boxborderw=12"
        ":x=(w-text_w)/2:y=370"
        ",drawtext=font='DejaVu Sans':text='Illustration - NOT 1983 sensor footage'"
        ":fontsize=31:fontcolor=white:box=1:boxcolor=black@0.73:boxborderw=12"
        ":x=(w-text_w)/2:y=440"
    )


def ffmpeg_actor_overlay(item: Mapping[str, Any]) -> str:
    """Truthful S01 reenactment label, below channel wordmark, for every frame."""
    if not _valid_overlay(item.get("overlay"), nasa=False):
        raise ValueError("S01 dramatization label is not the locked contract")
    return (
        ",drawtext=font='DejaVu Sans':text='DRAMATIZATION - NOT ARCHIVAL FOOTAGE'"
        ":fontsize=29:fontcolor=white:box=1:boxcolor=black@0.73:boxborderw=12"
        ":x=(w-text_w)/2:y=370"
    )


def load_for_preview(
    scene_manifest_path: Path, manifest: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    if not (_ids(manifest) & set(SCENE_BINDINGS)):
        return {}
    if manifest.get("scene_disclosure_contract") != SCENE_PATH:
        raise ValueError("Both model and reenactment truth warnings are mandatory")
    evidence_path = scene_manifest_path.parent / SCENE_CONTRACT
    contract = json.loads(evidence_path.read_text(encoding="utf-8"))
    checked = validate_disclosure(manifest, contract)
    if checked["status"] != "PASS":
        raise ValueError("Scene truth contract blocked: " + "; ".join(checked["failures"]))
    return {
        str(entry["asset_id"]): entry
        for entry in contract["disclosures"]
    }
