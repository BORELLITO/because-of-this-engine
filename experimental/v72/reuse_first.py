#!/usr/bin/env python3
"""REUSE-FIRST: read-only, fail-closed inventory and rework decision engine.

No TTS, network calls, Drive writes, downloads, rendering or publishing.
Git blob hashes pin immutable ORIGINAL input bytes. Remote Drive metadata is a
recovery candidate only; media must be downloaded, hashed and QA-checked before
being passed to production. The same source footage cannot be reused in a new
episode: this catalog is exclusively for the original episode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class ReuseFirstError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan(manifest_path: Path, script_path: Path, catalog_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise ReuseFirstError("Unsupported immutable preview catalog")
    video_id = str(manifest.get("video_id") or "")
    original_id = str(catalog.get("episode_id") or "")
    if not original_id or video_id != original_id:
        raise ReuseFirstError("Cross-episode reuse is forbidden; source clips remain locked")
    if catalog.get("reference_state") != "DRAFT_PREVIEW_ONLY":
        raise ReuseFirstError("Only the recorded draft preview may be indexed")
    raw_manifest = manifest_path.read_bytes()
    raw_script = script_path.read_bytes()
    manifest_match = git_blob_sha(raw_manifest) == catalog.get("original_manifest_git_blob_sha")
    script_match = git_blob_sha(raw_script) == catalog.get("original_script_git_blob_sha")
    artifacts = catalog.get("artifacts") or []
    if not isinstance(artifacts, list):
        raise ReuseFirstError("Catalog artifacts must be a list")
    found = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ReuseFirstError("Invalid artifact")
        kind = artifact.get("kind")
        if not kind or kind in found:
            raise ReuseFirstError("Artifact kinds must be unique")
        found.add(kind)
        if (not str(artifact.get("drive_file_id") or "").strip()
            or not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0
            or not isinstance(artifact.get("md5"), str) or len(artifact["md5"]) != 32):
            raise ReuseFirstError("Incomplete Drive receipt metadata")
    necessary = {"preview_mp4", "narration_wav", "preview_manifest", "caption_quality_report",
                 "narration_coverage_report", "technical_release_report", "visual_story_report",
                 "golden_layout_report", "v7_gates_report"}
    if not necessary.issubset(found):
        raise ReuseFirstError("An expected delivered preview evidence file is absent")
    same_input = manifest_match and script_match
    stages = {
        "narration": "REMOTE_CANDIDATE_REQUIRE_SHA_AND_QA" if same_input else "INVALIDATE_AND_REASSESS",
        "caption_alignment": "MISSING_DELIVERED_ASS_ALIGNMENT_REBUILD_IF_NEEDED",
        "visual_assets": "USE_EXISTING_DRIVE_ASSETS_SAME_EPISODE_ONLY",
        "render": "REMOTE_CANDIDATE_REQUIRE_SHA_AND_QA" if same_input else "INVALIDATE_AND_REASSESS",
        "publishing": "BLOCKED_HUMAN_APPROVAL_REQUIRED",
    }
    return {
        "status": "EXISTING_PREVIEW_FOUND_INPUTS_MATCH" if same_input else "INPUTS_CHANGED_REVIEW_REQUIRED",
        "source_run_id": catalog["run_id"],
        "source_commit": catalog["origin_commit"],
        "current_episode_id": video_id,
        "manifest_git_blob_match": manifest_match,
        "script_git_blob_match": script_match,
        "existing_drive_folder_id": catalog["drive_folder_id"],
        "existing_mp4_drive_file_id": next(a["drive_file_id"] for a in artifacts if a["kind"]=="preview_mp4"),
        "existing_wav_drive_file_id": next(a["drive_file_id"] for a in artifacts if a["kind"]=="narration_wav"),
        "artifacts_found": len(artifacts),
        "stages": stages,
        "rerender_requested": False,
        "tts_called": False,
        "files_downloaded": False,
        "drive_byte_hashes_verified_in_this_plan": False,
        "release_approved": False,
        "source_video_reuse_in_other_episodes_allowed": False,
        "next_action": "Review the existing Drive preview before considering any regeneration.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--script", required=True, type=Path)
    p.add_argument("--catalog", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    x = p.parse_args()
    try:
        result = plan(x.manifest, x.script, x.catalog)
        x.report.parent.mkdir(parents=True, exist_ok=True)
        x.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False))
        return 0 if result["status"]=="EXISTING_PREVIEW_FOUND_INPUTS_MATCH" else 1
    except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError,ReuseFirstError) as exc:
        print("REUSE_FIRST_BLOCKED: "+str(exc))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
