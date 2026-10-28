#!/usr/bin/env python3
"""Detect technically suspicious black, frozen or silent sections in a render."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from typing import Any

class MediaAnomalyError(RuntimeError):
    """Raised when anomaly analysis cannot be completed."""

BLACK_BLOCK_SECONDS = 2.0
BLACK_PIXEL_THRESHOLD = 0.03
FREEZE_ADVISORY_SECONDS = 3.0
SILENCE_ADVISORY_SECONDS = 3.0

def _value(line: str, key: str) -> float | None:
    match = re.search(rf"\b{re.escape(key)}:([0-9]+(?:\.[0-9]+)?)", line)
    return float(match.group(1)) if match else None

def parse_filter_log(log: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    active_silence: float | None = None
    for line in log.splitlines():
        if "black_duration:" in line:
            duration = _value(line, "black_duration")
            if duration is not None and duration >= BLACK_BLOCK_SECONDS:
                findings.append({"type": "black", "start": _value(line, "black_start"),
                    "end": _value(line, "black_end"), "duration_seconds": round(duration, 3),
                    "severity": "BLOCKING",
                    "reason": "Unexpected continuous black exceeds the transition budget."})
        if "freeze_duration:" in line:
            duration = _value(line, "freeze_duration")
            if duration is not None and duration >= FREEZE_ADVISORY_SECONDS:
                findings.append({"type": "freeze", "start": _value(line, "freeze_start"),
                    "end": _value(line, "freeze_end"), "duration_seconds": round(duration, 3),
                    "severity": "ADVISORY",
                    "reason": "A long frozen section may indicate an accidental stalled frame."})
        if "silence_start:" in line and "silence_end:" not in line:
            active_silence = _value(line, "silence_start")
        if "silence_duration:" in line:
            duration = _value(line, "silence_duration")
            if duration is not None and duration >= SILENCE_ADVISORY_SECONDS:
                findings.append({"type": "silence", "start": active_silence,
                    "end": _value(line, "silence_end"), "duration_seconds": round(duration, 3),
                    "severity": "ADVISORY",
                    "reason": "A long silent section may reduce narration intelligibility or continuity."})
            active_silence = None
    return findings

def analyze(path: Path, *, timeout: int = 240) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise MediaAnomalyError(f"Rendered media is missing or empty: {path}")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", str(path),
        "-vf", f"blackdetect=d=2:pix_th={BLACK_PIXEL_THRESHOLD:.2f},freezedetect=n=-60dB:d=3",
        "-af", "silencedetect=n=-45dB:d=3", "-f", "null", "-"]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise MediaAnomalyError(f"Could not run media anomaly scan: {detail[-1600:]}") from exc
    findings = parse_filter_log(result.stderr)
    blocking = [item for item in findings if item["severity"] == "BLOCKING"]
    return {"status": "BLOCKED" if blocking else ("ADVISORY" if findings else "PASS"),
        "tool": "ffmpeg blackdetect/freezedetect/silencedetect",
        "thresholds": {"black_block_seconds": BLACK_BLOCK_SECONDS,
            "black_pixel_threshold": BLACK_PIXEL_THRESHOLD,
            "freeze_advisory_seconds": FREEZE_ADVISORY_SECONDS,
            "silence_advisory_seconds": SILENCE_ADVISORY_SECONDS},
        "findings": findings, "blocking_findings": len(blocking)}
