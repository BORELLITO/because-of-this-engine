"""Evidence-first per-episode soundtrack clearance, independent of music loudness.

A Mixkit free video license is not a proof of zero Content ID claims, editorial
fit, soundtrack identity in a master, or historical effects. This gate
compares a source/rights dossier to the REAL archived FFmpeg QA report and the
completed-master historical registry. No provider requests, uploads, TTS, or
publishing. Missing/forged proof fails closed, with separate diagnostic states.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SHA = re.compile(r"^[0-9a-f]{64}$")
MIXKIT_LISTING = "https://mixkit.co/free-stock-music/"
MIXKIT_LICENSE = "https://mixkit.co/license/modal/musicFree/"
MIXKIT_MP3_PREFIX = "https://assets.mixkit.co/music/"


def _load(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("evidence path escapes repository")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evidence JSON must be object: " + name)
    return data


def _trusted_mixkit_https(url: Any, host: str) -> bool:
    parsed = urlparse(str(url or ""))
    return parsed.scheme == "https" and parsed.hostname == host and not parsed.username and not parsed.password


def audit(repo_root: Path, episode_id: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    failures: list[str] = []
    evidence: dict[str, Any] = {
        "license_for_commercial_online_video": "UNVERIFIED",
        "original_music_bytes": "UNVERIFIED",
        "new_song_vs_five_known_historical_sources": "UNVERIFIED",
        "actual_private_audio_mix": "UNVERIFIED",
        "creative_fitness_for_story": "UNVERIFIED",
        "content_id_claim_risk": "UNVERIFIED",
        "historical_sfx": "UNKNOWN",
    }
    details: dict[str, Any] = {}
    if not re.fullmatch(r"episode-\d{3}", str(episode_id)):
        failures.append("episode identifier must match episode-NNN")
        return _report(episode_id, evidence, details, failures)

    try:
        d = _load(root, f"episodes/{episode_id}/music-clearance-v21.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append("episode music-rights dossier missing or invalid: " + str(exc))
        return _report(episode_id, evidence, details, failures)

    if d.get("episode_id") != episode_id:
        failures.append("dossier belongs to a different episode")
    if d.get("schema_version") != "1.0":
        failures.append("unsupported soundtrack dossier schema")

    provider = str(d.get("provider") or "")
    mp3 = d.get("original_source_url")
    expected_license = MIXKIT_LICENSE
    license_info = d.get("license_scope") or {}
    if (provider != "mixkit" or
            not _trusted_mixkit_https(d.get("official_listing_url"), "mixkit.co") or
            not _trusted_mixkit_https(d.get("official_category_url"), "mixkit.co") or
            not _trusted_mixkit_https(d.get("official_license_url"), "mixkit.co") or
            d.get("official_license_url") != expected_license or
            not _trusted_mixkit_https(mp3, "assets.mixkit.co") or
            not str(mp3).startswith(MIXKIT_MP3_PREFIX)):
        failures.append("source/provider/license URLs do not match the official Mixkit identity")
    elif (license_info.get("status") != "PROVIDER_MUSIC_FREE_LICENSE_LISTED"
            or license_info.get("commercial_online_video_allowed") is not True
            or license_info.get("online_social_video_allowed") is not True
            or license_info.get("no_payment_required") is not True
            or license_info.get("independent_content_id_clearance") is not False):
        failures.append("free Mixkit video license scope incomplete or falsely presented as Content ID clearance")
    else:
        evidence["license_for_commercial_online_video"] = "SOURCE_TERMS_CONFIRMED_NOT_GLOBAL_CLAIM_WAIVER"

    try:
        qa_path = d.get("source_qa_report")
        if not isinstance(qa_path, str) or not qa_path.startswith("reports/"):
            raise ValueError("QA report must be a versioned repository report")
        qa = _load(root, qa_path)
        # The immutable Episode005 head-to-head test is a different schema
        # from the earlier single-track Silent Descent QA. Select the *actual*
        # music row by source SHA/URL rather than trusting an editorial label.
        if isinstance(qa.get("candidates"), list):
            candidate = next(
                (x for x in qa["candidates"]
                 if x.get("title") == d.get("title")
                 and x.get("source_sha256") == d.get("source_sha256")), None)
            history = d.get("source_evidence") or {}
            workflow = qa.get("evidence_workflow") or {}
            music_sha = d.get("source_sha256")
            if not candidate or (
                qa.get("episode_id") != episode_id or
                qa.get("scope") != "TWO_REAL_ORIGINAL_MIXKIT_MUSIC_STOCK_SOURCES_WITH_EXISTING_APPROVED_CHARON_PRIVATE_QA_ONLY" or
                not SHA.fullmatch(str(music_sha or "")) or
                candidate.get("artist") != d.get("artist") or
                candidate.get("source_url") != mp3 or
                abs(float(candidate.get("source_duration_seconds") or 0) -
                    float(d.get("source_duration_seconds") or 0)) > 0.05 or
                workflow.get("run_id") != history.get("qa_workflow_run_id") or
                workflow.get("conclusion") != "success" or
                not bool((qa.get("approved_voice") or {}).get("existing_cache_only")) or
                (qa.get("approved_voice") or {}).get("voice_name") != "Charon"):
                failures.append("Selpan original MP3 and exact-head-to-head QA provenance inconsistent")
            else:
                evidence["original_music_bytes"] = "SHA256_VERIFIED_IN_EXISTING_PRIVATE_QA_RUN"
            mix = qa.get("mix") or {}
            if (mix.get("source_ids_compared") != 5 or
                    history.get("acoustic_catalog_count") != 5 or
                    candidate.get("max_historic_similarity", 1) >= 0.78 or
                    mix.get("known_reuse_status") != "NO_MATCH_IN_KNOWN_FIVE"):
                failures.append("new candidate five-source acoustic replay/collision evidence missing")
            else:
                evidence["new_song_vs_five_known_historical_sources"] = "NO_MATCH_IN_KNOWN_CATALOG_ONLY"
            if (qa.get("status") != "PRIVATE_HEAD_TO_HEAD_TECHNICAL_PASS_RELEASE_BLOCKED" or
                    mix.get("stem_replay_verified") is not True or
                    candidate.get("technical_verdict") != "PASS" or
                    (qa.get("provisional_director_choice") or {}).get("title") != d.get("title")):
                failures.append("selected Selpan preview/voice mix was not genuinely verified")
            else:
                evidence["actual_private_audio_mix"] = "TECHNICAL_PASS_NOT_MASTER_OR_PUBLICATION"
        else:

            candidate = qa.get("candidate") or {}
            sfx_report = qa.get("source_review") or {}
            mix = qa.get("mix") or {}
            source_evidence = d.get("source_evidence") or {}
            sha = d.get("source_sha256")
            if (qa.get("episode_id") != episode_id or
                    qa.get("provider", "").lower() != provider or
                    candidate.get("title") != d.get("title") or
                    candidate.get("artist") != d.get("artist") or
                    candidate.get("original_mp3_url") != mp3 or
                    candidate.get("license_url") != expected_license or
                    candidate.get("original_audio_sha256") != sha or
                    not SHA.fullmatch(str(sha or "")) or
                    abs(float(candidate.get("duration_seconds") or 0) -
                        float(d.get("source_duration_seconds") or 0)) > .05):
                failures.append("source identity/duration disagrees with original MP3 and archived QA")
            else:
                evidence["original_music_bytes"] = "SHA256_VERIFIED_IN_EXISTING_PRIVATE_QA_RUN"
            if (sfx_report.get("historical_catalog_sources_verified") != 5 or
                    sfx_report.get("known_catalog_reuse") != "NO_MATCH_IN_KNOWN_CATALOG" or
                    source_evidence.get("acoustic_catalog_count") != 5 or
                    source_evidence.get("qa_workflow_run_id") !=
                    (qa.get("qa_ci") or {}).get("run_id") or
                    (qa.get("qa_ci") or {}).get("conclusion") != "success"):
                failures.append("five-source acoustic comparison not substantiated by archived CI")
            else:
                evidence["new_song_vs_five_known_historical_sources"] = "NO_MATCH_IN_KNOWN_CATALOG_ONLY"
            if (mix.get("mix_receipt_replay") is not True or
                    set(mix.get("stem_contributions") or []) != {"music", "narration"} or
                    (qa.get("decision") or {}).get("status") !=
                        "PRIVATE_AUDIO_QA_TECHNICAL_PASS_NOT_RELEASE_APPROVED" or
                    (qa.get("narration") or {}).get("voice_name") != "Charon"):
                failures.append("archived private Charon mix technical evidence incomplete")
            else:
                evidence["actual_private_audio_mix"] = "TECHNICAL_PASS_NOT_MASTER_OR_PUBLICATION"
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        failures.append("archived real-media audio QA missing/invalid: " + str(exc))

    editorial = d.get("editorial_fit") or {}
    if editorial.get("status") == "INDEPENDENT_STORY_FIT_VERIFIED":
        if (not str(editorial.get("audio_qa_evidence_artifact_sha256") or "") or
                not SHA.fullmatch(str(editorial.get("audio_qa_evidence_artifact_sha256"))) or
                not editorial.get("reasoned_story_fit_review")):
            failures.append("creative fit claimed without independently traceable listening report")
        else:
            evidence["creative_fitness_for_story"] = "EVIDENCE_DECLARED_NEEDS_INDEPENDENT_REVIEW"
    else:
        failures.append("editorial fit for historical-investigative suspense not verified")
        if (editorial.get("status") == "PENDING_INDEPENDENT_STORY_FIT" and
                editorial.get("suspense_or_investigative_tags_in_provider_listing") is False):
            evidence["creative_fitness_for_story"] = "HOLD_MELANCHOLIC_PROVIDER_TAGS_NOT_SUSPENSE_PROOF"
        elif editorial.get("status") == "PENDING_INDEPENDENT_STORY_FIT":
            evidence["creative_fitness_for_story"] = "PENDING_STORY_MUSIC_AUDITION_PROVIDER_TAGS_ONLY"

    # Heuristic signal inspection may flag siren-like sweeps or sharp
    # transients but CANNOT assert absence of sirens, vocal masking or other
    # intrusive effects; a full-source qualified audition remains required.
    screen = d.get("audio_content_screen") or {}
    if (screen.get("status") != "QUALIFIED_CONTENT_REVIEW_PASS" or
            screen.get("siren_absence_certified") is not True or
            screen.get("speech_masking_safely_verified") is not True or
            not SHA.fullmatch(str(screen.get("independent_audio_review_sha256") or ""))):
        failures.append("source listening/SFX/no-siren and voice-masking review is pending")
        evidence["music_sfx_content_review"] = "PENDING_FULL_SOURCE_AUDITION_AND_VOICE_CLARITY"

    claim = d.get("content_id") or {}
    if claim.get("status") == "PLATFORM_EVIDENCE_REVIEWED_NO_UNRESOLVED_CLAIM":
        if (not SHA.fullmatch(str(claim.get("platform_evidence_sha256") or "")) or
                not claim.get("platform_evidence_artifact_id") or
                claim.get("claim_exists") is not False):
            failures.append("Content ID assertion lacks platform-sourced evidence")
        else:
            evidence["content_id_claim_risk"] = "PLATFORM_REPORT_DECLARED_NOT_GLOBAL_IMMUNITY"
    else:
        failures.append("Content ID status unknown; Mixkit license cannot guarantee no claims")
        evidence["content_id_claim_risk"] = "PENDING_PLATFORM_OR_PROVIDER_CASE_EVIDENCE"

    # Historical SFX must be measured from the independent completed-master
    # registry. A user-supplied 'VERIFIED' dossier cannot fabricate missing
    # stem/audio-source mix receipts.
    try:
        masters = _load(root, "episodes/audio-rendered-master-registry.json")
        rendered = masters.get("rendered_masters") or []
        if not isinstance(rendered, list) or len(rendered) != 4:
            failures.append("four historical master evidence records unavailable")
        else:
            known = sum(int(row.get("sfx_tracks_verified") or 0) for row in rendered)
            details["historical_master_count"] = len(rendered)
            details["historical_verified_sfx_source_count"] = known
            details["historical_soundtrack_collision_count"] = len(
                masters.get("verified_full_track_collisions") or [])
            if (d.get("historical_sfx") or {}).get("verified_sfx_stem_sources") != known:
                failures.append("SFX dossier disagrees with independent master registry")
            if known == 0 or masters.get("historical_sfx_coverage") != "VERIFIED_COMPLETE":
                failures.append("historical SFX contributions remain unproven")
                evidence["historical_sfx"] = "ZERO_INDEPENDENT_STEM_PROOFS_DO_NOT_RETROACTIVELY_APPROVE"
            else:
                evidence["historical_sfx"] = "INDEPENDENT_MASTER_REGISTRY_DECLARED_COMPLETE"
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        failures.append("historical master SFX evidence not readable: " + str(exc))

    if (d.get("decision") or {}).get("status") != "APPROVED_FOR_RELEASE":
        failures.append("episode music candidate is not release-approved by the sound director")

    return _report(episode_id, evidence, details, failures)


def _report(episode_id: str, evidence: dict[str, Any],
            details: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    return {
        "gate": "V21_MUSIC_RIGHTS_CONTENT_ID_SFX_RELEASE",
        "episode_id": episode_id,
        "status": "BLOCKED" if failures else "PASS",
        "evidence": evidence,
        "historical_inventory": details,
        "failures": failures,
        "monetary_spend_authorized": False,
        "production_authorized": False,
        "publication_authorized": False,
        "tts_requests": 0,
        "audit_mode": "READ_ONLY",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--episode", type=str, default="episode-005")
    a = p.parse_args()
    result = audit(a.repo_root, a.episode)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
