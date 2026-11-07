"""Automatic per-story cinematic suspense bed ranking, fail closed on rights.

Ranks only evidenced, local audio candidates; does NOT scrape/download or
infer that 'royalty free' means free of all copyright claims. Real file,
commercial use rights, track-specific source URL and reuse checks are required
before the winner can enter the existing render_v21_final gate.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

FORBIDDEN = {"siren", "alarm", "emergency", "police", "air_raid",
             "horn", "loud_stinger", "explosion", "jump_scare"}
PREFERRED = {"dark_ambient", "psychological_suspense", "cinematic_drone",
             "minimal_tension", "investigative", "subtle_tension"}
STORY_WEIGHTS = {
    "historical_mystery": {"investigative": 5, "minimal_tension": 4, "cinematic_drone": 3},
    "psychological_horror": {"psychological_suspense": 6, "dark_ambient": 4},
    "human_tragedy": {"subtle_tension": 6, "minimal_tension": 5},
    "true_story": {"investigative": 5, "minimal_tension": 4},
    "supernatural": {"dark_ambient": 6, "cinematic_drone": 4},
}


def select_soundtrack(story: dict[str, Any], tracks: list[dict[str, Any]]) -> dict[str, Any]:
    """Editorial selection, not a legal license grant or audio-source verifier."""
    genre = str(story.get("genre") or "").strip()
    duration = float(story.get("picture_duration_seconds") or 0)
    if genre not in STORY_WEIGHTS or not 60 <= duration <= 80:
        return {"status": "BLOCKED", "reason": "story genre/duration not verified"}
    qualified = []
    rejected = []
    for t in tracks:
        tid = str(t.get("track_id") or "")
        tags = {str(x).lower() for x in t.get("tags", [])}
        problems = []
        if tags & FORBIDDEN or t.get("contains_siren_or_alarm") is not False:
            problems.append("siren/alarm or intrusive effects prohibited")
        if not tags & PREFERRED:
            problems.append("no suitable low-key cinematic suspense tags")
        if (t.get("license_verified") is not True or
                t.get("commercial_video_use") is not True or
                t.get("modification_allowed") is not True or
                t.get("item_license_evidence") != "VERIFIED" or
                not str(t.get("license_url") or "").startswith("https://") or
                not str(t.get("source_url") or "").startswith("https://")):
            problems.append("item-specific license/commercial use evidence incomplete")
        if t.get("content_id_risk_review") != "VERIFIED":
            problems.append("Content ID review missing")
        if t.get("local_file_verified") is not True or t.get("acoustic_uniqueness_qa") != "VERIFIED":
            problems.append("local file or independent acoustic uniqueness unverified")
        if t.get("source_duration_seconds", 0) < 10:
            problems.append("source too short for verifiable looping")
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
    return {"status": "EDITORIAL_SELECTED_RIGHTS_REVIEW_REQUIRED",
            "selected_track_id": winner["track_id"],
            "score": score, "genre": genre,
            "rejected": rejected,
            "required_next_gate": "NEW_MUSIC_REUSE_V21_AND_FINAL_AUDIO_QA",
            "publication_authorized": False,
            "note": "Ranking does not replace local SHA/Chromaprint, full rights or master QA."}


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
