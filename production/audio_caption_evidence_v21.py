"""Read-only structural verification of a frozen narration/caption checkpoint.

This audit cannot prove perceptual accuracy of timestamps, natural prosody,
visual styling, or rights. Those need independent human/media QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import wave
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tokens(value: str) -> list[str]:
    return [x.lower() for x in re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value, flags=re.IGNORECASE)]


def audit(
    audio_path: Path, script_path: Path, ass_path: Path,
    sidecar_path: Path, profile_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        script = script_path.read_text(encoding="utf-8")
        ass = ass_path.read_text(encoding="utf-8")
        with wave.open(str(audio_path), "rb") as reader:
            channels = reader.getnchannels()
            sample_rate = reader.getframerate()
            sample_width = reader.getsampwidth()
            duration = reader.getnframes() / sample_rate
        if channels != 1 or sample_width != 2 or sample_rate != 24000:
            errors.append("WAV must be mono 24 kHz 16-bit PCM")
        if not 60 <= duration <= 80:
            errors.append("WAV duration outside approved 60–80s bound")
        if profile.get("provider") != "gemini_tts" or profile.get("voice_name") != "Charon":
            errors.append("wrong frozen Charon provider/voice")
        if profile.get("audio_sha256") != _sha256(audio_path):
            errors.append("audio SHA-256 differs from frozen voice profile")
        # Episode 006's approved narration workflow calls read_text().strip()
        # before synthesis and hashes THAT exact provider input, not the
        # source file's trailing newline. Preserve the frozen audio identity.
        tts_script = script.strip()
        if profile.get("script_sha256") != hashlib.sha256(tts_script.encode("utf-8")).hexdigest():
            errors.append("normalized TTS script SHA-256 differs from frozen voice profile")
        words = sidecar.get("words")
        captions = sidecar.get("captions")
        if sidecar.get("status") != "WHISPER_FORCED_ALIGNMENT_PASS":
            errors.append("alignment sidecar is not PASS")
        if not isinstance(words, list) or not words:
            errors.append("word timestamp evidence missing")
            words = []
        if not isinstance(captions, list) or not captions:
            errors.append("caption groups missing")
            captions = []
        aligned = [str(word.get("canonical", "")) for word in words if isinstance(word, dict)]
        if _tokens(" ".join(aligned)) != _tokens(script):
            errors.append("word-by-word canonical transcript differs from frozen script")
        last_end = 0.0
        for index, word in enumerate(words):
            try:
                start, end = float(word["start"]), float(word["end"])
            except (TypeError, ValueError, KeyError):
                errors.append(f"invalid timestamp at word {index}")
                continue
            if not (0 <= start < end <= duration + 0.05):
                errors.append(f"word {index} timestamp out of audio bounds")
            if start < last_end - 0.015:
                errors.append(f"word {index} overlaps preceding word")
            last_end = max(last_end, end)
        caption_words = [
            str(word.get("canonical", ""))
            for group in captions if isinstance(group, dict)
            for word in group.get("words", []) if isinstance(word, dict)
        ]
        if _tokens(" ".join(caption_words)) != _tokens(script):
            errors.append("caption groups do not cover the frozen transcript")
        dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
        if len(dialogues) != len(captions):
            errors.append("ASS event count differs from caption groups")
        if sidecar.get("audio_duration_seconds") is None or abs(float(sidecar["audio_duration_seconds"]) - duration) > 0.2:
            errors.append("alignment duration differs from frozen WAV")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, wave.Error) as exc:
        errors.append(f"unreadable or malformed checkpoint:{exc}")
    return {
        "status": "AUDIO_CAPTION_STRUCTURAL_PASS" if not errors else "BLOCKED",
        "errors": errors,
        "perceptual_audio_caption_qa": "REQUIRES_HUMAN_REVIEW",
        "publication_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("audio", "script", "ass", "sidecar", "profile"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.audio, args.script, args.ass, args.sidecar, args.profile)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "AUDIO_CAPTION_STRUCTURAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
