#!/usr/bin/env python3
"""Generate one narration WAV through Google's Gemini TTS API.

This is an isolated provider adapter for the independent faceless Shorts project.
It does not read, import, or modify any other project or GitHub engine.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import queue
import tempfile
import threading
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-3.8-flash-lite-tts"
DEFAULT_VOICE = "Charon"
DEFAULT_STYLE = (
    "Neutral American English documentary narration. Clear, natural, "
    "steady pace with restrained emphasis; informative, not theatrical."
)


class NarrationError(RuntimeError):
    """Raised when narration cannot be generated or validated."""


def _read_script(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise NarrationError(f"Could not read script file: {path}") from exc
    if not text:
        raise NarrationError("The script file is empty.")
    return text


def _extract_audio(interaction: Any) -> bytes:
    try:
        encoded = interaction.output_audio.data
    except (AttributeError, TypeError) as exc:
        raise NarrationError("The API response did not contain generated audio.") from exc
    if not encoded:
        raise NarrationError("The API returned an empty audio payload.")
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise NarrationError("The API returned audio in an unexpected format.") from exc
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise NarrationError("The API output was not a valid WAV file.")
    return audio


def _wav_duration(audio: bytes) -> float:
    try:
        import io

        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            if wav_file.getframerate() <= 0:
                raise NarrationError("The WAV file has an invalid sample rate.")
            return wav_file.getnframes() / wav_file.getframerate()
    except (wave.Error, EOFError) as exc:
        raise NarrationError("The generated WAV file could not be validated.") from exc


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as tmp:
            temp_name = tmp.name
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_name, path)
    except OSError as exc:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise NarrationError(f"Could not safely write output file: {path}") from exc




def _request_with_timeout(request: Any, timeout_seconds: float) -> Any:
    """Run one provider call with a daemon guard against indefinite hangs."""
    result_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            result_queue.put(("ok", request()))
        except BaseException as exc:  # SDK exception types vary by release.
            result_queue.put(("error", exc))

    thread = threading.Thread(target=worker, name="gemini-tts-request", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise NarrationError(
            f"Google TTS request timed out after {timeout_seconds:.1f} seconds. "
            "No automatic retry was made."
        )
    try:
        status, value = result_queue.get_nowait()
    except queue.Empty as exc:
        raise NarrationError("Google TTS request ended without a response.") from exc
    if status == "error":
        raise value
    return value


def generate_narration(
    text: str,
    output_path: Path,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    style: str = DEFAULT_STYLE,
    overwrite: bool = False,
    request_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Generate one WAV and a JSON provenance sidecar; never retries a request."""
    output_path = output_path.expanduser().resolve()
    metadata_path = output_path.with_suffix(output_path.suffix + ".json")
    if output_path.suffix.lower() != ".wav":
        raise NarrationError("Output filename must end in .wav.")
    if not overwrite and (output_path.exists() or metadata_path.exists()):
        raise NarrationError(
            f"Output already exists: {output_path}. Use --overwrite to replace it."
        )

    try:
        from google import genai
    except ImportError as exc:
        raise NarrationError(
            "Missing dependency. Install requirements.txt in the active Python environment."
        ) from exc

    if request_timeout_seconds is None:
        raw_timeout = os.environ.get("GEMINI_TTS_TIMEOUT_SECONDS", "180").strip()
        try:
            request_timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise NarrationError("GEMINI_TTS_TIMEOUT_SECONDS must be numeric.") from exc
    if request_timeout_seconds <= 0 or request_timeout_seconds > 600:
        raise NarrationError("TTS request timeout must be greater than 0 and at most 600 seconds.")

    def request() -> Any:
        client = genai.Client(api_key=api_key)
        return client.interactions.create(
            model=model,
            input=[
                {
                    "type": "user_input",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                            "annotations": [
                                {"type": "speech_metadata", "style": style}
                            ],
                        }
                    ],
                }
            ],
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice}]},
        )

    try:
        interaction = _request_with_timeout(request, request_timeout_seconds)
    except NarrationError:
        raise
    except Exception as exc:  # SDK exceptions vary; do not expose request details or secrets.
        raise NarrationError(
            "Google TTS request failed. Check the API key, model access, quota, and connection. "
            "No automatic retry was made."
        ) from exc

    audio = _extract_audio(interaction)
    duration_seconds = round(_wav_duration(audio), 3)
    _atomic_write(output_path, audio)

    metadata = {
        "provider": "Google Gemini API",
        "model": model,
        "voice": voice,
        "style": style,
        "format": "WAV / 24 kHz mono PCM as returned by Gemini TTS",
        "language": "en-US",
        "duration_seconds": duration_seconds,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(interaction, "id", None),
    }
    _atomic_write(
        metadata_path,
        (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a standalone WAV narration for the independent Shorts project."
    )
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 text script file")
    parser.add_argument("--output", required=True, type=Path, help="Output .wav path")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini TTS model (default: {DEFAULT_MODEL})")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Gemini prebuilt voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--style", default=DEFAULT_STYLE, help="Short delivery direction for the narrator")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing WAV and metadata sidecar")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "replace_with_your_own_key":
        print("Error: set GEMINI_API_KEY in your environment. Do not paste the key into this script.", file=sys.stderr)
        return 2

    try:
        text = _read_script(args.input)
        result = generate_narration(
            text,
            args.output,
            api_key=api_key,
            model=args.model,
            voice=args.voice,
            style=args.style,
            overwrite=args.overwrite,
        )
    except NarrationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Narration saved: {args.output.expanduser().resolve()}")
    print(f"Duration: {result['duration_seconds']:.2f} seconds")
    print(f"Model: {result['model']} | Voice: {result['voice']}")
    print(f"Metadata: {args.output.expanduser().resolve()}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
