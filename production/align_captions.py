#!/usr/bin/env python3
"""Generate captions from real word timestamps in the final narration WAV.

The script uses the free Vosk recognizer only as an alignment instrument. The
caption text always comes from the canonical script; Vosk supplies the timing
of the words that were actually spoken. If the audio cannot be aligned to the
script, the pipeline fails closed instead of emitting guessed captions.
"""

from __future__ import annotations

import argparse
import json
import re
import wave
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from production.generate_phrase_captions import ass_time, phrase_chunks


class AlignmentError(RuntimeError):
    """Raised when real speech timing cannot be aligned safely."""


ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
TENS = ["", "", "twenty", "thirty", "forty", "fifty"]


def _number_words(value: int) -> list[str]:
    if 0 <= value < len(ONES):
        return [ONES[value]]
    if 20 <= value < 60:
        return [TENS[value // 10]] + ([] if value % 10 == 0 else [ONES[value % 10]])
    return [str(value)]


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower().replace("’", "'"))


def _units(text: str) -> list[tuple[str, list[list[str]]]]:
    raw = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|:", text.replace(r"\N", " "))
    result: list[tuple[str, list[list[str]]]] = []
    index = 0
    while index < len(raw):
        if (
            index + 2 < len(raw)
            and raw[index].isdigit()
            and raw[index + 1] == ":"
            and raw[index + 2].isdigit()
        ):
            left, right = int(raw[index]), int(raw[index + 2])
            original = f"{raw[index]}:{raw[index + 2]}"
            result.append((original, [
                [_normalise(raw[index]), _normalise(raw[index + 2])],
                _number_words(left) + _number_words(right),
            ]))
            index += 3
            continue
        token = _normalise(raw[index])
        if token:
            result.append((raw[index], [[token]]))
        index += 1
    return result


def _similar(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def _match_at(asr_words: list[dict[str, Any]], start: int, alternatives: list[list[str]]) -> tuple[int, float] | None:
    best: tuple[int, float] | None = None
    for alternative in alternatives:
        size = len(alternative)
        if start + size > len(asr_words):
            continue
        scores = [
            _similar(_normalise(asr_words[start + offset]["word"]), expected)
            for offset, expected in enumerate(alternative)
        ]
        score = sum(scores) / len(scores)
        if min(scores) >= 0.78 and (best is None or score > best[1]):
            best = (size, score)
    return best


def _align_chunk(chunk: str, asr_words: list[dict[str, Any]], cursor: int) -> tuple[float, float, int, list[dict[str, Any]]]:
    units = _units(chunk)
    if not units:
        raise AlignmentError("Caption chunk contains no spoken words.")
    matched = 0
    positions: list[dict[str, Any]] = []
    search_cursor = cursor
    for original, alternatives in units:
        found: tuple[int, int, float] | None = None
        for candidate in range(search_cursor, min(len(asr_words), search_cursor + 12)):
            match = _match_at(asr_words, candidate, alternatives)
            if match:
                size, score = match
                found = (candidate, size, score)
                break
        if found is None:
            continue
        candidate, size, score = found
        matched += 1
        positions.append({
            "canonical": original,
            "asr": " ".join(word["word"] for word in asr_words[candidate:candidate + size]),
            "start": asr_words[candidate]["start"],
            "end": asr_words[candidate + size - 1]["end"],
            "confidence": round(score, 3),
        })
        search_cursor = candidate + size

    required = max(1, int(len(units) * 0.72))
    if matched < required:
        missing = len(units) - matched
        raise AlignmentError(
            f"Could not align caption phrase {chunk!r}: matched {matched}/{len(units)} "
            f"spoken units ({missing} missing)."
        )
    return positions[0]["start"], positions[-1]["end"], search_cursor, positions


def _recognize(audio_path: Path, model_path: Path) -> list[dict[str, Any]]:
    try:
        from vosk import KaldiRecognizer, Model
    except ImportError as exc:
        raise AlignmentError("Vosk is required for forced caption alignment.") from exc
    if not model_path.is_dir():
        raise AlignmentError(f"Vosk model directory is missing: {model_path}")
    try:
        with wave.open(str(audio_path), "rb") as audio:
            if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 24000:
                raise AlignmentError("Narration must be mono 24 kHz 16-bit PCM WAV.")
            recognizer = KaldiRecognizer(Model(str(model_path)), 24000)
            recognizer.SetWords(True)
            while True:
                frames = audio.readframes(4000)
                if not frames:
                    break
                recognizer.AcceptWaveform(frames)
            payloads = [json.loads(recognizer.FinalResult())]
    except (OSError, wave.Error, json.JSONDecodeError) as exc:
        raise AlignmentError(f"Could not recognize narration audio: {audio_path}") from exc

    words: list[dict[str, Any]] = []
    for payload in payloads:
        for item in payload.get("result", []):
            if item.get("word") and isinstance(item.get("start"), (int, float)) and isinstance(item.get("end"), (int, float)):
                words.append({
                    "word": str(item["word"]),
                    "start": float(item["start"]),
                    "end": float(item["end"]),
                    "confidence": float(item.get("conf", 0.0)),
                })
    if not words:
        raise AlignmentError("Speech recognizer returned no word timestamps.")
    return words


def _write_ass(path: Path, events: list[dict[str, Any]]) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,100,100,320,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [
        f"Dialogue: 0,{ass_time(event['start'])},{ass_time(event['end'])},Default,,0,0,0,,{event['text']}"
        for event in events
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def generate(manifest_path: Path, model_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_path = (base / manifest["audio"]["path"]).resolve()
    captions = manifest.get("captions") or {}
    caption_path = (base / captions["path"]).resolve()
    duration = wave.open(str(audio_path), "rb")
    try:
        audio_seconds = duration.getnframes() / duration.getframerate()
    finally:
        duration.close()

    asr_words = _recognize(audio_path, model_path)
    chunks = phrase_chunks(
        (base / manifest["script"]["path"]).read_text(encoding="utf-8").strip(),
        max_line_chars=int(captions.get("max_line_chars", 42)),
    )
    events: list[dict[str, Any]] = []
    cursor = 0
    sidecar_chunks: list[dict[str, Any]] = []
    for chunk in chunks:
        start, end, cursor, positions = _align_chunk(chunk, asr_words, cursor)
        events.append({"start": start, "end": end, "text": chunk})
        sidecar_chunks.append({"text": chunk, "words": positions})

    for index in range(1, len(events)):
        boundary = (events[index - 1]["end"] + events[index]["start"]) / 2
        events[index - 1]["end"] = boundary
        events[index]["start"] = boundary
    events[0]["start"] = 0.0
    events[-1]["end"] = audio_seconds
    for event in events:
        if event["end"] - event["start"] < 0.08:
            raise AlignmentError("Forced-aligned caption phrase became too short.")
        event["start"] = round(max(0.0, event["start"]), 3)
        event["end"] = round(min(audio_seconds, event["end"]), 3)

    _write_ass(caption_path, events)
    sidecar_path = (base / captions.get("alignment_sidecar", "captions/narration.alignment.json")).resolve()
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps({
        "status": "FORCED_ALIGNMENT_PASS",
        "provider": "Vosk",
        "model": str(model_path),
        "audio_duration_seconds": round(audio_seconds, 3),
        "word_count": len(asr_words),
        "words": asr_words,
        "captions": sidecar_chunks,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "FORCED_CAPTIONS_GENERATED",
        "caption_path": str(caption_path),
        "alignment_sidecar": str(sidecar_path),
        "duration_seconds": round(audio_seconds, 3),
        "event_count": len(events),
        "recognized_words": len(asr_words),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.manifest, args.model_dir), ensure_ascii=False))
        return 0
    except (AlignmentError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FORCED CAPTION ALIGNMENT BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
