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
from production.canonical_config import caption_ass_style_line


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
    raw = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?|:", text.replace(r"\N", " "))
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
                "the": [["the"], ["uh"], ["thuh"], ["thee"]],
                "to": [["to"], ["two"], ["tuh"]],
                "of": [["of"], ["uhv"], ["ov"]],
                "and": [["and"], ["n"], ["ənd"]],
                "for": [["for"], ["fer"]],
                "in": [["in"], ["ən"]],
                "on": [["on"], ["awn"]],
                "at": [["at"], ["ət"]],
                "is": [["is"], ["iz"]],
                "was": [["was"], ["wuz"]],
                # Vosk may realize the unstressed vowel in “than” as “then”.
                # This is an explicit lexical ASR variant only; timing still
                # comes from the real Vosk word timestamp in the final WAV.
                "than": [["than"], ["then"]],
                # Content-word variants address common Vosk substitutions in
                # this production voice. They may match only a real ASR token;
                # no timestamp is ever synthesized or estimated.
                "figure": [["figure"], ["finger"], ["figger"]],
                "went": [["went"], ["when"]],
                "pointed": [["pointed"], ["point"], ["pointing"]],
                "directly": [["directly"], ["direct"]],
                "camera": [["camera"], ["cameras"]],
                "it": [["it"], ["ət"]],
                # Compound words and possessives can be emitted by ASR with a
                # different token boundary. These alternatives still require
                # every accepted token to have a real Vosk timestamp.
                "downhill": [["downhill"], ["down", "hill"]],
                "lakes": [["lakes"], ["lake"]],
                # Proper-name and specialist-term realizations observed in
                # factual narration. These are lexical ASR variants only; every
                # accepted match must still come from a real Vosk timestamp.
                "nyos": [
                    ["nyos"], ["nios"], ["nious"], ["neos"], ["nayos"], ["niyos"],
                    ["nee", "os"], ["nee", "ohs"], ["knee", "os"], ["nigh", "os"],
                    ["n"], ["no"], ["nose"], ["knows"],
                ],
                "limnic": [
                    ["limnic"], ["limnik"], ["limnick"], ["lim", "nick"],
                    ["lim", "nic"], ["lim", "nik"], ["lim", "neck"], ["limn", "ick"],
                ],
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
    grammar_phrases: list[str] | None = None,
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
            if vocabulary or grammar_phrases:
                # Constrained passes retain real timestamps from the final WAV.
                # Phrase entries are accepted by Vosk as multi-word grammar
                # alternatives, which helps preserve short words at acoustic
                # boundaries without fabricating any timing.
                grammar = grammar_phrases if grammar_phrases else vocabulary
                recognizer.SetGrammar(json.dumps(grammar, ensure_ascii=False))
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



def _merge_word_timings(*passes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge real word timestamps without creating a second timeline.

    Independent Vosk passes are useful for recovering a word that a broad pass
    missed, but their outputs are not safe to concatenate: the same spoken
    word can be returned with slightly different spans, and those spans can
    interleave with the next word. Keep the first acoustic timeline as the
    authority and admit later-pass words only when their real span fits a gap.
    This preserves real timestamps while preventing synthetic overlaps.
    """
    merged: list[dict[str, Any]] = []
    seen_exact: set[tuple[str, float, float]] = set()

    def overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
        return (
            float(left["start"]) < float(right["end"]) - 0.001
            and float(right["start"]) < float(left["end"]) - 0.001
        )

    for word_pass in passes:
        for item in sorted(
            word_pass,
            key=lambda value: (float(value["start"]), float(value["end"])),
        ):
            word = str(item.get("word", "")).strip()
            if not word:
                continue
            candidate = dict(item)
            key = (
                _normalise(word),
                round(float(candidate["start"]), 3),
                round(float(candidate["end"]), 3),
            )
            if key in seen_exact:
                continue
            if any(
                _normalise(str(existing.get("word", ""))) == _normalise(word)
                and overlaps(candidate, existing)
                for existing in merged
            ):
                continue
            seen_exact.add(key)
            merged.append(candidate)

    return sorted(merged, key=lambda item: (float(item["start"]), float(item["end"])))


def _recognize_passes(
    audio_path: Path,
    model_paths: list[Path],
    *,
    vocabulary: list[str] | None = None,
    grammar_phrases: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run independent acoustic recognizers and merge only real word timings."""
    passes = [
        _recognize(
            audio_path,
            model_path,
            vocabulary=vocabulary,
            grammar_phrases=grammar_phrases,
        )
        for model_path in model_paths
    ]
    return _merge_word_timings(*passes)


def _grammar_phrase(value: str) -> str:
    """Normalize a phrase before passing it to Vosk's grammar decoder."""
    tokens = re.findall(
        r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?",
        str(value).replace(r"\N", " "),
    )
    return " ".join(_normalise(token) for token in tokens if _normalise(token))


def _cursor_for_time(asr_words: list[dict[str, Any]], timestamp: float) -> int:
    for index, item in enumerate(asr_words):
        if float(item["start"]) >= max(0.0, timestamp - 0.02):
            return index
    return len(asr_words)


def _recover_with_phrase_vocabulary(
    chunks: list[str],
    base_words: list[dict[str, Any]],
    audio_path: Path,
    model_paths: list[Path],
) -> list[dict[str, Any]]:
    """Retry only failed phrases with a narrowly-scoped Vosk grammar.

    Broad grammars are useful for context but can drop short or acoustically
    weak content words. A phrase-scoped pass reduces the competing vocabulary
    and contributes only real Vosk word timestamps. The final full alignment
    is still mandatory; no estimated timings are accepted.
    """
    merged = list(base_words)
    cursor_time = 0.0
    for index, chunk in enumerate(chunks):
        cursor = _cursor_for_time(merged, cursor_time)
        try:
            _start, end, _next_cursor, _positions = _align_chunk(chunk, merged, cursor)
        except AlignmentError:
            # First retry the failed caption as a single ordered grammar
            # phrase.  The broad pass can legally spend acoustic probability
            # on neighboring words, while a phrase-only grammar makes Vosk
            # preserve weak content words (especially at the beginning of a
            # Piper beat) without fabricating any timing.  All accepted
            # timestamps still come from the final WAV recognizer result.
            phrase_only = _grammar_phrase(chunk)
            if phrase_only:
                phrase_words = _recognize_passes(
                    audio_path,
                    model_paths,
                    grammar_phrases=[phrase_only],
                )
                merged = _merge_word_timings(merged, phrase_words)
                cursor = _cursor_for_time(merged, cursor_time)
                try:
                    _start, end, _next_cursor, _positions = _align_chunk(chunk, merged, cursor)
                except AlignmentError:
                    pass
                else:
                    cursor_time = float(end)
                    continue
            # Keep the retry scoped to the failed phrase, but include one
            # neighboring phrase on each side. Short function words at a
            # caption boundary are often acoustically realized together with
            # the next content word (for example, "the danger"). The added
            # context improves recognition without changing canonical text or
            # inventing any timestamp.
            context_start = max(0, index - 1)
            context_end = min(len(chunks), index + 2)
            context_text = " ".join(chunks[context_start:context_end])
            phrase_vocabulary = _canonical_vocabulary(context_text)
            if not phrase_vocabulary:
                raise
            targeted_words = _recognize_passes(
                audio_path,
                model_paths,
                vocabulary=phrase_vocabulary,
            )
            merged = _merge_word_timings(merged, targeted_words)
            cursor = _cursor_for_time(merged, cursor_time)
            try:
                _start, end, _next_cursor, _positions = _align_chunk(chunk, merged, cursor)
            except AlignmentError:
                # A vocabulary-only grammar can still drop an unstressed word.
                # Retry with the failed phrase and its immediate context as
                # multi-word grammar entries. Any accepted token must still be
                # emitted by Vosk with a real start/end timestamp.
                grammar_phrases = [
                    _grammar_phrase(value)
                    for value in chunks[context_start:context_end]
                ]
                sequence_words = _recognize_passes(
                    audio_path,
                    model_paths,
                    grammar_phrases=grammar_phrases,
                )
                merged = _merge_word_timings(merged, sequence_words)
                cursor = _cursor_for_time(merged, cursor_time)
                _start, end, _next_cursor, _positions = _align_chunk(chunk, merged, cursor)
        cursor_time = float(end)
    return merged

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


def _normalize_sidecar_word_timeline(
    sidecar_chunks: list[dict[str, Any]],
    audio_seconds: float,
) -> int:
    """Close small cross-chunk ASR overlaps without inventing word order.

    Vosk can emit adjacent real words whose acoustic intervals overlap at a
    phrase boundary. The canonical word sequence is already fixed by the
    script; split only the overlapping boundary at its midpoint so captions,
    scene spans and the final renderer share one monotonic timeline.
    """
    previous: dict[str, Any] | None = None
    overlap_count = 0
    for chunk in sidecar_chunks:
        words = chunk.get("words") if isinstance(chunk, dict) else None
        if not isinstance(words, list) or not words:
            raise AlignmentError("Aligned caption chunk has no word timeline.")
        for word in words:
            if not isinstance(word, dict):
                raise AlignmentError("Aligned caption chunk contains an invalid word.")
            start = max(0.0, min(float(word["start"]), audio_seconds))
            end = max(start, min(float(word["end"]), audio_seconds))
            if end <= start:
                raise AlignmentError("Aligned word has no positive audio interval.")
            if previous is not None and start < float(previous["end"]) - 0.001:
                overlap_count += 1
                # Occasionally Vosk returns a short word nested almost
                # entirely inside the preceding word.  Split the actual
                # intersection, rather than averaging the two outer edges;
                # the latter can land at/after the short word's end and would
                # collapse its interval.  Both resulting intervals remain
                # bounded by timestamps emitted for the final WAV.
                overlap_start = max(float(previous["start"]), start)
                overlap_end = min(float(previous["end"]), end)
                boundary = round((overlap_start + overlap_end) / 2.0, 3)
                minimum = round(float(previous["start"]) + 0.001, 3)
                maximum = round(end - 0.001, 3)
                if maximum <= minimum:
                    raise AlignmentError(
                        "Aligned word overlap cannot be normalized without collapsing a word."
                    )
                boundary = max(minimum, min(boundary, maximum))
                previous["end"] = boundary
                start = boundary
            word["start"] = round(start, 3)
            word["end"] = round(end, 3)
            previous = word
    return overlap_count

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
        end_ms = max(start_ms + 1, round((float(position["end"]) - event_start) * 1000))
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
    style_line = caption_ass_style_line()
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
{style_line}

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

def generate(
    manifest_path: Path,
    model_path: Path,
    secondary_model_path: Path | None = None,
) -> dict[str, Any]:
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

    model_paths = [model_path]
    if secondary_model_path is not None:
        model_paths.append(secondary_model_path)
    for path in model_paths:
        if not path.is_dir():
            raise AlignmentError(f"Vosk model directory is missing: {path}")

    script = (base / manifest["script"]["path"]).read_text(encoding="utf-8").strip()
    chunks = phrase_chunks(
        script,
        max_line_chars=int(captions.get("max_line_chars", 42)),
    )
    asr_words: list[dict[str, Any]] = []
    try:
        asr_words = _recognize(audio_path, model_path)
        events, sidecar_chunks = _align_chunks(chunks, asr_words)
    except AlignmentError as first_error:
        secondary_error: AlignmentError | None = None
        secondary_aligned = False
        if secondary_model_path is not None:
            try:
                secondary_words = _recognize(audio_path, secondary_model_path)
                asr_words = _merge_word_timings(asr_words, secondary_words)
                events, sidecar_chunks = _align_chunks(chunks, asr_words)
                secondary_aligned = True
            except AlignmentError as error:
                secondary_error = error

        if not secondary_aligned:
            constrained_vocabulary = _canonical_vocabulary(script)
            try:
                asr_words = _recognize_passes(
                    audio_path,
                    model_paths,
                    vocabulary=constrained_vocabulary,
                )
                events, sidecar_chunks = _align_chunks(chunks, asr_words)
            except AlignmentError as constrained_error:
                try:
                    asr_words = _recover_with_phrase_vocabulary(
                        chunks,
                        asr_words,
                        audio_path,
                        model_paths,
                    )
                    events, sidecar_chunks = _align_chunks(chunks, asr_words)
                except AlignmentError as phrase_error:
                    secondary_note = (
                        f" Secondary acoustic retry also failed: {secondary_error}"
                        if secondary_error is not None else ""
                    )
                    raise AlignmentError(
                        f"{first_error}{secondary_note} "
                        f"Grammar-constrained retry also failed: {constrained_error} "
                        f"Phrase-scoped acoustic retry also failed: {phrase_error}"
                    ) from phrase_error
    overlap_count = _normalize_sidecar_word_timeline(sidecar_chunks, audio_seconds)
    # Rebuild phrase events from the normalized canonical word boundaries so
    # ASS captions and the story-timing report cannot disagree.
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
    # ASS stores centiseconds while the WAV duration is frame-precise.  A
    # normal round(audio_seconds * 100) can therefore place the final caption
    # a few milliseconds beyond the actual audio (for example 54.507s ->
    # 54.51s).  Keep the caption inside the measured WAV after serialization;
    # this leaves at most one centisecond of intentional tail gap and avoids a
    # false release-gate failure caused by timestamp quantization.
    safe_ass_end = int(audio_seconds * 100) / 100.0
    if safe_ass_end <= float(events[-1]["start"]):
        raise AlignmentError("Narration is too short to close the final caption at ASS precision.")
    events[-1]["end"] = safe_ass_end
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
        "models": [str(path) for path in model_paths],
        "audio_duration_seconds": round(audio_seconds, 3),
        "word_count": len(asr_words),
        "words": asr_words,
        "captions": sidecar_chunks,
        "word_timing_normalization": {
            "overlap_boundaries_closed": overlap_count,
            "timeline_monotonic": True,
        },
        "timing_mode": (
            "vosk_multi_model_word_timestamps"
            if secondary_model_path is not None else "vosk_word_timestamps"
        ),
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
    parser.add_argument("--secondary-model-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        print(json.dumps(
            generate(args.manifest, args.model_dir, args.secondary_model_dir),
            ensure_ascii=False,
        ))
        return 0
    except (AlignmentError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FORCED CAPTION ALIGNMENT BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
