#!/usr/bin/env python3
"""Align captions from Microsoft Edge TTS native WordBoundary timestamps."""

from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path
from typing import Any

from production.align_captions import (
    AlignmentError,
    _align_chunks,
    _normalize_sidecar_word_timeline,
    _write_ass,
)
from production.generate_phrase_captions import phrase_chunks


def _load_boundaries(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AlignmentError(f"Could not read Edge word-boundary sidecar: {path}") from exc
    if data.get("status") != "EDGE_TTS_WORD_BOUNDARIES":
        raise AlignmentError("Edge word-boundary sidecar has an invalid status")
    words: list[dict[str, Any]] = []
    for item in data.get("words", []):
        text = str(item.get("text", "")).strip()
        if not text or any(char.isspace() for char in text):
            raise AlignmentError(f"Edge word boundary is not a single word: {text!r}")
        start = float(item.get("start_seconds", -1))
        end = float(item.get("end_seconds", -1))
        if start < 0 or end <= start:
            raise AlignmentError(f"Edge word boundary has an invalid interval: {item!r}")
        words.append({
            "word": text,
            "start": start,
            "end": end,
            "confidence": 1.0,
            "timestamp_source": "edge_tts_word_boundary",
        })
    if not words:
        raise AlignmentError("Edge TTS returned no word boundaries")
    return words


def generate(manifest_path: Path, boundary_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_path = (base / manifest["audio"]["path"]).resolve()
    caption_config = manifest.get("captions") or {}
    caption_path = (base / caption_config["path"]).resolve()
    sidecar_path = (base / caption_config.get(
        "alignment_sidecar", "captions/narration.alignment.json"
    )).resolve()

    with wave.open(str(audio_path), "rb") as audio:
        audio_seconds = audio.getnframes() / audio.getframerate()
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 24000:
            raise AlignmentError("Narration must be mono 24 kHz 16-bit PCM WAV.")

    script = (base / manifest["script"]["path"]).read_text(encoding="utf-8").strip()
    chunks = phrase_chunks(script, max_line_chars=int(caption_config.get("max_line_chars", 42)))
    native_words = _load_boundaries(boundary_path.resolve())
    events, sidecar_chunks = _align_chunks(chunks, native_words)
    overlap_count = _normalize_sidecar_word_timeline(sidecar_chunks, audio_seconds)

    events = [
        {
            "start": chunk["words"][0]["start"],
            "end": chunk["words"][-1]["end"],
            "text": chunk["text"],
        }
        for chunk in sidecar_chunks
    ]
    events[0]["start"] = 0.0
    for previous, current in zip(events, events[1:]):
        if float(current["start"]) < float(previous["end"]):
            previous["end"] = float(current["start"])

    safe_ass_end = int(audio_seconds * 100) / 100.0
    if safe_ass_end <= float(events[-1]["start"]):
        raise AlignmentError("Narration is too short to close the final caption at ASS precision.")
    events[-1]["end"] = safe_ass_end
    for event in events:
        if event["end"] - event["start"] < 0.08:
            raise AlignmentError("Native Edge caption phrase became too short.")
        event["start"] = round(max(0.0, event["start"]), 3)
        event["end"] = round(min(audio_seconds, event["end"]), 3)

    active_word_color = str(caption_config.get("active_word_color", "#FF7777"))
    _write_ass(caption_path, events, sidecar_chunks, active_word_color)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps({
        "status": "EDGE_TTS_NATIVE_ALIGNMENT_PASS",
        "provider": "Microsoft Edge TTS",
        "timing_mode": "edge_tts_native_word_boundaries",
        "audio_duration_seconds": round(audio_seconds, 3),
        "word_count": len(native_words),
        "words": native_words,
        "captions": sidecar_chunks,
        "word_timing_normalization": {
            "overlap_boundaries_closed": overlap_count,
            "timeline_monotonic": True,
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "EDGE_TTS_NATIVE_CAPTIONS_GENERATED",
        "caption_path": str(caption_path),
        "alignment_sidecar": str(sidecar_path),
        "duration_seconds": round(audio_seconds, 3),
        "event_count": len(events),
        "recognized_words": len(native_words),
        "word_highlight_mode": "timestamp_color_transform",
        "active_word_color": active_word_color,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--word-boundaries", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.manifest, args.word_boundaries), ensure_ascii=False))
        return 0
    except (AlignmentError, OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"EDGE NATIVE CAPTION ALIGNMENT BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
