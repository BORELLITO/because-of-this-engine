"""Offline-only Chirp 3 HD Charon request contract for a future Cloud TTS migration.

No HTTP client, credential reader, TTS call, fallback, cache write or production
activation is included. Until reviewed, Gemini Charon remains the original
approved provider of the V7.4 branch; this module is a *candidate* only.
"""
from __future__ import annotations
import hashlib
import json
import re

PROVIDER = "google_cloud_tts"
VOICE_NAME = "en-US-Chirp3-HD-Charon"
LANGUAGE_CODE = "en-US"
MAX_TEXT_BYTES = 4800  # conservative bound below Cloud TTS request size limits


class Chirp3ContractError(ValueError):
    pass


def build_request(text: str) -> dict:
    """Build documented synchronous REST shape without making any network call.

    SSML, markup, pitch and rate are deliberately *not* injected: the provider's
    evolving Chirp3-HD feature matrix must be verified with a controlled API test
    before using optional controls. An unrecognized tag is rejected, never
    silently reinterpreted as ordinary narrative speech.
    """
    if not isinstance(text, str):
        raise Chirp3ContractError("Text must be a str")
    normalized = text.strip()
    if not normalized:
        raise Chirp3ContractError("Text cannot be blank")
    if "\x00" in normalized or re.search(r"<\s*[/a-zA-Z]", normalized):
        raise Chirp3ContractError("Only plain narration text is supported in this unactivated candidate")
    if len(normalized.encode("utf-8")) > MAX_TEXT_BYTES:
        raise Chirp3ContractError("Text too large for offline candidate request")
    return {
        "input": {"text": normalized},
        "voice": {"languageCode": LANGUAGE_CODE, "name": VOICE_NAME},
        "audioConfig": {"audioEncoding": "LINEAR16"},
    }


def offline_receipt(text: str) -> dict:
    request = build_request(text)
    canonical = json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {
        "status": "STATIC_CONTRACT_ONLY",
        "ready_for_real_tts": False,
        "requires_explicit_paid_test_approval": True,
        "voice_name": VOICE_NAME,
        "provider": PROVIDER,
        "request_sha256": hashlib.sha256(canonical).hexdigest(),
        "api_was_called": False,
        "audio_generated": False,
        "note": "Live API/quota, commercial terms, pacing, prosody and audio compatibility remain unverified.",
    }
