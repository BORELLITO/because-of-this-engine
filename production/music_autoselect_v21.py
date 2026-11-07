"""V2.1 autonomous *per-story* background music decision, fail-closed.

The engine, not the user, selects from independently ingested candidate
recordings. A third-party web claim, "royalty-free" label, hash or metadata
checkbox is never a blanket permission. Every candidate needs a source file,
scoped rights dossier, listening/content observations and anti-reuse proof.

This module DOES NOT scrape, download, pay for, compose, render or publish music.
An acquisition/review stage must supply verifiable candidates first.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from production.audio_candidate_gate_v21 import check_file
from production.audio_mix_receipt_v21 import file_sha256

SHA = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_LICENSE = {
    "mixkit": ("mixkit.co", "https://mixkit.co/license/modal/musicFree/"),
    "pixabay": ("pixabay.com", "https://pixabay.com/service/terms/"),
}
BANNED_TAGS = {
    "siren", "sirene", "alarm", "alarme", "police_siren", "air_raid",
    "horn", "buzzer", "klaxon", "vocal", "vocals", "lyrics",
    "jump_scare", "jumpscare", "loud_stinger", "trailer_boom",
}
PREFERRED_TEXTURES = {"dark_ambient", "low_drone", "subtle_pulse",
                      "psychological_suspense", "cinematic_tension"}
MAX_GAIN = 0.12


class MusicSelectionError(RuntimeError):
    pass


def _official(url: Any, hostname: str) -> bool:
    try:
        parsed = urlparse(str(url))
        return parsed.scheme == "https" and (
            parsed.hostname == hostname or parsed.hostname == "www." + hostname)
    except (TypeError, ValueError):
        return False


def _evidence(candidate: dict[str, Any], file_sha: str, episode_id: str) -> list[str]:
    errors: list[str] = []
    provider = str(candidate.get("provider") or "").lower()
    if provider not in ALLOWED_LICENSE:
        return ["unrecognized provider or license class"]
    host, terms = ALLOWED_LICENSE[provider]
    if not _official(candidate.get("source_item_url"), host):
        errors.append("missing official item-specific source URL")
    document = candidate.get("rights_evidence_path")
    if not document:
        return errors + ["item-specific archived license evidence missing"]
    path = Path(str(document))
    try:
        if (not path.is_file() or
                file_sha256(path) != candidate.get("rights_evidence_sha256")):
            raise MusicSelectionError("rights evidence file missing or altered")
        e = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(e, dict):
            raise MusicSelectionError("rights evidence is not an object")
        if (e.get("item_url") != candidate.get("source_item_url")
                or e.get("source_sha256") != file_sha
                or e.get("provider") != provider
                or e.get("license_terms_url") != terms):
            errors.append("license evidence does not identify exact item/file/provider")
        if e.get("rights_reviewer") != "MOTOR_V21_SOURCE_REVIEW":
            errors.append("independent licensing review provenance missing")
        if (e.get("commercial_video_use") is not True or
                not {"youtube_shorts", "tiktok"}.issubset(set(e.get("platform_scope") or []))
                or e.get("standalone_distribution") is not False):
            errors.append("commercial video platform/license scope unverified")
        if (e.get("third_party_rights") != "CLEARED_FOR_THIS_EDITORIAL_USAGE"
                or e.get("content_id_review") not in {"NO_KNOWN_MATCH", "CLAIM_RESOLUTION_DOCUMENTED"}):
            errors.append("third-party or Content ID risk unresolved")
        if (e.get("episode_id") != episode_id or
                e.get("usage_scope") != "BACKGROUND_MUSIC_IN_EPISODE_ONLY"):
            errors.append("episode-specific audio rights scope missing")
        if not e.get("license_checked_on") or not e.get("rights_evidence_refs"):
            errors.append("dated independent license/source evidence missing")
    except (OSError, ValueError, TypeError, json.JSONDecodeError, MusicSelectionError) as exc:
        errors.append("rights evidence unreadable: " + str(exc))
    return errors


def evaluate_one(
    candidate: dict[str, Any],
    story: dict[str, Any],
    *,
    episode_id: str,
    total_seconds: float,
    repo_root: Path,
) -> dict[str, Any]:
    reasons: list[str] = []
    candidate_id = str(candidate.get("candidate_id") or "")
    path = Path(str(candidate.get("local_audio_path") or "/missing"))
    if not path.is_file():
        return {"candidate_id": candidate_id, "status": "BLOCKED",
                "reasons": ["original candidate audio unavailable"], "score": 0}
    digest = file_sha256(path)
    if not SHA.fullmatch(str(candidate.get("sha256") or "")) or candidate.get("sha256") != digest:
        reasons.append("original candidate SHA-256 mismatch")
    if candidate.get("kind") != "music_bed":
        reasons.append("candidate is not background music")
    if candidate.get("episode_id") != episode_id:
        reasons.append("candidate episode mismatch")
    if str(candidate.get("title") or "").strip() == "" or not candidate.get("artist"):
        reasons.append("source title/creator missing")
    tags = {str(t).strip().lower() for t in candidate.get("tags", [])}
    if tags & BANNED_TAGS:
        reasons.append("siren/alarm/vocal/jumpscare texture prohibited")
    qa = candidate.get("content_qa") or {}
    if (qa.get("method") != "MULTI_SEGMENT_SOURCE_LISTENING_AND_SPECTRAL_REVIEW"
            or qa.get("result") != "PASS"
            or qa.get("siren_or_alarm") is not False
            or qa.get("lead_vocals") is not False
            or qa.get("start_audible") is not True
            or qa.get("speech_masking_risk") != "LOW"
            or qa.get("abrupt_stinger") is not False):
        reasons.append("music intelligibility/no-siren QA not independently recorded")
    if candidate.get("source_duration_seconds", 0) < total_seconds + 0.03:
        reasons.append("song too short: no looping or stretched audio permitted")
    reasons += _evidence(candidate, digest, episode_id)
    # Run real source identity, ffprobe, Chromaprint and prior-use checks.
    acoustic = check_file(path, candidate, root=repo_root)
    if acoustic.get("status") != "PASS":
        reasons.append("known music reuse or source audit blocked: "
                       + "; ".join(acoustic.get("failures") or ["unknown"]))
    arc = str(story.get("tension_arc") or "")
    if arc not in {"slow_burn", "steady_dread", "investigation", "escalation"}:
        reasons.append("episode's emotional trajectory is not defined")
    matching = tags & {str(t).lower() for t in story.get("mood_tags", [])}
    score = (len(matching) * 12
             + len(tags & PREFERRED_TEXTURES) * 5
             + (16 if qa.get("speech_masking_risk") == "LOW" else 0)
             + (10 if candidate.get("arc_fit") == arc else 0)
             + (5 if candidate.get("source_duration_seconds", 0) >= total_seconds + 8 else 0))
    if not matching:
        reasons.append("track does not fit documented story mood")
    return {"candidate_id": candidate_id, "status": "BLOCKED" if reasons else "ELIGIBLE",
            "score": score, "reasons": reasons,
            "original_audio_sha256": digest, "audio_path": str(path),
            "rights_evidence_sha256": candidate.get("rights_evidence_sha256"),
            "licensing_scope": "SINGLE_EPISODE_BACKGROUND_YOUTUBE_TIKTOK_ONLY",
            "publication_authorized": False}


def select_for_story(
    pool: dict[str, Any], *, repo_root: Path, total_seconds: float,
) -> dict[str, Any]:
    episode_id = str(pool.get("episode_id") or "")
    story = pool.get("story") or {}
    candidates = pool.get("candidates") or []
    if (not episode_id or not isinstance(story, dict) or
            not isinstance(candidates, list) or not candidates):
        return {"status": "BLOCKED", "reason": "episode/mood/candidate pool missing",
                "selected": None, "decisions": []}
    ids = [str(c.get("candidate_id") or "") for c in candidates]
    if len(set(ids)) != len(ids) or any(not key for key in ids):
        return {"status": "BLOCKED", "reason": "duplicate/empty music identities",
                "selected": None, "decisions": []}
    decisions = [evaluate_one(c, story, episode_id=episode_id,
                              total_seconds=total_seconds, repo_root=repo_root)
                 for c in candidates]
    eligible = [x for x in decisions if x["status"] == "ELIGIBLE"]
    eligible.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    best = eligible[0] if eligible else None
    return {
        "status": "AUTO_SELECTED_EVIDENCE_BOUND_V21" if best else "BLOCKED",
        "episode_id": episode_id,
        "selected": best,
        "decisions": decisions,
        "confidence_scope": "AUTO_RANKING_INSPECTED_LICENSED_AUDIO_NOT_WORLDWIDE_COPYRIGHT",
        "soundtrack_required": True,
        "music_through_end_card": True,
        "no_sirens": True,
        "publication_authorized": False,
        "note": "If no track survives, fail closed and acquire more source evidence; do not substitute silence.",
    }


def select_from_file(pool_path: Path, *, repo_root: Path,
                     total_seconds: float) -> dict[str, Any]:
    try:
        pool = json.loads(pool_path.read_text(encoding="utf-8"))
        return select_for_story(pool, repo_root=repo_root,
                                total_seconds=total_seconds)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED", "selected": None,
                "reason": "music pool unreadable: " + str(exc),
                "publication_authorized": False}
