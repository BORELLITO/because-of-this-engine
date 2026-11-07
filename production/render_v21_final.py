"""Canonical V2.1 final assembly from the already-approved, hashed creative preview.

This module intentionally reuses the existing V2.1 preview's 16-scene
picture, word-timed captions, logo, grading, factual notices and outro.
It NEVER re-creates the story visuals, calls TTS, uses V7, touches Drive,
or publishes. Real final dispatch is subject to the canonical final preflight,
source rights, music catalog, SFX proof and disabled production policy.

The internal media assembly helper is exercised using synthetic local files;
it is not a bypass/approval to run the episode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from production.music_autoselect_v21 import select_for_story
from production.audio_mix_receipt_v21 import execute_with_receipt, file_sha256
from production.render_v21_manual import validate_completed_audio_mix, validate_request
from production.render_v21_preview import validate_voice_profile, media_duration

EXPECTED_CREATIVE_PROFILE = "cinematic_dread_v73"
EXPECTED_NARRATION_PROVIDER = "gemini_tts"
EXPECTED_NARRATION_VOICE = "Charon"
PROFILE_PATH = Path(__file__).resolve().parent / "audio_mix_profile_v21.json"
OUTRO_SECONDS = 5.5


class FinalRenderError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalRenderError("required JSON evidence cannot be read: " + str(path)) from exc
    if not isinstance(data, dict):
        raise FinalRenderError("JSON evidence must be an object")
    return data


def _probe(path: Path) -> dict[str, Any]:
    try:
        run = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate:"
             "format=duration", "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=35)
        info = json.loads(run.stdout)
        return info
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        raise FinalRenderError("media FFprobe failed: " + str(path)) from exc


def _video_payload_sha256(path: Path) -> str:
    """Compressed video bitstream hash, independent of MP4 container/audio."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
             "-i", str(path), "-map", "0:v:0", "-c:v", "copy",
             "-f", "hash", "-hash", "sha256", "-"],
            check=True, capture_output=True, text=True, timeout=90,
        )
        value = p.stdout.strip()
        if not value.startswith("SHA256=") or len(value[7:]) != 64:
            raise ValueError("invalid FFmpeg hash payload")
        return value[7:]
    except (OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, ValueError) as exc:
        raise FinalRenderError("video stream cannot be verified") from exc


def _time_signature(profile: dict[str, Any], voice_seconds: float) -> float:
    if profile.get("profile_id") != "v21-cinematic-dread-charon-final-audio-candidate":
        raise FinalRenderError("audio profile identity changed")
    if (profile.get("voice_provider"), profile.get("voice_name")) != (
            EXPECTED_NARRATION_PROVIDER, EXPECTED_NARRATION_VOICE):
        raise FinalRenderError("audio profile changed frozen Gemini/Charon identity")
    if (profile.get("inherits") != EXPECTED_CREATIVE_PROFILE or
            profile.get("target_voice_integrated_loudness_lufs") != -16 or
            profile.get("outro_seconds") != OUTRO_SECONDS):
        raise FinalRenderError("frozen creative audio calibration/outro changed")
    if profile.get("status") not in {
            "CANDIDATE_FOR_QA_NOT_RELEASE_APPROVED", "INDEPENDENT_AUDIO_QA_PASS"}:
        raise FinalRenderError("audio mix profile status invalid")
    if not 60 <= voice_seconds or voice_seconds + OUTRO_SECONDS > 80.0:
        raise FinalRenderError("voice/outro timing cannot fit 60–80s final master")
    for key in ("music_gain", "sfx_gain"):
        value = profile.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 1:
            raise FinalRenderError("audio gain must be conservative")
    if (profile.get("music_gain") > 0.12
            or profile.get("music_gain_max") != 0.12
            or profile.get("music_starts_at_seconds") != 0
            or profile.get("music_to_last_frame") is not True
            or profile.get("music_ends_before_outro") is not False
            or profile.get("outro_audio") != "music_fades_with_visual_to_black"
            or profile.get("music_fade_out_alignment")
               != "last_1.2_seconds_of_existing_outro_visual_fade"
            or profile.get("music_fade_out_seconds") != 1.2
            or profile.get("music_fade_in_seconds") != 0.4
            or profile.get("music_duration_policy") != "MATCH_EXACT_FINAL_MASTER_NO_LOOPS"):
        raise FinalRenderError("approved continuous music, gain ceiling or outro fade contract changed")
    selection = profile.get("music_selection") or {}
    duck = profile.get("speech_ducking") or {}
    if (selection.get("decision_maker") != "MOTOR_V21"
            or selection.get("required_every_video") is not True
            or selection.get("no_approved_track_action") != "BLOCK_ACQUIRE_ALTERNATIVES_NOT_SILENCE"
            or duck.get("enabled") is not True
            or duck.get("method") != "ffmpeg_sidechaincompress"
            or not 0 < duck.get("threshold", 0) <= 0.1
            or not 2 <= duck.get("ratio", 0) <= 8
            or not 5 <= duck.get("attack_ms", 0) <= 40
            or not 100 <= duck.get("release_ms", 0) <= 800):
        raise FinalRenderError("autonomous sound selection or voice-ducking contract changed")
    return round(voice_seconds + OUTRO_SECONDS, 3)


def build_audio_mix_command(
    narration: Path, music: Path, sfx: dict[str, Path],
    output: Path, *, voice_seconds: float, profile: dict[str, Any],
) -> list[str]:
    """Deterministic FFmpeg recipe; terms/creative mixing gains are explicit."""
    total = _time_signature(profile, voice_seconds)
    if any(not role.startswith("sfx:") or len(role) <= 4 or
           any(word in role.lower() for word in ("siren", "sirene", "alarm", "alarme", "horn", "klaxon"))
           for role in sfx):
        raise FinalRenderError("siren/alarm sound effects are prohibited in V2.1")
    if len(sfx) != len(set(sfx)) or len(sfx) > 10:
        raise FinalRenderError("too many or duplicate effect roles")
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
        "-i", str(narration.resolve()), "-i", str(music.resolve()),
    ]
    for name in sorted(sfx):
        command += ["-i", str(sfx[name].resolve())]

    # User-approved intent: subtle 0.12 maximum, narration always foreground.
    # The music starts at t=0, is ducked whenever Charon speaks, continues
    # across the voice-free branded outro and fades with its last 1.2s to black.
    fade_at = total - profile["music_fade_out_seconds"]
    duck = profile["speech_ducking"]
    graph = [
        f"[0:a]aresample=48000,loudnorm=I=-16:TP=-1:LRA=7,"
        f"alimiter=limit=0.95,atrim=duration={voice_seconds:.3f},"
        f"asetpts=PTS-STARTPTS,apad=pad_dur={OUTRO_SECONDS:.3f},"
        f"atrim=duration={total:.3f},asplit=2[v][voice_key]",
        f"[1:a]aresample=48000,atrim=duration={total:.3f},"
        f"asetpts=PTS-STARTPTS,volume={profile['music_gain']:.4f},"
        f"afade=t=in:st=0:d={profile['music_fade_in_seconds']:.3f},"
        f"afade=t=out:st={fade_at:.3f}:d={profile['music_fade_out_seconds']:.3f}[musicbed]",
        f"[musicbed][voice_key]sidechaincompress="
        f"threshold={duck['threshold']:.4f}:ratio={duck['ratio']:.2f}:"
        f"attack={duck['attack_ms']}:release={duck['release_ms']}[ducked]",
    ]
    inputs = ["[v]", "[ducked]"]
    for i, name in enumerate(sorted(sfx), start=2):
        graph.append(
            f"[{i}:a]aresample=48000,atrim=duration={voice_seconds:.3f},"
            f"asetpts=PTS-STARTPTS,volume={profile['sfx_gain']:.4f}[s{i}]"
        )
        inputs.append(f"[s{i}]")
    graph.append(
        "".join(inputs) + f"amix=inputs={len(inputs)}:duration=longest:normalize=0,"
        "alimiter=limit=0.95,"
        f"atrim=duration={total:.3f}[out]"
    )
    command += ["-filter_complex", ";".join(graph), "-map", "[out]",
                "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                "-y", str(output.resolve())]
    return command


def assemble_verified_picture_with_audio(
    *, picture: Path, narration: Path, music: Path, sfx: dict[str, Path],
    output: Path, mix_output: Path, audio_receipt: Path,
    voice_seconds: float, profile: dict[str, Any],
    episode_id: str,
) -> dict[str, Any]:
    """Internal deterministic real-media E2E lane, with no external writes.

    Caller MUST have passed validate_request(mode='final') and required
    provenance checks. It refuses to overwrite anything previously approved.
    """
    destinations = [output, mix_output, audio_receipt]
    all_paths = [picture, narration, music, *sfx.values(), *destinations]
    if len({path.resolve() for path in all_paths}) != len(all_paths):
        raise FinalRenderError("source and destination paths must be unique")
    for path in (output, mix_output, audio_receipt):
        if path.exists():
            raise FinalRenderError("refusing to overwrite a previous video or audio receipt: " + str(path))
    total = _time_signature(profile, voice_seconds)
    music_metadata = _probe(music)
    music_seconds = float((music_metadata.get("format") or {}).get("duration") or 0)
    if music_seconds < total + 0.03:
        raise FinalRenderError("full-length music source is shorter than final picture/outro; looping forbidden")
    picture_metadata = _probe(picture)
    image_streams = [x for x in picture_metadata.get("streams", [])
                     if x.get("codec_type") == "video"]
    if len(image_streams) != 1 or image_streams[0].get("codec_name") != "h264":
        raise FinalRenderError("verified picture must have a single H264 stream")
    picture_duration = float(picture_metadata.get("format", {}).get("duration") or 0)
    if abs(picture_duration - total) > 0.36:
        raise FinalRenderError("picture duration differs from frozen Charon/outro timing")
    source_video_sha = _video_payload_sha256(picture)
    sources = {"narration": narration, "music": music, **sfx}
    mix_command = build_audio_mix_command(
        narration, music, sfx, mix_output,
        voice_seconds=voice_seconds, profile=profile)
    execute_with_receipt(episode_id, mix_command, sources, mix_output, audio_receipt)
    # The mandatory postflight below runs replay, per-stem counterfactual
    # verification and finished-master binding exactly once. Avoid redundant
    # expensive replays before the fast video stream-copy step.
    pending = output.with_name("." + output.stem + ".V21-CANDIDATE" + output.suffix)
    if pending.exists():
        raise FinalRenderError("unreviewed candidate output already exists")
    try:
        pending.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
             "-i", str(picture), "-i", str(mix_output),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-t", f"{total:.3f}", "-movflags", "+faststart", str(pending)],
            check=True, capture_output=True, text=True, timeout=180)
        postflight = validate_completed_audio_mix(
            {"episode_id": episode_id},
            receipt_path=audio_receipt, master_video=pending)
        if postflight.get("status") != "V21_AUDIO_POSTFLIGHT_EVIDENCE_PASS":
            raise FinalRenderError("finished master does not match independently replayed audio")
        actual_video_sha = _video_payload_sha256(pending)
        if source_video_sha != actual_video_sha:
            raise FinalRenderError("output video stream differs from approved picture/HUD/captions")
        os.replace(pending, output)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FinalRenderError) as exc:
        pending.unlink(missing_ok=True)
        raise FinalRenderError("real final assembly failed: " + str(exc)) from exc
    return {
        "status": "V21_FINAL_AUDIO_AND_PICTURE_TECHNICAL_PASS",
        "episode_id": episode_id,
        "picture_sha256": file_sha256(picture),
        "picture_video_stream_sha256": source_video_sha,
        "final_master_sha256": file_sha256(output),
        "mix_audio_sha256": file_sha256(mix_output),
        "receipt_sha256": file_sha256(audio_receipt),
        "stem_contributions": postflight["source_contributions_confirmed"],
        "master_audio_bound": postflight["master_audio_bound"],
        "total_duration_seconds": total,
        "publication": "MANUAL_ONLY_NOT_RUN",
        "drive_write": "NOT_RUN",
    }


def _verify_preview_binding(preview: Path, report: Path, voice: dict[str, Any]) -> None:
    p = _json(report)
    branding = p.get("branding") or {}
    if (p.get("status") != "V21_CREATIVE_PREVIEW_RENDER_PASS" or
            p.get("creative_profile") != EXPECTED_CREATIVE_PROFILE or
            p.get("scene_count") != 16 or
            p.get("music", {}).get("status") != "NOT_MIXED" or
            p.get("voice", {}).get("audio_sha256") != voice["audio_sha256"] or
            branding.get("logo_overlay") is not True or
            branding.get("caption_margin_v") != 650 or
            branding.get("active_word_color") != "#F04444" or
            branding.get("outro_audio") != "silence" or
            p.get("visual_continuity_gate", {}).get("status") != "PASS"):
        raise FinalRenderError("approved V2.1 preview, captions, visual truth or branding changed")
    if p.get("output_sha256") != file_sha256(preview):
        raise FinalRenderError("rendered preview bytes disagree with frozen preview report")


def _verify_sfx_evidence(
    episode_id: str, stems: dict[str, Path], manifest_path: Path,
) -> None:
    data = _json(manifest_path)
    if data.get("episode_id") != episode_id:
        raise FinalRenderError("SFX manifest episode mismatch")
    entries = data.get("stems")
    if not stems and data.get("status") == "QA_VERIFIED_NO_SFX_REQUIRED":
        if entries != [] or data.get("story_sound_design") != "AMBIENT_MUSIC_ONLY":
            raise FinalRenderError("no-SFX story decision missing independent context")
        return
    if data.get("status") != "QA_VERIFIED":
        raise FinalRenderError("episode-scoped SFX manifest or independent QA missing")
    if not isinstance(entries, list) or len(entries) != len(stems):
        raise FinalRenderError("SFX sources and manifest must match")
    seen: set[str] = set()
    for entry in entries:
        role = entry.get("role") if isinstance(entry, dict) else None
        if role not in stems or role in seen or any(
                banned in str(role).lower()
                for banned in ("siren", "sirene", "alarm", "alarme", "horn", "klaxon")):
            raise FinalRenderError("SFX role missing, prohibited siren/alarm or duplicated")
        seen.add(role)
        if (entry.get("source_sha256") != file_sha256(stems[role]) or
                entry.get("license_status") != "APPROVED" or
                entry.get("timing_review") != "VERIFIED"):
            raise FinalRenderError("SFX rights, timeline or real source fingerprint unverified")


def run_final(
    *,
    record_path: Path, repo_root: Path, preview: Path, preview_report: Path,
    narration: Path, voice_profile: Path, music: Path, music_candidate: Path,
    effects_manifest: Path, sfx: dict[str, Path],
    output: Path, mix_output: Path, receipt: Path, report: Path,
) -> dict[str, Any]:
    """One supported final dispatch: preflight FIRST, then verified media only."""
    record = _json(record_path)
    from production.render_v21_manual import ManualRenderGateError
    try:
        gate = validate_request(record, repo_root=repo_root, mode="final")
    except (ManualRenderGateError, OSError, ValueError) as exc:
        raise FinalRenderError("canonical final render preflight blocked: " + str(exc)) from exc
    if gate.get("status") != "V21_MANUAL_RENDER_PREFLIGHT_PASS":
        raise FinalRenderError(
            "canonical final render preflight blocked: "
            + ",".join(gate.get("failures", []))
        )
    if any(x.exists() for x in (output, mix_output, receipt, report)):
        raise FinalRenderError("refusing to overwrite a prior V2.1 production artifact")
    voice = validate_voice_profile(voice_profile, narration)
    _verify_preview_binding(preview, preview_report, voice)
    _verify_sfx_evidence(str(record.get("episode_id")), sfx, effects_manifest)
    candidate = _json(music_candidate)
    audio_gate = check_file(music, candidate, root=repo_root)
    if audio_gate.get("status") != "PASS":
        raise FinalRenderError("music source anti-reuse/license evidence blocked: "
                               + str(audio_gate.get("failures", [])))
    # Distinct from source identity: explicit authorization and independent
    # music usage rights are required before actually dispatching the mix.
    if (candidate.get("episode_id") != record.get("episode_id") or
            candidate.get("editorial_use_approval") != "VERIFIED_BY_ENGINE" or
            not candidate.get("source_license_url")):
        raise FinalRenderError("episode-specific soundtrack provenance/rights missing")
    profile = _json(PROFILE_PATH)
    if profile.get("status") != "INDEPENDENT_AUDIO_QA_PASS":
        raise FinalRenderError("final music/SFX gain calibration has no independent listening QA")
    voice_seconds = media_duration(narration)
    result = assemble_verified_picture_with_audio(
        picture=preview, narration=narration, music=music, sfx=sfx,
        output=output, mix_output=mix_output, audio_receipt=receipt,
        voice_seconds=voice_seconds, profile=profile,
        episode_id=str(record.get("episode_id")))
    if result.get("status") != "V21_FINAL_AUDIO_AND_PICTURE_TECHNICAL_PASS":
        raise FinalRenderError("finished master technical verification blocked")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({
        **result,
        "preview_report_sha256": file_sha256(preview_report),
        "narration_profile_sha256": file_sha256(voice_profile),
        "music_candidate_sha256": file_sha256(music_candidate),
        "sfx_manifest_sha256": file_sha256(effects_manifest),
        "audio_profile_sha256": file_sha256(PROFILE_PATH),
        "production_authorized_for_this_render": True,
        "ready_for_publication": False,
        "publication": "MANUAL_ONLY_NOT_RUN",
        "new_tts_requests": 0,
        "visual_reconstruction": False,
        "render_source": "HASH_VERIFIED_V21_CREATIVE_PREVIEW",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--preview", type=Path, required=True)
    p.add_argument("--preview-report", type=Path, required=True)
    p.add_argument("--narration", type=Path, required=True)
    p.add_argument("--voice-profile", type=Path, required=True)
    p.add_argument("--music", type=Path, required=True)
    p.add_argument("--music-candidate", type=Path, required=True)
    p.add_argument("--effects-manifest", type=Path, required=True)
    p.add_argument("--sfx", action="append", default=[], help="sfx:name=/path/to/verified-pretimed.wav")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mix-output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        effects: dict[str, Path] = {}
        for raw in args.sfx:
            role, path = raw.split("=", 1)
            if role in effects or not role.startswith("sfx:"):
                raise FinalRenderError("SFX roles must be distinct sfx: identifiers")
            effects[role] = Path(path).resolve()
        result = run_final(
            record_path=args.record.resolve(),
            repo_root=args.repo_root.resolve(),
            preview=args.preview.resolve(), preview_report=args.preview_report.resolve(),
            narration=args.narration.resolve(), voice_profile=args.voice_profile.resolve(),
            music=args.music.resolve(), music_candidate=args.music_candidate.resolve(),
            effects_manifest=args.effects_manifest.resolve(), sfx=effects,
            output=args.output.resolve(), mix_output=args.mix_output.resolve(),
            receipt=args.receipt.resolve(), report=args.report.resolve(),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError,
            FinalRenderError) as exc:
        print(json.dumps({
            "status": "V21_FINAL_RENDER_BLOCKED", "render": "NOT_APPROVED",
            "drive_write": "NOT_RUN", "publication": "MANUAL_ONLY_NOT_RUN",
            "failure": str(exc),
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
