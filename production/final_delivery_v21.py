"""Mandatory fail-closed V2.1 final-video delivery gate.

All MP4/MOV/MKV/WEBM/AVI/M4V deliveries through the canonical Drive adapter
must pass production-policy authorization, real independently replayed audio mix,
per-stem contribution evidence, final-master binding and media format checks.

Never uploads, renders, calls TTS, or publishes. Non-video backups remain
independent; the Episode 005 narration-only GitHub creative preview is separate.
"""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
EXPECTED_RENDER = {"width": 1080, "height": 1920, "fps": 60}
MAX_DURATION_SECONDS = 80.0
MIN_DURATION_SECONDS = 60.0
EXPECTED_VOICE = ("gemini_tts", "Charon")


def _read(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise ValueError("mandatory production record/policy path is missing")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON document must contain an object")
    return data


def collect_media(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for source in paths:
        path = Path(source)
        if not path.exists():
            raise ValueError(f"delivery source unavailable:{path}")
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = [x for x in path.rglob("*") if x.is_file()]
        else:
            raise ValueError("invalid delivery source type")
        found.extend(x.resolve() for x in files if x.suffix.lower() in VIDEO_EXTENSIONS)
    return found


def _probe_final_video(path: Path) -> dict[str, Any]:
    run = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries",
         "stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate:format=duration",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=35,
    )
    obj = json.loads(run.stdout)
    streams = obj.get("streams") or []
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if len(video) != 1 or len(audio) != 1:
        raise ValueError("exactly one final video and audio stream required")
    v, a = video[0], audio[0]
    fps = Fraction(str(v.get("avg_frame_rate") or "0"))
    duration = float((obj.get("format") or {}).get("duration") or 0)
    if (int(v.get("width") or 0), int(v.get("height") or 0)) != (1080, 1920):
        raise ValueError("final frame geometry must be 1080x1920")
    if abs(float(fps) - 60.0) > 0.01:
        raise ValueError("final video must have 60fps average frame rate")
    if v.get("codec_name") != "h264":
        raise ValueError("final video codec must be h264")
    if a.get("codec_name") != "aac" or int(a.get("sample_rate") or 0) != 48000:
        raise ValueError("final audio codec/rate must be AAC 48kHz")
    if not MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS:
        raise ValueError("final video duration must be 60–80 seconds")
    return {"width": 1080, "height": 1920, "fps": 60,
            "duration_seconds": round(duration, 3),
            "video_codec": "h264", "audio_codec": "aac"}


def verify_drive_video_delivery(
    paths: list[Path],
    *,
    production_record_path: Path | None = None,
    audio_receipt_path: Path | None = None,
    master_video_path: Path | None = None,
    repo_root: Path | None = None,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    """Validate BEFORE constructing a Drive client or writing any remote bytes.

    Proofs must be derived from the same episode and exact media bytes.  A
    human's story approval alone never changes production enablement.
    """
    failures: list[str] = []
    try:
        videos = collect_media(paths)
    except (OSError, ValueError) as exc:
        return {"gate": "FINAL_VIDEO_DELIVERY_V21", "status": "BLOCKED",
                "failures": [str(exc)], "remote_write": "NOT_RUN"}

    if not videos:
        return {"gate": "FINAL_VIDEO_DELIVERY_V21",
                "status": "NON_VIDEO_BACKUP_ONLY",
                "video_count": 0, "remote_write": "NOT_RUN",
                "publication_authorized": False,
                "note": "This gate covers media video payloads; no final video passed."}

    if len(videos) != 1 or len(set(videos)) != 1:
        failures.append("exactly one distinct finished master video per delivery is required")
    if not master_video_path:
        failures.append("explicit final master path is required")
        master = None
    else:
        master = Path(master_video_path).resolve()
        if videos != [master]:
            failures.append("delivered video must be the exact verified master path")
    root = (repo_root or Path(".")).resolve()
    try:
        policy = _read(policy_path or (root / "production/active_engine_policy.json"))
        record = _read(production_record_path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        policy, record = {}, {}
        failures.append("required policy and production record unavailable: " + str(exc))

    if policy.get("active_engine_version") != "2.1":
        failures.append("active engine is not canonical V2.1")
    if policy.get("canonical_entrypoint") != "production/canonical_entrypoint.py":
        failures.append("canonical engine entrypoint changed")
    if policy.get("voice_provider") != EXPECTED_VOICE[0] or (
            policy.get("voice_policy") or {}).get("voice_name") != EXPECTED_VOICE[1]:
        failures.append("approved Charon voice identity differs")
    if policy.get("publication_policy") != "manual_only":
        failures.append("publication must remain manual")
    if policy.get("production_enablement") is not True:
        failures.append("policy production_enablement=false")
    if policy.get("final_drive_delivery_enablement") is not True:
        failures.append("final_drive_delivery_enablement is not authorized")

    if record.get("production_enablement") is not True:
        failures.append("episode production_enablement=false")
    if not str(record.get("episode_id") or "").strip():
        failures.append("record episode_id required")
    if (record.get("render_authorization") or {}).get("status") != "APPROVED":
        failures.append("render authorization missing")
    contract = record.get("render_contract") or {}
    if any(contract.get(k) != v for k, v in EXPECTED_RENDER.items()):
        failures.append("render identity does not match 1080x1920@60")
    if contract.get("render_executed") is not True:
        failures.append("real completed final render has not been recorded")
    voice = record.get("tts_contract") or {}
    if voice.get("provider") != EXPECTED_VOICE[0] or voice.get("voice_name") != EXPECTED_VOICE[1]:
        failures.append("episode narration must be canonical Gemini/Charon")

    # Independent episode-specific evidence still applies: passing a mix receipt
    # must not launder missing rights, historical SFX, or truthful visual labels.
    try:
        from production.audio_history_audit_v21 import audit as audio_history_audit
        from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
        from production.scene_disclosures_v21 import audit_repository as scene_disclosures
        from production.rights_autonomy_v21 import audit_repository as autonomous_rights
        for name, report in (
            ("audio_history", audio_history_audit(root)),
            ("visual_rights", validate_visual_rights_consistency(record, repo_root=root)),
            ("scene_disclosures", scene_disclosures(record, repo_root=root)),
            ("autonomous_rights", autonomous_rights(record, repo_root=root)),
        ):
            if report.get("status") != "PASS":
                failures.append(name + ": original safety gate blocked")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        failures.append("independent V2.1 safety gates unavailable: " + str(exc))

    if master is not None and master.is_file():
        try:
            _probe_final_video(master)
        except (OSError, ValueError, TypeError, ZeroDivisionError,
                subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            failures.append("final media ffprobe validation failed: " + str(exc))
    else:
        failures.append("verified master bytes are not present")

    if audio_receipt_path is None:
        failures.append("verified original audio mix receipt is required")
    elif master is not None and master.is_file():
        try:
            from production.render_v21_manual import validate_completed_audio_mix
            audio = validate_completed_audio_mix(
                record, receipt_path=Path(audio_receipt_path), master_video=master)
            if audio.get("status") != "V21_AUDIO_POSTFLIGHT_EVIDENCE_PASS":
                failures.append("independent audio mix replay, per-stem contribution or master binding failed")
            elif "narration" not in audio.get("source_contributions_confirmed", []) or (
                    "music" not in audio.get("source_contributions_confirmed", [])):
                failures.append("narration or music was not detected in the final mix")
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            failures.append("audio postflight evidence unavailable: " + str(exc))

    return {
        "gate": "FINAL_VIDEO_DELIVERY_V21",
        "status": "PASS" if not failures else "BLOCKED",
        "failures": failures,
        "video_count": len(videos),
        "remote_write": "NOT_RUN",
        "publication_authorized": False,
        "mode": "FINAL_MASTER_ONLY",
        "release_ready": not failures,
        "note": "PASS only authorizes controlled Drive transfer; platform publication remains manual.",
    }
