#!/usr/bin/env python3
"""Optional free WhisperX forced-alignment evaluator; DOES NOT replace V7 Vosk.

Requires opt-in local install of the BSD-2-Clause WhisperX library and optional
model weights, whose licenses and compute requirements must be checked separately.
Outputs a candidate JSON only; cannot write canonical ASS captions.
"""
from __future__ import annotations

import argparse
import json
import re
import wave
from pathlib import Path
from typing import Any

class CandidateAlignmentError(ValueError):
    pass

def tokens(text: str) -> list[str]:
    return [w.lower().replace("’", "'") for w in re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", text)]

def validate_candidate(script: str, words: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    if not isinstance(words, list) or not words:
        raise CandidateAlignmentError("No word timestamps supplied")
    if duration <= 0:
        raise CandidateAlignmentError("Audio duration is not positive")
    expected = tokens(script)
    observed: list[str] = []
    checked: list[dict[str, Any]] = []
    end_previous = 0.0
    for item in words:
        if not isinstance(item, dict):
            raise CandidateAlignmentError("Word item must be a dict")
        literal = str(item.get("word") or "").strip()
        subtokens = tokens(literal)
        if len(subtokens) != 1:
            raise CandidateAlignmentError("Each candidate must contain one spoken word")
        try:
            start, end = float(item["start"]), float(item["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CandidateAlignmentError("Word has no real timestamp") from exc
        if not (end_previous <= start < end <= duration + 0.02):
            raise CandidateAlignmentError("Overlapping, inverted or out-of-bounds timestamps")
        end_previous = end
        observed.append(subtokens[0])
        checked.append({"word": literal, "start": round(start, 3), "end": round(end, 3)})
    if expected != observed:
        raise CandidateAlignmentError(
            f"Canonical script differs from spoken word alignment: expected {len(expected)} tokens, got {len(observed)}"
        )
    return {
        "status": "CANDIDATE_ONLY",
        "provider": "WhisperX",
        "word_count": len(checked),
        "words": checked,
        "audio_duration_seconds": round(duration, 3),
        "canonical_captions_modified": False,
        "human_audio_audit_required": True,
    }

def evaluate(wav_path: Path, script_path: Path, device: str = "cpu") -> dict[str, Any]:
    try:
        import whisperx
    except ImportError as exc:
        raise CandidateAlignmentError("WhisperX is optional; install explicitly in isolated environment") from exc
    script = script_path.read_text(encoding="utf-8").strip()
    with wave.open(str(wav_path), "rb") as wav:
        duration = wav.getnframes() / wav.getframerate()
    audio = whisperx.load_audio(str(wav_path))
    model, metadata = whisperx.load_align_model(language_code="en", device=device)
    result = whisperx.align([{"start": 0.0, "end": duration, "text": script}],
                             model, metadata, audio, device, return_char_alignments=False)
    return validate_candidate(script, result.get("word_segments", []), duration)

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wav", required=True, type=Path)
    ap.add_argument("--script", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = ap.parse_args()
    try:
        result = evaluate(args.wav, args.script, args.device)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WHISPERX_CANDIDATE_PASS: {result['word_count']} words; V7 captions unchanged")
        return 0
    except (OSError, CandidateAlignmentError, KeyError, ValueError, RuntimeError) as exc:
        print("WHISPERX_CANDIDATE_BLOCKED: " + str(exc))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
