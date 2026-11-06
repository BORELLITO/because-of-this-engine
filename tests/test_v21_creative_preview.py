from __future__ import annotations

import hashlib
import json
import tempfile
import wave
from pathlib import Path

from production.render_v21_preview import PreviewRenderError, build_scene_plan, validate_voice_profile


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x00\x00" * 24000)


def _profile(audio: Path) -> dict:
    return {
        "provider": "creativeclaw_google_gemini",
        "voice_id": "charon",
        "model": "speech/gemini-3.8-flash-tts",
        "identity_status": "APPROVED_REFERENCE_MATCH",
        "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
    }


def test_creative_preview_requires_approved_charon_identity() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        audio = root / "narration.wav"
        _write_wav(audio)
        profile = root / "voice-profile.json"
        profile.write_text(json.dumps(_profile(audio)), encoding="utf-8")
        assert validate_voice_profile(profile, audio)["voice_id"] == "charon"


def test_creative_preview_rejects_edge_voice_profile() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        audio = root / "narration.wav"
        _write_wav(audio)
        data = _profile(audio)
        data["provider"] = "microsoft_edge_tts"
        data["voice_id"] = "en-US-ChristopherNeural"
        profile = root / "voice-profile.json"
        profile.write_text(json.dumps(data), encoding="utf-8")
        try:
            validate_voice_profile(profile, audio)
        except PreviewRenderError as exc:
            assert "Voice identity mismatch" in str(exc)
        else:
            raise AssertionError("Edge TTS must not pass the creative preview gate")


def test_scene_plan_scales_to_final_audio_duration() -> None:
    ranges = [
        "00:00-00:04", "00:04-00:09", "00:09-00:14", "00:14-00:18",
        "00:18-00:23", "00:23-00:27", "00:27-00:32", "00:32-00:37",
        "00:37-00:41", "00:41-00:46", "00:46-00:51", "00:51-00:56",
        "00:56-01:01", "01:01-01:06", "01:06-01:12", "01:12-01:18",
    ]
    story = {
        "shot_plan": [
            {"shot_id": f"S{index:02d}", "range": value, "role": "test"}
            for index, value in enumerate(ranges, start=1)
        ]
    }
    manifest = {
        "assets": [
            {"candidate_id": f"asset-{index:02d}"}
            for index in range(1, 17)
        ],
        "shot_assignments": [
            {
                "shot_id": f"S{index:02d}",
                "assignment": {"candidate_id": f"asset-{index:02d}"},
            }
            for index in range(1, 17)
        ],
    }

    plan = build_scene_plan(manifest, story, target_duration=70.0)

    assert len(plan) == 16
    assert len({item["candidate_id"] for item in plan}) == 16
    assert round(sum(float(item["duration"]) for item in plan), 3) == 70.0
    assert plan[0]["timeline_source_duration"] == 4
    assert plan[-1]["duration"] > 0
