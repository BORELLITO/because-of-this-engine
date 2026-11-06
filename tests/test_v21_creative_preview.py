from __future__ import annotations

import hashlib
import json
import tempfile
import wave
from pathlib import Path

from production.render_v21_preview import PreviewRenderError, validate_voice_profile
import production.render_v21_preview as preview_renderer


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x00\x00" * 24000)


def _profile(audio: Path) -> dict:
    return {
        "provider": "gemini_tts",
        "voice_name": "Charon",
        "model": "gemini-3.8-flash-tts",
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
        assert validate_voice_profile(profile, audio)["voice_name"] == "Charon"


def test_creative_preview_rejects_edge_voice_profile() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        audio = root / "narration.wav"
        _write_wav(audio)
        data = _profile(audio)
        data["provider"] = "microsoft_edge_tts"
        data["voice_name"] = "en-US-ChristopherNeural"
        profile = root / "voice-profile.json"
        profile.write_text(json.dumps(data), encoding="utf-8")
        try:
            validate_voice_profile(profile, audio)
        except PreviewRenderError as exc:
            assert "Voice identity mismatch" in str(exc)
        else:
            raise AssertionError("Edge TTS must not pass the creative preview gate")


def test_creative_preview_splits_voice_before_sidechain_mix() -> None:
    source = Path(preview_renderer.__file__).read_text(encoding="utf-8")
    assert "asplit=2[voice_mix][voice_key]" in source
    assert "[bed][voice_key]sidechaincompress" in source
    assert "[voice_mix][ducked]amix" in source
