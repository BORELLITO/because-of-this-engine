#!/usr/bin/env python3
"""Forced-align captions with local Whisper word timestamps."""

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


def _recognize(audio_path: Path, model_name: str) -> list[dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise AlignmentError("faster-whisper is required for local forced alignment") from exc
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(
            str(audio_path),
            language="en",
            task="transcribe",
            word_timestamps=True,
            vad_filter=False,
            beam_size=5,
            condition_on_previous_text=False,
        )
        words: list[dict[str, Any]] = []
        for segment in segments:
            for item in segment.words or []:
                text = str(item.word or "").strip()
                if not text:
                    continue
                words.append({
                    "word": text,
                    "start": float(item.start),
                    "end": float(item.end),
                    "confidence": float(getattr(item, "probability", 1.0)),
                    "timestamp_source": "faster_whisper_word_timestamp",
                })
    except Exception as exc:
        raise AlignmentError(f"Whisper recognition failed: {exc}") from exc
    if not words:
        raise AlignmentError("Whisper returned no word timestamps")
    return words


def generate(manifest_path: Path, model_name: str) -> dict[str, Any]:
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
    words = _recognize(audio_path, model_name)
    try:
        events, sidecar_chunks = _align_chunks(chunks, words)
    except AlignmentError as first_error:
        try:
            events, sidecar_chunks = _align_chunks(chunks, words, recover_missing=True)
        except AlignmentError as recovery_error:
            raise AlignmentError(
                f"{first_error} Bounded function-word recovery also failed: {recovery_error}"
            ) from recovery_error

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
            raise AlignmentError("Whisper caption phrase became too short.")
        event["start"] = round(max(0.0, event["start"]), 3)
        event["end"] = round(min(audio_seconds, event["end"]), 3)

    active_word_color = str(caption_config.get("active_word_color", "#FF7777"))
    _write_ass(caption_path, events, sidecar_chunks, active_word_color)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps({
        "status": "WHISPER_FORCED_ALIGNMENT_PASS",
        "provider": "faster-whisper",
        "model": model_name,
        "timing_mode": "whisper_word_timestamps",
        "audio_duration_seconds": round(audio_seconds, 3),
        "word_count": len(words),
        "words": words,
        "captions": sidecar_chunks,
        "word_timing_normalization": {
            "overlap_boundaries_closed": overlap_count,
            "timeline_monotonic": True,
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "WHISPER_FORCED_CAPTIONS_GENERATED",
        "caption_path": str(caption_path),
        "alignment_sidecar": str(sidecar_path),
        "duration_seconds": round(audio_seconds, 3),
        "event_count": len(events),
        "recognized_words": len(words),
        "word_highlight_mode": "timestamp_color_transform",
        "active_word_color": active_word_color,
        "model": model_name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", default="tiny.en")
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.manifest, args.model), ensure_ascii=False))
        return 0
    except (AlignmentError, OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"WHISPER CAPTION ALIGNMENT BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
