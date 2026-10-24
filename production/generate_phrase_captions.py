#!/usr/bin/env python3
"""Generate reviewed phrase-level ASS captions from the final narration WAV.

This is intentionally preview-grade: it preserves the exact canonical script and
anchors each phrase to the measured final audio duration. Final releases still
require real word-level alignment.
"""

from __future__ import annotations

import argparse
import json
import re
import wave
from pathlib import Path
from textwrap import wrap


class CaptionGenerationError(RuntimeError):
    pass


def read_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2 or handle.getframerate() != 24000:
                raise CaptionGenerationError("Narration must be mono 24 kHz 16-bit PCM WAV.")
            return handle.getnframes() / 24000.0
    except (OSError, wave.Error) as exc:
        raise CaptionGenerationError(f"Could not read narration WAV: {path}") from exc


def ass_time(seconds: float) -> str:
    total_centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[^A-Za-z0-9\s]", text)


def _balanced_lines(sentence: str, width: int) -> list[str]:
    words = sentence.split()
    if not words:
        return []
    if len(sentence) <= width:
        return [sentence]

    candidates: list[tuple[float, list[str]]] = []
    for split in range(1, len(words)):
        left, right = " ".join(words[:split]), " ".join(words[split:])
        if len(left) <= width and len(right) <= width:
            imbalance = abs(len(left) - len(right))
            candidates.append((max(len(left), len(right)) + imbalance * 0.15, [left, right]))
    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    return wrap(sentence, width=width, break_long_words=False, break_on_hyphens=False)


def phrase_chunks(script: str, max_line_chars: int = 42) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", script.strip()) if part.strip()]
    chunks: list[str] = []
    for sentence in sentences:
        lines = _balanced_lines(sentence, max_line_chars)
        for index in range(0, len(lines), 2):
            chunk = lines[index:index + 2]
            if chunk:
                chunks.append("\\N".join(chunk))
    if not chunks:
        raise CaptionGenerationError("Script produced no caption phrases.")
    return chunks


def generate(manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    script_path = (base / manifest["script"]["path"]).resolve()
    audio_path = (base / manifest["audio"]["path"]).resolve()
    duration = read_duration(audio_path)
    script = script_path.read_text(encoding="utf-8").strip()
    caption_config = manifest.get("captions") or {}
    max_line_chars = int(caption_config.get("max_line_chars", 42))
    if max_line_chars < 20:
        raise CaptionGenerationError("Caption max_line_chars must be at least 20.")
    chunks = phrase_chunks(script, max_line_chars=max_line_chars)

    weights = [max(1, len(tokenize(chunk))) for chunk in chunks]
    total_weight = sum(weights)
    events: list[str] = []
    cursor = 0.0
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        end = duration if index == len(chunks) else cursor + duration * weight / total_weight
        if end - cursor < 0.08:
            raise CaptionGenerationError("Caption phrase became too short for readable display.")
        events.append(
            f"Dialogue: 0,{ass_time(cursor)},{ass_time(end)},Default,,0,0,0,,{chunk}"
        )
        cursor = end

    caption_path = (base / manifest["captions"]["path"]).resolve()
    caption_path.parent.mkdir(parents=True, exist_ok=True)
    ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,100,100,320,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
""" + "\n".join(events) + "\n"
    caption_path.write_text(ass, encoding="utf-8")
    return {"status": "PHRASE_CAPTIONS_GENERATED", "caption_path": str(caption_path), "duration_seconds": round(duration, 3), "event_count": len(events)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.manifest), ensure_ascii=False))
        return 0
    except (CaptionGenerationError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"CAPTION GENERATION BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
