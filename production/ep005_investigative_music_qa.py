"""EP005 official Mixkit music head-to-head — read-only source/technical QA.

Runs on a standard free GitHub-hosted runner in a public repository.
Sources: official Mixkit stock page+CDN; narration: already-approved
GitHub artifact. No TTS, paid API, final render, Drive or publication.
Does not claim human audition, siren clearance or Content ID immunity.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import re
import subprocess
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from production.audio_acoustic_fingerprint_v21 import catalog_coverage, review_file
from production.audio_mix_receipt_v21 import execute_with_receipt, verify_receipt, file_sha256
from production.render_v21_final import build_audio_mix_command, _time_signature, PROFILE_PATH
from production.render_v21_preview import validate_voice_profile, media_duration
from production.zero_cost_v21 import evaluate_cost

LISTING = "https://mixkit.co/free-stock-music/drone-music/"
LICENSE = "https://mixkit.co/license/modal/musicFree/"
TARGETS = {
    "Selpan": {
        "artist": "Eugenio Mininni",
        "url": "https://assets.mixkit.co/music/612/612.mp3",
        "duration_listed_seconds": 194,
        "tags": ["mysterious", "eerie", "investigation", "documentary",
                 "electric_guitar", "sound_effects"],
    },
    "Delirium": {
        "artist": "Eugenio Mininni",
        "url": "https://assets.mixkit.co/music/605/605.mp3",
        "duration_listed_seconds": 290,
        "tags": ["mysterious", "disturbing", "investigation", "crime",
                 "bass", "sound_effects"],
    },
}
VOICE_SHA = "0746581eae60c3cccf69173f24658b8dc49fdbb85c74d060c26b7dcecae66ebe"
CANDIDATE_RANKING_TAGS = {"investigation": 5, "documentary": 5, "mysterious": 4,
                          "eerie": 3, "disturbing": 1, "crime": -3,
                          "sound_effects": -1, "electric_guitar": 0, "bass": 0}


def official_cdn_from_listing(html: str, title: str) -> str:
    """Bind title+artist+actual URL in Mixkit JSON-LD; refuse guesses/changes."""
    if title not in TARGETS:
        raise ValueError("unreviewed music title")
    artist = TARGETS[title]["artist"]
    pattern = (r'"name"\s*:\s*"' + re.escape(title)
               + r'"(?P<context>[\s\S]{0,380}?)"url"\s*:\s*"'
               + r'(?P<url>https://assets\.mixkit\.co/music/\d+/\d+\.mp3)"')
    matches = []
    for m in re.finditer(pattern, html):
        if re.search(r'"byArtist"\s*:\s*"' + re.escape(artist) + r'"', m.group("context")):
            matches.append(m.group("url"))
    if len(set(matches)) != 1:
        raise ValueError("no unique exact official track metadata for " + title)
    url = matches[0]
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "assets.mixkit.co"
            or url != TARGETS[title]["url"]):
        raise ValueError("official source changed unexpectedly for " + title)
    return url


def editorial_score(title: str) -> int:
    if title not in TARGETS:
        raise ValueError("unknown candidate")
    return sum(CANDIDATE_RANKING_TAGS.get(tag, 0) for tag in TARGETS[title]["tags"])


def _download(url: str, dest: Path, max_bytes: int = 24_000_000) -> str:
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc not in {"mixkit.co", "assets.mixkit.co"}
            or parsed.username or parsed.password):
        raise ValueError("untrusted download host")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; BOT-V21-Stock-Music-QA/1.0)"
    })
    with urllib.request.urlopen(req, timeout=40) as response:
        if urllib.parse.urlsplit(response.geturl()).netloc != parsed.netloc:
            raise ValueError("provider redirected to unexpected domain")
        data = response.read(max_bytes + 1)
    if not 10000 < len(data) <= max_bytes:
        raise ValueError("incomplete/oversized official provider source")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _duration(path: Path) -> float:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True, timeout=35)
    return float(completed.stdout.strip())


def _loudness(path: Path) -> tuple[float, float]:
    measured = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-v", "info",
         "-i", str(path), "-map", "0:a:0", "-af", "ebur128=peak=true",
         "-f", "null", "-"],
        check=True, capture_output=True, text=True, timeout=130)
    summary = measured.stderr.rsplit("Summary:", 1)[-1]
    lufs = re.search(r"Integrated loudness:\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", summary)
    peak = re.search(r"True peak:\s*Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", summary)
    if not lufs or not peak:
        raise RuntimeError("real FFmpeg EBU R128 measurements absent")
    return float(lufs.group(1)), float(peak.group(1))


def _outro_rms(mix: Path, begin: float, end: float) -> float:
    with wave.open(str(mix), "rb") as data:
        if data.getnchannels() != 1 or data.getsampwidth() != 2:
            raise RuntimeError("unexpected canonical mix format")
        rate = data.getframerate()
        start = min(data.getnframes(), round(begin * rate))
        data.setpos(start)
        frames = data.readframes(max(1, round((end - begin) * rate)))
    a = array.array("h")
    a.frombytes(frames)
    return math.sqrt(sum(i*i for i in a) / max(1, len(a)))


def run(*, repo_root: Path, voice_dir: Path, output_dir: Path) -> dict:
    repo_root = Path(repo_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cost = evaluate_cost("existing_charon_audio_reuse",
                         policy_path=repo_root / "production/active_engine_policy.json")
    if cost["status"] != "PASS":
        raise RuntimeError("zero-cost offline reuse policy failed")
    voice = voice_dir / "narration.wav"
    profile_path = voice_dir / "voice-profile.json"
    identity = validate_voice_profile(profile_path, voice)
    if identity.get("audio_sha256") != VOICE_SHA:
        raise RuntimeError("original Gemini/Charon narration identity changed")
    profile = json.loads((repo_root / PROFILE_PATH.relative_to(repo_root)).read_text())
    voice_seconds = media_duration(voice)
    total = _time_signature(profile, voice_seconds)
    assert profile["music_gain"] == .12 and profile["music_fade_out_seconds"] == 3.5
    coverage = catalog_coverage(repo_root)
    if coverage["status"] != "PASS" or coverage["known_source_count"] != 5:
        raise RuntimeError("five-source historical audio protection not verified")

    raw_page = output_dir / ".mixkit-listing.html"
    listing_sha = _download(LISTING, raw_page, max_bytes=3_000_000)
    html = raw_page.read_text(encoding="utf-8", errors="replace")
    report = {
        "schema_version": "1.0", "episode_id": "episode-005",
        "status": "PRIVATE_TECHNICAL_MUSIC_QA_NOT_RELEASE",
        "source": "MIXKIT_OFFICIAL_LISTING_AND_ORIGINAL_MP3_BYTES",
        "listing_url": LISTING, "listing_html_sha256": listing_sha,
        "license_url": LICENSE,
        "license_status": "FREE_COMMERCIAL_ONLINE_VIDEO_ALLOWED_NOT_CONTENT_ID_IMMUNITY",
        "credit_required": False,
        "actual_provider_content_id_check": "NOT_PERFORMED",
        "full_siren_absence_audition": "NOT_INDEPENDENTLY_VERIFIED",
        "human_or_qualified_listening_qa": "PENDING",
        "monetary_spend_authorized": False,
        "new_tts_calls": 0, "visual_render": "NOT_RUN",
        "drive_upload": "NOT_RUN", "publication_authorized": False,
        "production_enablement": False,
        "voice_sha256": VOICE_SHA,
        "voice_duration_seconds": voice_seconds, "outro_seconds": 5.5,
        "finished_audio_seconds": total, "music_gain": .12,
        "historical_catalog_coverage": coverage,
        "tracks": [], "provisional_editorial_selection": None,
    }
    raw_page.unlink(missing_ok=True)
    for title, expected in TARGETS.items():
        filename = title.lower()
        mp3 = output_dir / (".source-" + filename + ".mp3")
        try:
            url = official_cdn_from_listing(html, title)
            digest = _download(url, mp3)
            dur = _duration(mp3)
            if not total + .03 < dur or abs(dur - expected["duration_listed_seconds"]) > 3.0:
                raise RuntimeError("original track duration inadequate/metadata mismatch")
            acoustics = review_file(mp3, repo_root / "episodes/audio-acoustic-fingerprints-v21.json")
            if acoustics["status"] != "PASS":
                raise RuntimeError("new source resembles known historical music: " + str(acoustics))
            # Real, replayed FFmpeg mix from preapproved Charon and original stock
            # audio. Private audio-only podcast-like proof; no unmodified stock.
            mix = output_dir / (".mixed-" + filename + ".wav")
            receipt = output_dir / (".receipt-" + filename + ".json")
            cmd = build_audio_mix_command(voice, mp3, {}, mix,
                                          voice_seconds=voice_seconds, profile=profile)
            execute_with_receipt("episode-005", cmd, {"narration": voice, "music": mp3}, mix, receipt)
            proof = verify_receipt(receipt, replay=True)
            if proof["status"] != "PASS" or set(proof["source_contributions_confirmed"]) != {"narration", "music"}:
                raise RuntimeError("audio original/Charon postmix source replay failed")
            out = output_dir / ("EP005_" + title + "_Charon_Suspense_Private_QA.mp3")
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
                            "-i", str(mix), "-c:a", "libmp3lame", "-b:a", "192k",
                            "-y", str(out)], check=True, capture_output=True, timeout=120)
            lufs, peak = _loudness(out)
            if not -20 <= lufs <= -13 or peak > -1:
                raise RuntimeError(f"audio loudness/true peak blocked {lufs}, {peak}")
            early = _outro_rms(mix, voice_seconds + .12, voice_seconds + .8)
            late = _outro_rms(mix, total - .25, total - .05)
            if not (early > 10 and late < early * .6):
                raise RuntimeError("music outro/fade technically not verified")
            report["tracks"].append({
                "title": title, "artist": expected["artist"],
                "provider_original_url": url, "original_mp3_sha256": digest,
                "source_seconds": round(dur, 3),
                "tags_from_listing": expected["tags"], "story_fit_score_metadata_only": editorial_score(title),
                "historic_reuse": "NO_MATCH_IN_KNOWN_5_ONLY",
                "best_known_acoustic_similarity": acoustics["best_matches"][0]["similarity"],
                "actual_charon_mix": "REPLAYED_WITH_MUSIC_AND_NARRATION",
                "source_contributions_confirmed": proof["source_contributions_confirmed"],
                "preview_filename": out.name,
                "preview_mp3_sha256": file_sha256(out),
                "lufs": lufs, "true_peak_dbTP": peak,
                "outro_early_rms": round(early, 3),
                "outro_near_black_rms": round(late, 3),
                "technical_qa": "PASS",
                "release_status": "PENDING_CONTENT_ID_AND_INDEPENDENT_AUDITION",
                "siren_absence_not_certified": True,
            })
            print("EP005_REAL_MUSIC_QA_PASS", title, digest, lufs, peak, round(early, 1), round(late, 1))
        finally:
            mp3.unlink(missing_ok=True)
            (output_dir / (".mixed-" + filename + ".wav")).unlink(missing_ok=True)
            (output_dir / (".receipt-" + filename + ".json")).unlink(missing_ok=True)

    if len(report["tracks"]) != len(TARGETS):
        raise RuntimeError("both independent source tracks are required for comparison")
    ranking = sorted(report["tracks"], key=lambda x: (-x["story_fit_score_metadata_only"], x["title"]))
    report["provisional_editorial_selection"] = {
        "title": ranking[0]["title"], "reason": "highest investigative-documentary source metadata fit",
        "status": "BEST_METADATA_FIT_REQUIRES_INDEPENDENT_AUDITION",
        "not_a_release_clearance": True,
    }
    (output_dir / "EP005_MIXKIT_INVESTIGATIVE_COMPARISON_QA.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return report


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--voice-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a=p.parse_args()
    r=run(repo_root=a.repo_root,voice_dir=a.voice_dir,output_dir=a.output_dir)
    print("EP005_MIXKIT_TWO_CANDIDATE_PRIVATE_QA_OK",json.dumps({
        "selected_provisionally":r["provisional_editorial_selection"],
        "audio_count":len(r["tracks"]),
        "production_enabled":False,"content_id":"NOT_VERIFIED"}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
