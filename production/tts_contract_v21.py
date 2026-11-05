"""Offline TTS contract gate for the V2.1 canonical path."""
from __future__ import annotations
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from production.gemini_tts import DEFAULT_MODEL, MAX_NARRATION_SECONDS, MIN_NARRATION_SECONDS, PROVIDER, VOICE_NAME

SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
POLICY_PATH = Path(__file__).resolve().parent / "active_engine_policy.json"

def validate_tts_contract(record: Mapping[str, Any], policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    failures: list[str] = []
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"gate": "TTS_CONTRACT", "status": "BLOCKED", "failures": [f"active policy unavailable:{exc}"], "execution": "NOT_RUN", "real_call": "NOT_RUN"}

    voice_policy = policy.get("voice_policy") if isinstance(policy.get("voice_policy"), Mapping) else {}
    contract = record.get("tts_contract")
    if not isinstance(contract, Mapping):
        failures.append("tts_contract is required")
        contract = {}

    expected = {
        "provider": policy.get("voice_provider", PROVIDER),
        "voice_name": voice_policy.get("voice_name", VOICE_NAME),
        "language_code": voice_policy.get("language_code", "en-US"),
        "model": voice_policy.get("model", DEFAULT_MODEL),
        "provider_fallback": voice_policy.get("provider_fallback", "forbidden"),
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            failures.append(f"tts_contract.{field} must equal {value}")

    if contract.get("status") != "OFFLINE_CONTRACT_VERIFIED":
        failures.append("tts_contract.status must be OFFLINE_CONTRACT_VERIFIED")
    if contract.get("real_call_authorized") is not False:
        failures.append("real TTS call must remain unauthorized in this stage")
    if contract.get("request_count", 0) != 0:
        failures.append("offline contract cannot report a real request")
    if contract.get("script_sha256") and not SHA256.fullmatch(str(contract["script_sha256"])):
        failures.append("tts_contract.script_sha256 must be a SHA-256")
    characters = contract.get("estimated_characters")
    if not isinstance(characters, int) or isinstance(characters, bool) or characters <= 0:
        failures.append("tts_contract.estimated_characters must be a positive integer")
    max_characters = int(contract.get("character_budget", 10000))
    if isinstance(characters, int) and characters > max_characters:
        failures.append("estimated narration exceeds the declared character budget")
    duration = contract.get("estimated_duration_seconds")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool):
        failures.append("tts_contract.estimated_duration_seconds is required")
    elif not MIN_NARRATION_SECONDS <= float(duration) <= 80.0:
        failures.append("estimated narration duration must be between 60 and 80 seconds")

    return {
        "gate": "TTS_CONTRACT",
        "status": "PASS" if not failures else "BLOCKED",
        "failures": failures,
        "execution": "OFFLINE_CONTRACT_VERIFIED" if not failures else "BLOCKED",
        "real_call": "NOT_RUN",
        "provider": expected["provider"],
        "voice": expected["voice_name"],
    }
