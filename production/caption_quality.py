#!/usr/bin/env python3
"""Strict caption quality gate for the independent BECAUSE OF THIS engine.

The profile adapts the useful editorial rules from the Corte Fino engine:
semantic segmentation, clean line breaks, readable speed, safe lower-third
placement, transcript identity, overlap protection and explicit timing honesty.
It never claims word-level precision unless a real alignment sidecar is present.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import wave
from pathlib import Path
from typing import Any


class CaptionQualityError(RuntimeError):
    """Raised when the caption contract fails."""


def resolve_inside(base: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise CaptionQualityError(f"{label} path must be a non-empty string.")
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise CaptionQualityError(f"{label} path escapes the manifest directory: {relative}")
    if not path.is_file():
        raise CaptionQualityError(f"{label} file is missing: {relative}")
    return path


def parse_ass_time(value: str) -> float:
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})\.(\d{2})", value.strip())
    if not match:
        raise CaptionQualityError(f"Invalid ASS timestamp: {value}")
    hours, minutes, seconds, centiseconds = (int(item) for item in match.groups())
    return hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0


def strip_ass_tags(value: str) -> str:
    return re.sub(r"\{[^}]*\}", "", value)


def visible_text(value: str) -> str:
    return strip_ass_tags(value).replace(r"\N", "\n").replace(r"\n", "\n").strip()


def normalize_words(value: str) -> list[str]:
    value = strip_ass_tags(value)
    value = value.replace(r"\N", " ").replace(r"\n", " ")
    value = value.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value)


def _events_format(path: Path) -> list[str]:
    in_events = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_events = line.lower() == "[events]"
        elif in_events and line.lower().startswith("format:"):
            fields = [part.strip().lower() for part in line.split(":", 1)[1].split(",")]
            if len(fields) != len(set(fields)) or not {"start", "end", "text"}.issubset(fields):
                raise CaptionQualityError("ASS Events format must contain unique Start, End and Text fields.")
            return fields
    return ["layer", "start", "end", "style", "name", "marginl", "marginr", "marginv", "effect", "text"]


def parse_events(path: Path) -> list[dict[str, Any]]:
    fields = _events_format(path)
    start_index, end_index, text_index = fields.index("start"), fields.index("end"), fields.index("text")
    events: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip().startswith("Dialogue:"):
            continue
        values = raw.split(",", len(fields) - 1)
        if len(values) != len(fields):
            raise CaptionQualityError(f"Malformed ASS Dialogue line: {raw}")
        start, end = parse_ass_time(values[start_index]), parse_ass_time(values[end_index])
        if end <= start:
            raise CaptionQualityError(f"Caption interval is not positive: {raw}")
        text = values[text_index]
        events.append({
            "start": start,
            "end": end,
            "duration": end - start,
            "text": text,
            "visible_text": visible_text(text),
        })
    if not events:
        raise CaptionQualityError("Caption file has no Dialogue events.")
    for previous, current in zip(events, events[1:]):
        if current["start"] < previous["start"]:
            raise CaptionQualityError("Caption events are not chronologically ordered.")
        if current["start"] < previous["end"] - 0.001:
            raise CaptionQualityError("Caption events overlap.")
    return events


def _default_style(path: Path) -> dict[str, Any]:
    in_styles = False
    format_fields: list[str] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_styles = line.lower() == "[v4+ styles]"
            continue
        if not in_styles:
            continue
        if line.lower().startswith("format:"):
            format_fields = [part.strip().lower() for part in line.split(":", 1)[1].split(",")]
        elif line.lower().startswith("style:") and format_fields:
            values = line.split(":", 1)[1].split(",")
            if len(values) != len(format_fields):
                continue
            record = dict(zip(format_fields, values))
            if record.get("name", "").strip().lower() == "default":
                result: dict[str, Any] = {}
                for field in ("fontsize", "outline", "shadow", "alignment", "marginl", "marginr", "marginv"):
                    try:
                        result[field] = float(record[field])
                    except (KeyError, ValueError):
                        raise CaptionQualityError(f"Default ASS style has invalid {field}.")
                return result
    raise CaptionQualityError("ASS file must declare a Default style.")


def audio_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2 or handle.getframerate() != 24000:
                raise CaptionQualityError("Narration must be mono 24 kHz 16-bit PCM WAV.")
            return handle.getnframes() / 24000.0
    except (OSError, wave.Error) as exc:
        raise CaptionQualityError(f"Narration could not be read: {path}") from exc




_TRANSFORM_RE = re.compile(r"\\t\((\d+),(\d+),\\1c(&H[0-9A-Fa-f]{8}&)\)")


def _ass_color(value: str) -> str:
    raw = str(value or "").lstrip("#")
    if len(raw) != 6 or any(char not in "0123456789abcdefABCDEF" for char in raw):
        raise CaptionQualityError("Active-word caption color must be a valid six-digit hex color.")
    red, green, blue = raw[0:2], raw[2:4], raw[4:6]
    return f"&H00{blue}{green}{red}&"


def _relative_luminance(value: str) -> float:
    raw = str(value).lstrip("#")
    channels = [int(raw[index:index + 2], 16) / 255.0 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _validate_word_highlight(
    events: list[dict[str, Any]],
    sidecar: dict[str, Any],
    captions: dict[str, Any],
) -> dict[str, Any]:
    if captions.get("word_highlight_enabled") is not True:
        return {"enabled": False}
    if captions.get("word_highlight_mode") != "timestamp_color_transform":
        raise CaptionQualityError(
            "Word highlight must use timestamp_color_transform; guessed or frame-based highlighting is forbidden."
        )
    active_color = str(captions.get("active_word_color", "")).strip()
    if not active_color:
        raise CaptionQualityError("Word highlight requires active_word_color.")
    _ass_color(active_color)
    contrast = (max(_relative_luminance(active_color), 0.0) + 0.05) / 0.05
    if contrast < 4.5:
        raise CaptionQualityError(
            f"Active-word color {active_color} is not sufficiently legible against the black outline."
        )
    chunks = sidecar.get("captions")
    if not isinstance(chunks, list) or len(chunks) != len(events):
        raise CaptionQualityError("Word highlight sidecar chunks do not match caption events.")
    active_ass = _ass_color(active_color)
    reset_ass = "&H00FFFFFF&"
    max_error_ms = int(captions.get("word_highlight_tolerance_ms", 35))
    if max_error_ms < 1 or max_error_ms > 100:
        raise CaptionQualityError("word_highlight_tolerance_ms must be between 1 and 100 ms.")
    total_words = 0
    recovered_words = 0
    for index, (event, chunk) in enumerate(zip(events, chunks), start=1):
        words = chunk.get("words") if isinstance(chunk, dict) else None
        if not isinstance(words, list) or not words:
            raise CaptionQualityError(f"Caption C{index:03d} has no word-level highlight timestamps.")
        transforms = _TRANSFORM_RE.findall(event["text"])
        if len(transforms) != len(words) * 2:
            raise CaptionQualityError(
                f"Caption C{index:03d} has {len(transforms)} color transforms for {len(words)} words; "
                "exactly two transforms per word are required."
            )
        for word_index, word in enumerate(words):
            if word.get("recovered") is True:
                recovered_words += 1
                recovered_duration = float(word["end"]) - float(word["start"])
                if recovered_duration > 0.35:
                    raise CaptionQualityError(
                        f"Caption C{index:03d} word {word_index + 1} exceeds the bounded recovery window."
                    )
            active = transforms[word_index * 2]
            reset = transforms[word_index * 2 + 1]
            expected_start = round((float(word["start"]) - event["start"]) * 1000)
            expected_end = round((float(word["end"]) - event["start"]) * 1000)
            if abs(int(active[0]) - expected_start) > max_error_ms or abs(int(active[1]) - expected_end) > max_error_ms:
                raise CaptionQualityError(
                    f"Caption C{index:03d} word {word_index + 1} is not synchronized to the alignment sidecar."
                )
            if active[2].upper() != active_ass.upper() or reset[2].upper() != reset_ass.upper():
                raise CaptionQualityError(
                    f"Caption C{index:03d} word {word_index + 1} has an invalid active/reset color pair."
                )
        total_words += len(words)
    if recovered_words > 2:
        raise CaptionQualityError("Word highlight contains more than two bounded-recovery words.")
    return {
        "enabled": True,
        "mode": "timestamp_color_transform",
        "active_word_color": active_color,
        "contrast_against_black_outline": round(contrast, 2),
        "word_count": total_words,
        "recovered_word_count": recovered_words,
        "tolerance_ms": max_error_ms,
    }

def quality_report(manifest_path: Path, require_word_level: bool = False) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    captions = manifest.get("captions")
    if not isinstance(captions, dict):
        raise CaptionQualityError("Manifest requires a captions object.")
    caption_path = resolve_inside(base, captions.get("path"), "Captions")
    audio_path = resolve_inside(base, manifest.get("audio", {}).get("path"), "Audio")
    script_path = resolve_inside(base, manifest.get("script", {}).get("path"), "Script")
    events = parse_events(caption_path)
    duration = audio_duration(audio_path)

    alignment_mode = captions.get("alignment_mode")
    alignment_source = str(captions.get("alignment_source", "")).strip()
    word_level = captions.get("word_level_available") is True
    sidecar: dict[str, Any] | None = None
    if alignment_mode not in {"forced_alignment", "hybrid_alignment", "phrase_level_manual_reviewed"}:
        raise CaptionQualityError("Manifest declares an unsupported caption alignment_mode.")
    if not alignment_source:
        raise CaptionQualityError("Caption alignment_source is required.")
    if alignment_mode == "phrase_level_manual_reviewed" and word_level:
        raise CaptionQualityError("Phrase-level captions cannot declare word_level_available=true.")
    if alignment_mode == "forced_alignment" or word_level:
        sidecar_path = resolve_inside(
            base,
            captions.get("alignment_sidecar", "captions/narration.alignment.json"),
            "Caption alignment sidecar",
        )
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CaptionQualityError("Caption alignment sidecar is unreadable.") from exc
        if sidecar.get("status") != "FORCED_ALIGNMENT_PASS" or not isinstance(sidecar.get("words"), list):
            raise CaptionQualityError("Forced caption alignment sidecar is incomplete.")
        if abs(float(sidecar.get("audio_duration_seconds", -1)) - duration) > 0.15:
            raise CaptionQualityError("Caption alignment sidecar duration does not match narration.")
        if any(not isinstance(item, dict) or not item.get("word") for item in sidecar["words"]):
            raise CaptionQualityError("Caption alignment sidecar contains invalid word timestamps.")
    if require_word_level and not word_level:
        raise CaptionQualityError(
            "Final release requires real word-level alignment; current captions are explicitly phrase-level."
        )

    word_highlight = {"enabled": False}
    if captions.get("word_highlight_enabled") is True:
        if sidecar is None:
            raise CaptionQualityError("Word highlight requires a readable forced-alignment sidecar.")
        word_highlight = _validate_word_highlight(events, sidecar, captions)

    script_words = normalize_words(script_path.read_text(encoding="utf-8"))
    caption_words = normalize_words(" ".join(event["text"] for event in events))
    if script_words != caption_words:
        raise CaptionQualityError("Caption words do not exactly match the canonical script.")

    max_lines = int(captions.get("max_lines", 2))
    max_line_chars = int(captions.get("max_line_chars", 42))
    max_cps = float(captions.get("max_cps", 24.0))
    target_cps = float(captions.get("target_cps", max_cps))
    end_tolerance = float(captions.get("end_tolerance_seconds", 0.10))
    if (
        max_lines < 1
        or max_lines > 2
        or max_line_chars < 20
        or target_cps <= 0
        or max_cps <= 0
        or target_cps > max_cps
    ):
        raise CaptionQualityError("Caption readability thresholds are invalid.")

    quality_events = []
    for index, event in enumerate(events, start=1):
        lines = event["visible_text"].splitlines()
        if not 1 <= len(lines) <= max_lines:
            raise CaptionQualityError(f"Caption C{index:03d} exceeds the {max_lines}-line limit.")
        if any(not line.strip() for line in lines):
            raise CaptionQualityError(f"Caption C{index:03d} contains an empty line.")
        if any(len(line) > max_line_chars for line in lines):
            raise CaptionQualityError(f"Caption C{index:03d} exceeds {max_line_chars} characters on one line.")
        cps = len(event["visible_text"].replace("\n", " ")) / event["duration"]
        if cps > max_cps:
            raise CaptionQualityError(
                f"Caption C{index:03d} is too fast: {cps:.2f} CPS exceeds {max_cps:.2f}."
            )
        quality_events.append({
            "caption_id": f"C{index:03d}",
            "start": round(event["start"], 3),
            "end": round(event["end"], 3),
            "duration": round(event["duration"], 3),
            "cps": round(cps, 2),
            "line_count": len(lines),
            "within_target_cps": cps <= target_cps,
            "text": event["visible_text"],
        })

    first_start = events[0]["start"]
    end_gap = duration - events[-1]["end"]
    if first_start < 0 or first_start > 0.75:
        raise CaptionQualityError("Caption opening is not anchored to the narration hook.")
    if end_gap < -0.001 or end_gap > end_tolerance:
        raise CaptionQualityError(f"Caption end gap {end_gap:.3f}s exceeds {end_tolerance:.3f}s.")

    style = _default_style(caption_path)
    if style["alignment"] != 2:
        raise CaptionQualityError("Captions must use centered lower-third alignment=2.")
    if style["marginl"] < 80 or style["marginr"] < 80 or style["marginv"] < 280:
        raise CaptionQualityError("Captions do not meet the mobile safe-zone margins.")
    if not 42 <= style["fontsize"] <= 56:
        raise CaptionQualityError("Caption font size is outside the approved mobile range.")
    if style["outline"] < 2 or style["outline"] > 5 or style["shadow"] > 3:
        raise CaptionQualityError("Caption outline/shadow is outside the approved legibility range.")

    return {
        "status": "CAPTION_QA_PASS",
        "manifest": str(manifest_path),
        "caption_path": str(caption_path),
        "audio_duration_seconds": round(duration, 3),
        "event_count": len(events),
        "alignment_mode": alignment_mode,
        "word_level_available": word_level,
        "alignment_source": alignment_source,
        "timing_claim": (
            "word_level_verified_with_bounded_anchor_recovery"
            if word_level and sidecar and sidecar.get("recovered_word_count", 0)
            else ("word_level_verified" if word_level else "reviewed_phrase_level")
        ),
        "word_highlight": word_highlight,
        "thresholds": {
            "max_lines": max_lines,
            "max_line_chars": max_line_chars,
            "target_cps": target_cps,
            "max_cps": max_cps,
            "end_tolerance_seconds": end_tolerance,
        },
        "style": style,
        "events": quality_events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the strict BECAUSE OF THIS caption QA gate.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-word-level", action="store_true")
    args = parser.parse_args()
    try:
        report = quality_report(args.manifest, require_word_level=args.require_word_level)
    except (CaptionQualityError, OSError, json.JSONDecodeError) as exc:
        print(f"CAPTION QA BLOCKED: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
