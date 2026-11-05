"""Read-only audio, captions, render and Drive contracts for V2.1."""
from __future__ import annotations
import re
from collections.abc import Mapping
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)

def _result(gate: str, failures: list[str], **extra: Any) -> dict[str, Any]:
    return {"gate": gate, "status": "PASS" if not failures else "BLOCKED", "failures": failures, **extra}

def validate_audio_contract(record: Mapping[str, Any]) -> dict[str, Any]:
    contract = record.get("audio_contract")
    failures: list[str] = []
    if not isinstance(contract, Mapping):
        return _result("AUDIO_MIX", ["audio_contract is required"], execution="NOT_RUN")
    expected = {
        "source": "final_audio",
        "status": "OFFLINE_CONTRACT_VERIFIED",
        "real_audio_generated": False,
        "final_transcription_required": True,
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            failures.append(f"audio_contract.{field} must equal {value}")
    duration = contract.get("target_duration_seconds")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not 60 <= float(duration) <= 80:
        failures.append("audio_contract.target_duration_seconds must be between 60 and 80")
    return _result("AUDIO_MIX", failures, execution="OFFLINE_CONTRACT_VERIFIED" if not failures else "BLOCKED", real_audio="NOT_RUN")

def validate_captions_contract(record: Mapping[str, Any]) -> dict[str, Any]:
    contract = record.get("captions_contract")
    failures: list[str] = []
    if not isinstance(contract, Mapping):
        return _result("CAPTIONS", ["captions_contract is required"], execution="NOT_RUN")
    expected = {
        "source": "final_audio_transcription",
        "word_level": True,
        "status": "OFFLINE_CONTRACT_VERIFIED",
        "real_caption_generated": False,
        "safe_zone_status": "PENDING_REAL_CAPTURE",
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            failures.append(f"captions_contract.{field} must equal {value}")
    source_hash = contract.get("source_audio_sha256")
    if not SHA256.fullmatch(str(source_hash or "")):
        failures.append("captions_contract.source_audio_sha256 must be a SHA-256")
    return _result("CAPTIONS", failures, execution="OFFLINE_CONTRACT_VERIFIED" if not failures else "BLOCKED", real_captions="NOT_RUN")

def validate_render_contract(record: Mapping[str, Any]) -> dict[str, Any]:
    contract = record.get("render_contract")
    failures: list[str] = []
    if not isinstance(contract, Mapping):
        return _result("VISUAL_ASSEMBLY", ["render_contract is required"], execution="NOT_RUN")
    expected = {
        "width": 1080,
        "height": 1920,
        "fps": 60,
        "status": "OFFLINE_CONTRACT_VERIFIED",
        "render_executed": False,
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            failures.append(f"render_contract.{field} must equal {value}")
    duration = contract.get("duration_target_seconds")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not 60 <= float(duration) <= 80:
        failures.append("render_contract.duration_target_seconds must be between 60 and 80")
    return _result("VISUAL_ASSEMBLY", failures, execution="OFFLINE_CONTRACT_VERIFIED" if not failures else "BLOCKED", render="NOT_RUN")

def validate_drive_contract(record: Mapping[str, Any]) -> dict[str, Any]:
    contract = record.get("drive_contract")
    failures: list[str] = []
    if not isinstance(contract, Mapping):
        return _result("DRIVE_DELIVERY", ["drive_contract is required"], execution="NOT_RUN")
    expected = {
        "mode": "read_only",
        "write_authorized": False,
        "status": "OFFLINE_CONTRACT_VERIFIED",
        "receipt_status": "NOT_RUN",
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            failures.append(f"drive_contract.{field} must equal {value}")
    return _result("DRIVE_DELIVERY", failures, execution="OFFLINE_CONTRACT_VERIFIED" if not failures else "BLOCKED", drive_write="NOT_RUN")
