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
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
            short_word_variants = {
                "a": [["a"], ["uh"], ["ah"]],
                "an": [["an"], ["un"]],
                "the": [["the"], ["uh"], ["thuh"]],
                "to": [["to"], ["two"], ["tuh"]],
                "of": [["of"], ["uhv"], ["ov"]],
                "and": [["and"], ["n"], ["ənd"]],
                "for": [["for"], ["fer"]],
                "in": [["in"], ["ən"]],
                "on": [["on"], ["awn"]],
                "at": [["at"], ["ət"]],
                "is": [["is"], ["iz"]],
                "was": [["was"], ["wuz"]],
                "it": [["it"], ["ət"]],
            }
            result.append((raw[index], short_word_variants.get(token, [[token]])))
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


_RECOVERY_DURATIONS = {
    "a": 0.10,
    "an": 0.12,
    "the": 0.16,
    "to": 0.14,
    "of": 0.13,
    "and": 0.14,
    "for": 0.16,
    "in": 0.13,
    "on": 0.13,
    "at": 0.11,
    "is": 0.12,
    "was": 0.16,
    "it": 0.11,
}


def _recovery_duration(canonical: str) -> float | None:
    """Return a conservative duration only for short function words.

    Recovery never invents a timestamp for content words. For a missing
    function word, the real neighboring Vosk anchor is used and the short
    word is placed immediately before the following anchor (or after the
    previous one), leaving any intervening silence untouched.
    """
    return _RECOVERY_DURATIONS.get(_normalise(canonical))


def _align_chunk(
    chunk: str,
    asr_words: list[dict[str, Any]],
    cursor: int,
    *,
    recover_missing: bool = False,
) -> tuple[float, float, int, list[dict[str, Any]]]:
    units = _units(chunk)
    if not units:
        raise AlignmentError("Caption chunk contains no spoken words.")
    matched = 0
    matched_units: list[dict[str, Any] | None] = []
    search_cursor = cursor
    for original, alternatives in units:
        found: tuple[int, int, float, float] | None = None
        # Speech recognizers finalize audio in natural pauses. A caption can
        # therefore begin several recognized tokens after the previous one,
        # especially when Vosk emits segment results. Search a generous,
        # bounded lookahead but still keep the timeline strictly monotonic.
        window_end = min(len(asr_words), search_cursor + 48)
        for candidate in range(search_cursor, window_end):
            match = _match_at(asr_words, candidate, alternatives)
            if not match:
                continue
            size, score = match
            gap = candidate - search_cursor
            rank = score - min(gap, 24) * 0.003
            if found is None or rank > found[3]:
                found = (candidate, size, score, rank)
        if found is None:
            matched_units.append(None)
            continue
        candidate, size, score, _rank = found
        matched += 1
        matched_units.append({
            "canonical": original,
            "asr": " ".join(word["word"] for word in asr_words[candidate:candidate + size]),
            "start": asr_words[candidate]["start"],
            "end": asr_words[candidate + size - 1]["end"],
            "confidence": round(score, 3),
            "recovered": False,
            "timestamp_source": "vosk_word_timestamp",
            "_asr_index": candidate,
        })
        search_cursor = candidate + size

    if matched < len(units):
        if not recover_missing:
            missing = len(units) - matched
            matched_canonical = [
                item["canonical"] for item in matched_units if item is not None
            ]
            raise AlignmentError(
                f"Could not align caption phrase {chunk!r}: matched {matched}/{len(units)} "
                f"spoken units ({missing} missing). Matched canonical units: {matched_canonical}. "
                "Strict word-highlight alignment requires every canonical word to have a real timestamp."
            )
        if matched == 0:
            raise AlignmentError(
                f"Could not recover caption phrase {chunk!r}: no Vosk word anchors were found."
            )
        recovered_count = 0
        index = 0
        while index < len(units):
            if matched_units[index] is not None:
                index += 1
                continue
            group_start = index
            while index < len(units) and matched_units[index] is None:
                index += 1
            group_end = index
            count = group_end - group_start
            if count > 2:
                raise AlignmentError(
                    f"Could not safely recover {count} missing word timestamp(s) in {chunk!r}."
                )
            estimates = [
                _recovery_duration(units[item][0])
                for item in range(group_start, group_end)
            ]
            if any(value is None for value in estimates):
                missing_words = [units[item][0] for item in range(group_start, group_end)]
                raise AlignmentError(
                    f"Could not safely recover non-function word(s) {missing_words!r} in {chunk!r}."
                )
            total_duration = sum(float(value) for value in estimates if value is not None)
            if total_duration < 0.035 or total_duration > 0.35:
                raise AlignmentError(
                    f"Could not safely recover {count} missing word timestamp(s) in {chunk!r}; "
                    f"estimated span={total_duration:.3f}s."
                )
            previous = next(
                (matched_units[item] for item in range(group_start - 1, -1, -1)
                 if matched_units[item] is not None),
                None,
            )
            following = next(
                (matched_units[item] for item in range(group_end, len(units))
                 if matched_units[item] is not None),
                None,
            )
            if following is not None:
                end_time = float(following["start"])
                start_time = end_time - total_duration
                if previous is not None and start_time < float(previous["end"]):
                    raise AlignmentError(
                        f"Could not safely recover {count} missing word timestamp(s) in {chunk!r}; "
                        "the following-anchor window overlaps the previous anchor."
                    )
            elif previous is not None:
                start_time = float(previous["end"])
                end_time = start_time + total_duration
            else:
                raise AlignmentError(f"Could not recover caption phrase {chunk!r}.")
            cursor_time = start_time
            for missing_index, estimate in zip(
                range(group_start, group_end), estimates
            ):
                word_start = cursor_time
                word_end = word_start + float(estimate)
                matched_units[missing_index] = {
                    "canonical": units[missing_index][0],
                    "asr": "",
                    "start": word_start,
                    "end": word_end,
                    "confidence": 0.0,
                    "recovered": True,
                    "timestamp_source": "vosk_bounded_function_word_recovery",
                    "recovery_anchor": "following" if following is not None else "previous",
                    "_asr_index": None,
                }
                cursor_time = word_end
                recovered_count += 1
        if recovered_count > 2:
            raise AlignmentError(
                f"Could not safely recover caption phrase {chunk!r}: "
                f"{recovered_count} words require anchor recovery."
            )

    positions = [item for item in matched_units if item is not None]
    if len(positions) != len(units):
        raise AlignmentError(f"Caption phrase {chunk!r} did not produce a complete word timeline.")
    positions.sort(key=lambda item: (float(item["start"]), float(item["end"])))
    for item in positions:
        item.pop("_asr_index", None)
    return positions[0]["start"], positions[-1]["end"], search_cursor, positions

def _canonical_vocabulary(script: str) -> list[str]:
    vocabulary: set[str] = set()
    for _original, alternatives in _units(script):
        for alternative in alternatives:
            vocabulary.update(alternative)
    return sorted(token for token in vocabulary if token)


def _recognize(
    audio_path: Path,
    model_path: Path,
    *,
    vocabulary: list[str] | None = None,
) -> list[dict[str, Any]]:
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
            if vocabulary:
                # A second, constrained pass reduces predictable ASR substitutions
                # while retaining real timestamps from the final WAV. The grammar
                # is derived only from the canonical script; it never invents
                # caption timings.
                recognizer.SetGrammar(json.dumps(vocabulary, ensure_ascii=False))
            recognizer.SetWords(True)
            payloads: list[dict[str, Any]] = []
            while True:
                frames = audio.readframes(4000)
                if not frames:
                    break
                if recognizer.AcceptWaveform(frames):
                    payloads.append(json.loads(recognizer.Result()))
            payloads.append(json.loads(recognizer.FinalResult()))
    except (OSError, wave.Error, json.JSONDecodeError) as exc:
        raise AlignmentError(f"Could not recognize narration audio: {audio_path}") from exc

    words: list[dict[str, Any]] = []
    seen: set[tuple[str, float, float]] = set()
    for payload in payloads:
        for item in payload.get("result", []):
            if item.get("word") and isinstance(item.get("start"), (int, float)) and isinstance(item.get("end"), (int, float)):
                key = (str(item["word"]), float(item["start"]), float(item["end"]))
                if key in seen:
                    continue
                seen.add(key)
                words.append({
                    "word": str(item["word"]),
                    "start": float(item["start"]),
                    "end": float(item["end"]),
                    "confidence": float(item.get("conf", 0.0)),
                })
    words.sort(key=lambda item: (item["start"], item["end"]))
    if not words:
        raise AlignmentError("Speech recognizer returned no word timestamps.")
    return words


def _align_chunks(
    chunks: list[str],
    asr_words: list[dict[str, Any]],
    *,
    recover_missing: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    sidecar_chunks: list[dict[str, Any]] = []
    cursor = 0
    for chunk in chunks:
        start, end, cursor, positions = _align_chunk(
            chunk, asr_words, cursor, recover_missing=recover_missing
        )
        events.append({"start": start, "end": end, "text": chunk})
        sidecar_chunks.append({"text": chunk, "words": positions})
    return events, sidecar_chunks

def _ass_color(value: str) -> str:
    raw = str(value or "#FF7777").lstrip("#")
    if len(raw) != 6 or any(char not in "0123456789abcdefABCDEF" for char in raw):
        raise AlignmentError("Active-word caption color must be a valid six-digit hex color.")
    red, green, blue = raw[0:2], raw[2:4], raw[4:6]
    return f"&H00{blue}{green}{red}&"


def _highlighted_chunk(
    chunk: str,
    event_start: float,
    event_end: float,
    positions: list[dict[str, Any]],
    active_word_color: str,
) -> str:
    """Build one ASS event whose active word is colored by exact audio time.

    The event remains a single phrase, so normal caption QA sees the canonical
    transcript once. Each word receives two ASS color transforms: white to the
    soft brand red at the word's real start, then back to white at its real end.
    """

    if not positions:
        raise AlignmentError("Caption phrase has no word timestamps for highlighting.")
    color = _ass_color(active_word_color)
    duration_ms = max(1, round((event_end - event_start) * 1000))
    cursor = 0
    pieces: list[str] = []
    for position in positions:
        canonical = str(position.get("canonical", "")).strip()
        if not canonical:
            raise AlignmentError("Caption word position is missing its canonical token.")
        match = re.search(re.escape(canonical), chunk[cursor:], flags=re.IGNORECASE)
        if match is None:
            raise AlignmentError(
                f"Could not map aligned canonical word {canonical!r} back to caption text {chunk!r}."
            )
        token_start = cursor + match.start()
        token_end = cursor + match.end()
        start_ms = max(0, min(duration_ms, round((float(position["start"]) - event_start) * 1000)))
        end_ms = max(start_ms + 1, min(duration_ms, round((float(position["end"]) - event_start) * 1000)))
        reset_end_ms = min(duration_ms + 1000, end_ms + 1)
        tags = (
            "{\\1c&H00FFFFFF&"
            f"\\t({start_ms},{end_ms},\\1c{color})"
            f"\\t({end_ms},{reset_end_ms},\\1c&H00FFFFFF&)"
            "}"
        )
        pieces.append(chunk[cursor:token_start])
        pieces.append(tags)
        pieces.append(chunk[token_start:token_end])
        cursor = token_end
    pieces.append(chunk[cursor:])
    return "".join(pieces)


def _write_ass(
    path: Path,
    events: list[dict[str, Any]],
    sidecar_chunks: list[dict[str, Any]],
    active_word_color: str,
) -> None:
    if len(events) != len(sidecar_chunks):
        raise AlignmentError("Caption events and alignment chunks must have identical counts.")
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
    lines: list[str] = []
    for event, chunk in zip(events, sidecar_chunks):
        text = _highlighted_chunk(
            event["text"],
            float(event["start"]),
            float(event["end"]),
            chunk.get("words") or [],
            active_word_color,
        )
        lines.append(
            f"Dialogue: 0,{ass_time(event['start'])},{ass_time(event['end'])},"
            f"Default,,0,0,0,,{text}"
        )
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

    script = (base / manifest["script"]["path"]).read_text(encoding="utf-8").strip()
    chunks = phrase_chunks(
        script,
        max_line_chars=int(captions.get("max_line_chars", 42)),
    )
    try:
        asr_words = _recognize(audio_path, model_path)
        events, sidecar_chunks = _align_chunks(chunks, asr_words)
    except AlignmentError as first_error:
        constrained_vocabulary = _canonical_vocabulary(script)
        try:
            asr_words = _recognize(
                audio_path,
                model_path,
                vocabulary=constrained_vocabulary,
            )
            events, sidecar_chunks = _align_chunks(chunks, asr_words)
        except AlignmentError as constrained_error:
            raise AlignmentError(
                f"{first_error} Grammar-constrained retry also failed: {constrained_error}"
            ) from constrained_error
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

    active_word_color = str(captions.get("active_word_color", "#FF7777"))
    _write_ass(caption_path, events, sidecar_chunks, active_word_color)
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
        "timing_mode": "vosk_word_timestamps",
        "recovered_word_count": 0,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "FORCED_CAPTIONS_GENERATED",
        "caption_path": str(caption_path),
        "alignment_sidecar": str(sidecar_path),
        "duration_seconds": round(audio_seconds, 3),
        "event_count": len(events),
        "recognized_words": len(asr_words),
        "word_highlight_mode": "timestamp_color_transform",
        "active_word_color": active_word_color,
        "recovered_word_count": 0,
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
