#!/usr/bin/env python3
"""Safe Gemini image-generation adapter for the independent Shorts engine.

This module is deliberately isolated from every other project engine.  It
generates one approved image asset at a time, writes a provenance sidecar,
and fails closed before a request when the local quota guard is exhausted.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "gemini-nano-banana-2.1"
PREMIUM_MODEL = "gemini-3-pro-image"
ALLOWED_MODELS = {
    "gemini-nano-banana-2.1",
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
}


class ImageGenerationError(RuntimeError):
    """Raised for a blocked, failed, or invalid image generation."""


@dataclass(frozen=True)
class ImageRequest:
    scene_id: str
    prompt: str
    output_path: Path
    aspect_ratio: str = "9:16"
    image_size: str = "1K"
    overwrite: bool = False


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        raise ImageGenerationError(f"Could not safely write {path}") from exc


def _read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "days": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImageGenerationError(f"Image quota ledger is unreadable: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("days", {}), dict):
        raise ImageGenerationError(f"Image quota ledger has an invalid schema: {path}")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    _atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _validate_image(data: bytes) -> tuple[str, int, int]:
    if not data:
        raise ImageGenerationError("The image response was empty.")
    try:
        from PIL import Image

        with Image.open(__import__("io").BytesIO(data)) as image:
            image.load()
            width, height = image.size
            if width < 512 or height < 512:
                raise ImageGenerationError(f"Generated image is too small: {width}x{height}.")
            return image.format or "unknown", width, height
    except ImageGenerationError:
        raise
    except Exception as exc:
        raise ImageGenerationError("The API output was not a readable PNG/JPEG image.") from exc


def _extract_image(interaction: Any) -> bytes:
    try:
        encoded = interaction.output_image.data
    except (AttributeError, TypeError) as exc:
        raise ImageGenerationError("The API response did not contain a generated image.") from exc
    if not encoded:
        raise ImageGenerationError("The API returned an empty image payload.")
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ImageGenerationError("The API returned image data in an unexpected format.") from exc


class GeminiImageProvider:
    """One-request-at-a-time Gemini image provider with a local quota guard."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        quota_ledger: Path | None = None,
        max_requests_per_day: int = 6,
    ) -> None:
        if not api_key or api_key == "replace_with_your_own_key":
            raise ImageGenerationError("Set GEMINI_API_KEY in the environment; never paste it into source code.")
        if model not in ALLOWED_MODELS:
            raise ImageGenerationError(f"Unsupported image model: {model}")
        if os.environ.get("GEMINI_ALLOW_IMAGE_BILLING") != "1":
            raise ImageGenerationError(
                "Gemini image API generation is blocked because its current API pricing has no free tier. "
                "Set GEMINI_ALLOW_IMAGE_BILLING=1 only after confirming the intended budget."
            )
        if model == PREMIUM_MODEL and os.environ.get("GEMINI_ALLOW_PREMIUM_IMAGE") != "1":
            raise ImageGenerationError(
                "Premium image generation is blocked by default. Set GEMINI_ALLOW_PREMIUM_IMAGE=1 "
                "only after confirming billing and the intended cost."
            )
        if max_requests_per_day < 1:
            raise ImageGenerationError("max_requests_per_day must be at least 1.")
        self.api_key = api_key
        self.model = model
        self.quota_ledger = quota_ledger or Path("production/image-generation-usage.json")
        self.max_requests_per_day = max_requests_per_day

    def _reserve_request(self) -> tuple[str, int]:
        today = datetime.now(timezone.utc).date().isoformat()
        ledger = _read_ledger(self.quota_ledger)
        day = ledger.setdefault("days", {}).setdefault(today, {"requests": 0, "models": {}})
        used = int(day.get("requests", 0))
        if used >= self.max_requests_per_day:
            raise ImageGenerationError(
                f"Local image quota guard stopped the run: {used}/{self.max_requests_per_day} requests used today."
            )
        day["requests"] = used + 1
        models = day.setdefault("models", {})
        models[self.model] = int(models.get(self.model, 0)) + 1
        _write_json_atomic(self.quota_ledger, ledger)
        return today, used + 1

    def generate(self, request: ImageRequest) -> dict[str, Any]:
        output_path = request.output_path.expanduser().resolve()
        sidecar_path = output_path.with_suffix(output_path.suffix + ".json")
        if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ImageGenerationError("Image output must be .png, .jpg, or .jpeg.")
        if not request.overwrite and (output_path.exists() or sidecar_path.exists()):
            raise ImageGenerationError(f"Output already exists: {output_path}. Use --overwrite deliberately.")
        if request.aspect_ratio not in {"9:16", "16:9", "1:1", "4:5", "3:4", "4:3", "5:4", "2:3", "3:2", "21:9"}:
            raise ImageGenerationError(f"Unsupported aspect ratio: {request.aspect_ratio}")
        if request.image_size not in {"1K", "2K", "4K"}:
            raise ImageGenerationError("image_size must be 1K, 2K, or 4K.")

        day, request_number = self._reserve_request()
        try:
            from google import genai
        except ImportError as exc:
            raise ImageGenerationError("Missing google-genai. Install requirements.txt first.") from exc

        try:
            client = genai.Client(api_key=self.api_key)
            interaction = client.interactions.create(
                model=self.model,
                input=request.prompt,
                response_format={
                    "type": "image",
                    "mime_type": "image/png",
                    "aspect_ratio": request.aspect_ratio,
                    "image_size": request.image_size,
                },
            )
        except Exception as exc:  # SDK exceptions vary; never expose request details or secrets.
            raise ImageGenerationError(
                "Gemini image request failed. Check API access, model availability, quota, and billing. "
                "The local quota guard counted this attempt; no automatic retry was made."
            ) from exc

        data = _extract_image(interaction)
        image_format, width, height = _validate_image(data)
        _atomic_write(output_path, data)
        metadata = {
            "schema_version": "1.0",
            "provider": "Google Gemini native image generation",
            "model": self.model,
            "scene_id": request.scene_id,
            "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
            "prompt": request.prompt,
            "aspect_ratio": request.aspect_ratio,
            "requested_image_size": request.image_size,
            "format": image_format,
            "width": width,
            "height": height,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(interaction, "id", None),
            "quota_guard": {"utc_day": day, "request_number": request_number, "daily_limit": self.max_requests_per_day},
        }
        _write_json_atomic(sidecar_path, metadata)
        return metadata
