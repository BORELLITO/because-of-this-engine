#!/usr/bin/env python3
"""Generate one narration WAV through Google's Gemini TTS API.

The production path uses the documented Interactions REST endpoint so
that narration uses the provider's supported unary audio contract and actionable HTTP errors. The
legacy SDK path remains available only as an explicit fallback via
``GEMINI_TTS_TRANSPORT=sdk``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import queue
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-3.8-flash-tts"
DEFAULT_VOICE = "Charon"
DEFAULT_TRANSPORT = "rest_unary"
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_STYLE = (
    "Neutral American English documentary narration. Clear, natural, "
    "steady pace with restrained emphasis; informative, not theatrical."
)
INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


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


def _decode_base64_audio(encoded: Any) -> bytes:
    if not encoded:
        raise NarrationError("The API returned an empty audio payload.")
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise NarrationError("The API returned audio in an unexpected format.") from exc
    if not audio:
        raise NarrationError("The API returned an empty audio payload.")
    return audio


def _extract_audio(interaction: Any) -> bytes:
    """Extract and validate a complete WAV from the SDK convenience property."""
    try:
        encoded = interaction.output_audio.data
    except (AttributeError, TypeError) as exc:
        raise NarrationError("The API response did not contain generated audio.") from exc
    audio = _decode_base64_audio(encoded)
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise NarrationError("The API output was not a valid WAV file.")
    return audio


def _pcm_to_wav(pcm: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    if not pcm:
        raise NarrationError("The streaming API returned no PCM audio.")
    if len(pcm) % 2:
        raise NarrationError("The streaming API returned an incomplete PCM sample.")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


def _wav_duration(audio: bytes) -> float:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            if wav_file.getframerate() <= 0:
                raise NarrationError("The WAV file has an invalid sample rate.")
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise NarrationError("The WAV file must be mono 16-bit PCM.")
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
        except BaseException as exc:  # SDK and urllib exception types vary.
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


def _request_payload(text: str, model: str, voice: str, style: str) -> bytes:
    payload = {
        "model": model,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [{"type": "speech_metadata", "style": style}],
                    }
                ],
            }
        ],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _error_detail(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return "empty provider response"
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return text[:400]
    if isinstance(value, dict):
        error = value.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)[:400]
        if value.get("message"):
            return str(value["message"])[:400]
    return text[:400]


def _http_error(exc: urllib.error.HTTPError) -> NarrationError:
    detail = _error_detail(exc.read(8192))
    status = int(exc.code)
    if status in {401, 403}:
        category = "authentication_or_permission"
    elif status == 429:
        category = "quota_or_rate_limit"
    elif 500 <= status <= 599:
        category = "provider_server_error"
    else:
        category = "request_rejected"
    return NarrationError(f"Google TTS HTTP {status} [{category}]: {detail}")


def _audio_from_stream_event(value: Any) -> tuple[bytes | None, str | None, str | None]:
    """Return (audio, request_id, error) from one Interactions SSE event."""
    if not isinstance(value, dict):
        return None, None, None
    request_id = value.get("id") if isinstance(value.get("id"), str) else None
    error = value.get("error")
    if error:
        if isinstance(error, dict):
            error = error.get("message") or json.dumps(error, ensure_ascii=False)
        return None, request_id, str(error)
    status = value.get("status")
    if status in {"failed", "error"}:
        return None, request_id, str(value.get("message") or "provider marked interaction as failed")

    candidates = [value.get("delta"), value.get("content")]
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("type") == "audio":
            encoded = candidate.get("data")
            return _decode_base64_audio(encoded), request_id, None
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict) and item.get("type") == "audio":
                    return _decode_base64_audio(item.get("data")), request_id, None
    if value.get("type") == "audio":
        return _decode_base64_audio(value.get("data")), request_id, None
    return None, request_id, None


def _rest_audio_from_response(value: Any) -> tuple[bytes, str | None]:
    """Extract the last model audio block from the documented REST response."""
    if not isinstance(value, dict):
        raise NarrationError("Google TTS returned a non-object REST response.")
    request_id = value.get("id") if isinstance(value.get("id"), str) else None
    error = value.get("error")
    if error:
        if isinstance(error, dict):
            error = error.get("message") or json.dumps(error, ensure_ascii=False)
        raise NarrationError(f"Google TTS REST interaction failed: {str(error)[:400]}")

    candidates: list[Any] = []
    output_audio = value.get("output_audio")
    if isinstance(output_audio, dict):
        candidates.append(output_audio)
    steps = value.get("steps")
    if isinstance(steps, list):
        for step in reversed(steps):
            if not isinstance(step, dict):
                continue
            if step.get("type") not in {"model_output", "audio"}:
                continue
            content = step.get("content")
            if isinstance(content, list):
                candidates.extend(reversed(content))
            elif isinstance(content, dict):
                candidates.append(content)

    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("type") == "audio":
            return _decode_base64_audio(candidate.get("data")), request_id
        if isinstance(candidate, dict) and candidate.get("data"):
            return _decode_base64_audio(candidate.get("data")), request_id
    raise NarrationError(
        "Google TTS REST response completed without audio. "
        "Check model access, voice name and API availability."
    )


def _request_rest_stream(
    text: str,
    *,
    api_key: str,
    model: str,
    voice: str,
    style: str,
    timeout_seconds: float,
) -> tuple[bytes, str | None]:
    """Call the documented unary Interactions REST endpoint.

    The provider documentation returns a complete WAV in a JSON response
    (steps[].content[].data or output_audio.data). The old implementation
    advertised SSE streaming and waited on an unsupported stream contract,
    which caused the 180-second timeout seen in production.
    """
    request = urllib.request.Request(
        INTERACTIONS_URL,
        data=_request_payload(text, model, voice, style),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    socket_timeout = max(1.0, min(600.0, timeout_seconds))
    try:
        with urllib.request.urlopen(request, timeout=socket_timeout) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read()
            if status >= 400:
                raise NarrationError(f"Google TTS returned unexpected HTTP status {status}.")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise NarrationError("Google TTS returned malformed JSON.") from exc
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, socket.timeout):
            raise NarrationError(f"Google TTS request timed out after {timeout_seconds:.1f} seconds.") from exc
        raise NarrationError(f"Google TTS network error: {reason}") from exc
    except socket.timeout as exc:
        raise NarrationError(f"Google TTS request timed out after {timeout_seconds:.1f} seconds.") from exc

    audio, request_id = _rest_audio_from_response(value)
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise NarrationError(
            "Google TTS returned audio without a valid WAV container. "
            "The v2 pipeline requires the documented audio/wav response."
        )
    return audio, request_id

def _request_sdk_audio(
    text: str,
    *,
    api_key: str,
    model: str,
    voice: str,
    style: str,
    timeout_seconds: float,
) -> tuple[bytes, str | None]:
    try:
        from google import genai
    except ImportError as exc:
        raise NarrationError(
            "Missing dependency. Install requirements.txt in the active Python environment."
        ) from exc

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
                            "annotations": [{"type": "speech_metadata", "style": style}],
                        }
                    ],
                }
            ],
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice}]},
        )

    try:
        interaction = _request_with_timeout(request, timeout_seconds)
    except NarrationError:
        raise
    except Exception as exc:
        raise NarrationError(
            "Google TTS SDK request failed. Use GEMINI_TTS_TRANSPORT=rest_stream for "
            "explicit HTTP diagnostics. No automatic retry was made."
        ) from exc
    return _extract_audio(interaction), getattr(interaction, "id", None)


def _request_audio(
    text: str,
    *,
    api_key: str,
    model: str,
    voice: str,
    style: str,
    timeout_seconds: float,
    transport: str,
) -> tuple[bytes, str | None]:
    if transport in {"rest_unary", "rest_stream"}:
        return _request_with_timeout(
            lambda: _request_rest_stream(
                text,
                api_key=api_key,
                model=model,
                voice=voice,
                style=style,
                timeout_seconds=timeout_seconds,
            ),
            timeout_seconds,
        )
    if transport == "sdk":
        return _request_sdk_audio(
            text,
            api_key=api_key,
            model=model,
            voice=voice,
            style=style,
            timeout_seconds=timeout_seconds,
        )
    raise NarrationError(
        f"Unsupported GEMINI_TTS_TRANSPORT={transport!r}. Use rest_unary or sdk."
    )


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
    transport: str | None = None,
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
    if request_timeout_seconds is None:
        raw_timeout = os.environ.get("GEMINI_TTS_TIMEOUT_SECONDS", "180").strip()
        try:
            request_timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise NarrationError("GEMINI_TTS_TIMEOUT_SECONDS must be numeric.") from exc
    if request_timeout_seconds <= 0 or request_timeout_seconds > 600:
        raise NarrationError("TTS request timeout must be greater than 0 and at most 600 seconds.")
    selected_transport = (transport or os.environ.get("GEMINI_TTS_TRANSPORT", DEFAULT_TRANSPORT)).strip().lower()

    audio, request_id = _request_audio(
        text,
        api_key=api_key,
        model=model,
        voice=voice,
        style=style,
        timeout_seconds=request_timeout_seconds,
        transport=selected_transport,
    )
    duration_seconds = round(_wav_duration(audio), 3)
    _atomic_write(output_path, audio)

    metadata = {
        "provider": "Google Gemini API",
        "model": model,
        "voice": voice,
        "style": style,
        "transport": selected_transport,
        "format": "WAV / 24 kHz mono PCM",
        "language": "en-US",
        "duration_seconds": duration_seconds,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
    }
    _atomic_write(
        metadata_path,
        (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a standalone WAV narration for the Shorts project.")
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 text script file")
    parser.add_argument("--output", required=True, type=Path, help="Output .wav path")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini TTS model (default: {DEFAULT_MODEL})")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Gemini prebuilt voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--style", default=DEFAULT_STYLE, help="Short delivery direction for the narrator")
    parser.add_argument("--transport", default=None, help="TTS transport: rest_unary (default) or sdk")
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
            transport=args.transport,
        )
    except NarrationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Narration saved: {args.output.expanduser().resolve()}")
    print(f"Duration: {result['duration_seconds']:.2f} seconds")
    print(f"Model: {result['model']} | Voice: {result['voice']} | Transport: {result['transport']}")
    print(f"Metadata: {args.output.expanduser().resolve()}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
