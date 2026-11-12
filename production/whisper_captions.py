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
    _align_chunk,
    _align_chunks,
    _normalize_sidecar_word_timeline,
    _write_ass,
)
from production.align_edge_captions import _load_boundaries
from production.generate_phrase_captions import phrase_chunks
from production.caption_style_v21 import default_active_word_color


def _load_audio(audio_path: Path) -> tuple[Any, int, float]:
    try:
        import numpy as np

        with wave.open(str(audio_path), "rb") as audio:
            sample_rate = audio.getframerate()
            frame_count = audio.getnframes()
            pcm = audio.readframes(frame_count)
        waveform = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        return waveform, sample_rate, frame_count / sample_rate
    except Exception as exc:
        raise AlignmentError(f"Could not read narration PCM: {audio_path}: {exc}") from exc


def _model(model_name: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise AlignmentError("faster-whisper is required for local forced alignment") from exc
    try:
        return WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception as exc:
        raise AlignmentError(f"Whisper model could not be loaded: {exc}") from exc


def _recognize_waveform(
    model: Any,
    waveform: Any,
    sample_rate: int,
    offset_seconds: float = 0.0,
    initial_prompt: str | None = None,
) -> list[dict[str, Any]]:
    # faster-whisper consumes PCM arrays on a 16 kHz clock. The production
    # narration is intentionally stored as mono 24 kHz WAV, so resample only
    # the recognition buffer while retaining offsets in the source WAV clock.
    try:
        import numpy as np

        source = np.asarray(waveform, dtype=np.float32)
        if sample_rate != 16000:
            target_length = max(1, int(round(len(source) * 16000 / sample_rate)))
            source_positions = np.linspace(0.0, 1.0, num=len(source), endpoint=False)
            target_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
            waveform = np.interp(target_positions, source_positions, source).astype(np.float32)
        else:
            waveform = source
    except Exception as exc:
        raise AlignmentError(f"Could not resample narration for Whisper: {exc}") from exc
    try:
        segments, _info = model.transcribe(
            waveform,
            language="en",
            task="transcribe",
            word_timestamps=True,
            vad_filter=False,
            beam_size=5,
            condition_on_previous_text=False,
            temperature=0.0,
            initial_prompt=initial_prompt,
        )
        words: list[dict[str, Any]] = []
        for segment in segments:
            for item in segment.words or []:
                text = str(item.word or "").strip()
                if not text:
                    continue
                start = offset_seconds + float(item.start)
                end = offset_seconds + float(item.end)
                if end - start < 0.02:
                    continue
                words.append({
                    "word": text,
                    "start": start,
                    "end": end,
                    "confidence": float(getattr(item, "probability", 1.0)),
                    "timestamp_source": "faster_whisper_phrase_window_word_timestamp",
                })
        return words
    except Exception as exc:
        raise AlignmentError(f"Whisper recognition failed: {exc}") from exc


def _recognize(audio_path: Path, model_name: str) -> list[dict[str, Any]]:
    waveform, sample_rate, _duration = _load_audio(audio_path)
    return _recognize_waveform(_model(model_name), waveform, sample_rate)


def _recognize_phrase_windows(
    audio_path: Path,
    model_name: str,
    native_chunks: list[dict[str, Any]],
    audio_seconds: float,
) -> list[dict[str, Any]]:
    waveform, sample_rate, _duration = _load_audio(audio_path)
    model = _model(model_name)
    words: list[dict[str, Any]] = []
    for chunk in native_chunks:
        native_words = chunk.get("words") or []
        if not native_words:
            raise AlignmentError("Native timing window has no words.")
        # Give Whisper acoustic context around the provider window. The
        # provider boundaries choose the phrase; padding supplies coarticulation
        # and avoids dropping short numerals/articles at the edges.
        start = max(0.0, float(native_words[0]["start"]) - 0.75)
        end = min(audio_seconds, float(native_words[-1]["end"]) + 0.75)
        start_frame = max(0, int(round(start * sample_rate)))
        end_frame = min(len(waveform), int(round(end * sample_rate)))
        if end_frame <= start_frame:
            raise AlignmentError(f"Invalid acoustic window for caption phrase {chunk.get('text')!r}.")
        window_words = _recognize_waveform(
            model,
            waveform[start_frame:end_frame],
            sample_rate,
            offset_seconds=start_frame / sample_rate,
            initial_prompt=str(chunk.get("text", "")).replace(r"\\N", " "),
        )
        words.extend(window_words)
    if not words:
        raise AlignmentError("Whisper returned no phrase-window word timestamps.")
    return words


def _advance_cursor(words: list[dict[str, Any]], cursor: int, end_time: float) -> int:
    """Move an ASR cursor past a selected real-timestamp phrase."""
    while cursor < len(words) and float(words[cursor]["end"]) <= end_time + 0.001:
        cursor += 1
    return cursor


def _align_chunks_with_vosk_fallback(
    chunks: list[str],
    whisper_words: list[dict[str, Any]],
    vosk_words: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep Whisper as authority and use Vosk only for a failed phrase.

    Each accepted word still comes from an ASR timestamp in the final WAV.
    The two recognizers are never concatenated into one global transcript,
    which avoids duplicate/interleaved timelines.
    """
    events: list[dict[str, Any]] = []
    sidecar_chunks: list[dict[str, Any]] = []
    previous_end = 0.0
    for chunk in chunks:
        # Start each phrase from the final timestamp of the preceding phrase.
        # A fallback cannot therefore carry a stale token index into the other
        # recognizer's independent transcript.
        whisper_cursor = _advance_cursor(whisper_words, 0, previous_end)
        vosk_cursor = _advance_cursor(vosk_words, 0, previous_end)
        chosen: tuple[float, float, int, list[dict[str, Any]]] | None = None
        source = "faster-whisper"
        try:
            chosen = _align_chunk(chunk, whisper_words, whisper_cursor)
        except AlignmentError:
            source = "Vosk"
            chosen = _align_chunk(chunk, vosk_words, vosk_cursor)
        start, end, next_cursor, positions = chosen
        if start < previous_end - 0.001:
            raise AlignmentError(
                f"Multi-ASR fallback produced a non-monotonic phrase for {chunk!r}."
            )
        events.append({"start": start, "end": end, "text": chunk})
        sidecar_chunks.append({"text": chunk, "words": positions, "timestamp_provider": source})
        previous_end = end
        # Cursors are recomputed from the real phrase boundary above; do not
        # transfer source-local token indexes across recognizers.
    return events, sidecar_chunks


def _bounded_words(words: list[dict[str, Any]], audio_seconds: float) -> list[dict[str, Any]]:
    bounded: list[dict[str, Any]] = []
    for word in words:
        start = max(0.0, float(word["start"]))
        end = min(audio_seconds, float(word["end"]))
        if start < audio_seconds and end - start >= 0.02:
            bounded.append({**word, "start": start, "end": end})
    if not bounded:
        raise AlignmentError("Whisper produced no timestamps inside the WAV duration")
    return bounded


def _events_from_chunks(sidecar_chunks: list[dict[str, Any]], audio_seconds: float) -> list[dict[str, Any]]:
    events = [
        {
            "start": chunk["words"][0]["start"],
            "end": chunk["words"][-1]["end"],
            "text": chunk["text"],
        }
        for chunk in sidecar_chunks
    ]
    if not events:
        raise AlignmentError("No caption events were produced.")
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
    return events


def generate(
    manifest_path: Path,
    model_name: str,
    native_boundaries_path: Path | None = None,
    secondary_vosk_model_dir: Path | None = None,
) -> dict[str, Any]:
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
    words = _bounded_words(_recognize(audio_path, model_name), audio_seconds)
    alignment_mode = "whisper_full_audio_word_timestamps"
    try:
        _events, sidecar_chunks = _align_chunks(chunks, words)
    except AlignmentError as full_error:
        if secondary_vosk_model_dir is not None:
            from production.align_captions import _recognize as recognize_vosk
            vosk_words = _bounded_words(
                recognize_vosk(audio_path, secondary_vosk_model_dir),
                audio_seconds,
            )
            try:
                _events, sidecar_chunks = _align_chunks_with_vosk_fallback(
                    chunks, words, vosk_words
                )
            except AlignmentError as vosk_error:
                raise AlignmentError(
                    f"{full_error} Phrase-scoped Vosk fallback also failed: {vosk_error}"
                ) from vosk_error
            alignment_mode = "whisper_vosk_phrase_fallback_word_timestamps"
        elif native_boundaries_path is not None:
            native_words = _load_boundaries(native_boundaries_path.resolve())
            _native_events, native_chunks = _align_chunks(chunks, native_words)
            window_words = _bounded_words(
                _recognize_phrase_windows(audio_path, model_name, native_chunks, audio_seconds),
                audio_seconds,
            )
            try:
                _events, sidecar_chunks = _align_chunks(chunks, window_words)
            except AlignmentError as window_error:
                raise AlignmentError(
                    f"{full_error} Phrase-window acoustic retry also failed: {window_error}"
                ) from window_error
            alignment_mode = "whisper_phrase_window_word_timestamps"
        else:
            raise

    overlap_count = _normalize_sidecar_word_timeline(sidecar_chunks, audio_seconds)
    events = _events_from_chunks(sidecar_chunks, audio_seconds)
    active_word_color = str(caption_config.get("active_word_color", default_active_word_color()))
    _write_ass(caption_path, events, sidecar_chunks, active_word_color, margin_v=int(caption_config.get("margin_v", 650)))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps({
        "status": "WHISPER_FORCED_ALIGNMENT_PASS",
        "provider": "faster-whisper+vosk" if secondary_vosk_model_dir is not None else "faster-whisper",
        "model": model_name,
        "timing_mode": alignment_mode,
        "audio_duration_seconds": round(audio_seconds, 3),
        "word_count": len(words),
        "words": sidecar_chunks and [
            word for chunk in sidecar_chunks for word in chunk.get("words", [])
        ] or words,
        "captions": sidecar_chunks,
        "word_timing_normalization": {
            "overlap_boundaries_closed": overlap_count,
            "timeline_monotonic": True,
            "native_edge_windows_used": alignment_mode == "whisper_phrase_window_word_timestamps",
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
        "timing_mode": alignment_mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", default="tiny.en")
    parser.add_argument("--native-boundaries", type=Path, default=None)
    parser.add_argument("--secondary-vosk-model-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        print(json.dumps(
            generate(
                args.manifest,
                args.model,
                args.native_boundaries,
                args.secondary_vosk_model_dir,
            ),
            ensure_ascii=False,
        ))
        return 0
    except (AlignmentError, OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"WHISPER CAPTION ALIGNMENT BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
