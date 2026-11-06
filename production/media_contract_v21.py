"""Read-only audio, captions, render and Drive contracts for V2.1."""
from __future__ import annotations
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)

ADAPTERS = {
    "audio_contract.adapter": ("production/gemini_tts.py", "synthesize_chunks"),
    "captions_contract.adapter": ("production/align_captions.py", "main"),
    "render_contract.adapter": ("production/render_v21_manual.py", "main"),
    "drive_contract.assets_adapter": ("production/google_drive_assets.py", "main"),
    "drive_contract.delivery_adapter": ("production/google_drive_delivery.py", "main"),
}

def validate_adapter_wiring(record: Mapping[str, Any], repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[1]
    failures: list[str] = []
    for field, (relative_path, symbol) in ADAPTERS.items():
        parts = field.split(".")
        value: Any = record
        for part in parts:
            value = value.get(part) if isinstance(value, Mapping) else None
        if value != relative_path:
            failures.append(f"{field} must equal {relative_path}")
            continue
        path = root / relative_path
        if not path.is_file():
            failures.append(f"adapter file does not exist:{relative_path}")
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"adapter cannot be read:{relative_path}:{exc}")
            continue
        if f"def {symbol}" not in source:
            failures.append(f"adapter symbol missing:{relative_path}:{symbol}")
    return _result("ADAPTER_WIRING", failures, execution="STATIC_WIRING_VERIFIED" if not failures else "BLOCKED")


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
    source_status = contract.get("source_audio_status")
    if source_hash is None:
        if source_status != "PENDING_GEMINI_GENERATION" or contract.get("real_caption_generated") is not False:
            failures.append("captions_contract may omit source_audio_sha256 only while Gemini audio is pending")
    elif not SHA256.fullmatch(str(source_hash)):
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