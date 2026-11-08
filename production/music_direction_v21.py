"""The ONE canonical per-story suspense music selector for V2.1.

Makes a deterministic *editorial* choice from pre-ingested audio sources.
Tracks must carry independently recorded item-specific license and audio-QA
evidence tied to the original SHA256 and selected episode. Does not crawl,
download, publish, guarantee legal immunity or invent rights when absent.
Final render still independently checks actual audio + Chromaprint anti-reuse.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from production.audio_mix_receipt_v21 import file_sha256

FORBIDDEN = {"siren", "sirene", "alarm", "alarme", "emergency", "police",
             "air_raid", "horn", "klaxon", "loud_stinger", "explosion",
             "jump_scare", "jumpscare", "vocals", "lead_vocals", "lyrics"}
PREFERRED = {"dark_ambient", "psychological_suspense", "cinematic_drone",
             "minimal_tension", "investigative", "subtle_tension"}
STORY_WEIGHTS = {
    "historical_mystery": {"investigative": 5, "minimal_tension": 4, "cinematic_drone": 3},
    "psychological_horror": {"psychological_suspense": 6, "dark_ambient": 4},
    "human_tragedy": {"subtle_tension": 6, "minimal_tension": 5},
    "true_story": {"investigative": 5, "minimal_tension": 4},
    "supernatural": {"dark_ambient": 6, "cinematic_drone": 4},
}
OFFICIAL_RIGHTS = {
    "mixkit": ("mixkit.co", "https://mixkit.co/license/modal/musicFree/"),
    "pixabay": ("pixabay.com", "https://pixabay.com/service/terms/"),
}


def _on_provider(url: Any, provider: str) -> bool:
    parsed = urlparse(str(url or ""))
    host = parsed.hostname or ""
    return parsed.scheme == "https" and host in {
        OFFICIAL_RIGHTS[provider][0], "www." + OFFICIAL_RIGHTS[provider][0]
    }


def _check_source_rights(track: dict[str, Any], episode_id: str) -> list[str]:
    problems: list[str] = []
    provider = str(track.get("provider") or "").lower()
    if provider not in OFFICIAL_RIGHTS:
        return ["unrecognized music provider/rights license"]
    official_license = OFFICIAL_RIGHTS[provider][1]
    if (not _on_provider(track.get("source_url"), provider) or
            track.get("license_url") != official_license):
        problems.append("source item or official provider license URL invalid")
    source_path = Path(str(track.get("local_audio_path") or "/missing"))
    if not source_path.is_file():
        return problems + ["original licensed audio file missing"]
    digest = file_sha256(source_path)
    if digest != track.get("sha256") or digest != track.get("source_sha256"):
        problems.append("original music file SHA-256 is not attested")
    evidence_path = Path(str(track.get("rights_evidence_path") or "/missing"))
    if not evidence_path.is_file():
        return problems + ["individual episode license evidence file missing"]
    try:
        if file_sha256(evidence_path) != track.get("rights_evidence_sha256"):
            problems.append("license evidence file was altered")
        proof = json.loads(evidence_path.read_text(encoding="utf-8"))
        if (proof.get("episode_id") != episode_id
                or proof.get("source_sha256") != digest
                or proof.get("source_url") != track.get("source_url")
                or proof.get("license_url") != official_license
                or proof.get("provider") != provider):
            problems.append("license dossier not bound to exact episode/source")
        if (proof.get("reviewer") != "MOTOR_V21_MEDIA_REVIEW"
                or proof.get("license_review_status") != "CLEARED_FOR_THIS_EPISODE"
                or proof.get("commercial_video_use") is not True
                or proof.get("standalone_distribution") is not False
                or not {"youtube_shorts", "tiktok"}.issubset(set(proof.get("platforms") or []))
                or proof.get("third_party_rights") != "CLEARED_FOR_THIS_EDITORIAL_USE"
                or proof.get("content_id_status") not in {
                    "REVIEWED_NO_KNOWN_UNRESOLVED_CLAIM", "CLAIM_RESOLUTION_DOCUMENTED"
                }
                or not proof.get("source_license_citation")
                or not proof.get("reviewed_on")):
            problems.append("commercial/platform/third-party/Content ID clearance incomplete")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        problems.append("archived license evidence unreadable")
    return problems


def select_soundtrack(story: dict[str, Any], tracks: list[dict[str, Any]]) -> dict[str, Any]:
    """Motor's sole editorial decision. Legal and sound evidence is mandatory."""
    genre = str(story.get("genre") or "").strip()
    episode_id = str(story.get("episode_id") or "").strip()
    duration = float(story.get("picture_duration_seconds") or 0)
    if genre not in STORY_WEIGHTS or not 60 <= duration <= 80 or not episode_id:
        return {"status": "BLOCKED", "reason": "story identity/genre/duration unverified",
                "requires_new_search": True}
    if not isinstance(tracks, list) or not tracks:
        return {"status": "BLOCKED", "reason": "empty music inventory",
                "requires_new_search": True}
    identities = [str(t.get("track_id") or "") for t in tracks]
    if not all(identities) or len(identities) != len(set(identities)):
        return {"status": "BLOCKED", "reason": "duplicated/missing track identifiers"}
    qualified, rejected = [], []
    for t in tracks:
        tid = str(t.get("track_id") or "")
        tags = {str(x).lower() for x in t.get("tags", [])}
        problems = []
        if tags & FORBIDDEN or t.get("contains_siren_or_alarm") is not False:
            problems.append("siren/alarm or intrusive effects prohibited")
        if not tags & PREFERRED:
            problems.append("no suitable low-key cinematic suspense tags")
        if t.get("lead_vocals") is not False or t.get("speech_masking_qa") != "LOW":
            problems.append("lead vocals or speech-masking review unresolved")
        if (t.get("music_content_qa_method") != "MULTI_SEGMENT_LISTENING_AND_SPECTRAL_REVIEW"
                or t.get("music_content_qa_status") != "PASS"):
            problems.append("independent music content/audio review absent")
        if t.get("source_duration_seconds", 0) < duration + 0.03:
            problems.append("source does not cover final end-card without looping")
        if (t.get("local_file_verified") is not True or
                t.get("acoustic_uniqueness_qa") != "VERIFIED"):
            problems.append("local media or independent acoustic uniqueness unverified")
        problems.extend(_check_source_rights(t, episode_id))
        if problems:
            rejected.append({"track_id": tid, "reasons": problems})
            continue
        score = sum(STORY_WEIGHTS[genre].get(tag, 0) for tag in tags)
        score += 2 * len(tags & PREFERRED)
        if t.get("low_dynamic_range") is True:
            score += 3
        if t.get("sparse_arrangement") is True:
            score += 3
        qualified.append((score, tid, t))
    if not qualified:
        return {"status": "BLOCKED", "reason": "no rights-verified suspense soundtrack",
                "rejected": rejected, "requires_new_search": True}
    qualified.sort(key=lambda x: (-x[0], x[1]))
    score, _, winner = qualified[0]
    return {
        "status": "EDITORIAL_SELECTED_RIGHTS_REVIEW_REQUIRED",
        "selected_track_id": winner["track_id"],
        "selected_audio_sha256": winner["sha256"],
        "selected_source_url": winner["source_url"],
        "selected_license_url": winner["license_url"],
        "selected_rights_evidence_sha256": winner["rights_evidence_sha256"],
        "score": score, "genre": genre, "episode_id": episode_id,
        "rejected": rejected,
        "required_next_gate": "NEW_MUSIC_REUSE_V21_AND_FINAL_AUDIO_QA",
        "publication_authorized": False,
        "note": "Ranking is never a license grant or a proof of worldwide originality.",
    }


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--story", type=Path, required=True)
    p.add_argument("--candidates", type=Path, required=True)
    args = p.parse_args()
    result = select_soundtrack(
        json.loads(args.story.read_text()),
        json.loads(args.candidates.read_text())["tracks"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("EDITORIAL_SELECTED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
