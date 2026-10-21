#!/usr/bin/env python3
"""Cloudflare Workers AI image provider for the free-first path."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from image_provider import ImageGenerationError, ImageRequest, _atomic_write, _validate_image, _write_json_atomic

DEFAULT_MODEL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"


class CloudflareImageProvider:
    """One-request-at-a-time Cloudflare provider with a local quota guard."""

    def __init__(self, *, account_id: str, api_token: str, model: str = DEFAULT_MODEL, quota_ledger: Path | None = None, max_requests_per_day: int = 6) -> None:
        if not account_id or not api_token:
            raise ImageGenerationError("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN first.")
        if max_requests_per_day < 1:
            raise ImageGenerationError("max_requests_per_day must be at least 1.")
        self.account_id = account_id
        self.api_token = api_token
        self.model = model
        self.quota_ledger = quota_ledger or Path("production/image-generation-usage.json")
        self.max_requests_per_day = max_requests_per_day

    def _reserve_request(self) -> tuple[str, int]:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.quota_ledger.exists():
            try:
                ledger = json.loads(self.quota_ledger.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ImageGenerationError(f"Image quota ledger is unreadable: {self.quota_ledger}") from exc
        else:
            ledger = {"schema_version": 1, "days": {}}
        if not isinstance(ledger, dict) or not isinstance(ledger.get("days", {}), dict):
            raise ImageGenerationError(f"Image quota ledger has an invalid schema: {self.quota_ledger}")
        day = ledger.setdefault("days", {}).setdefault(today, {"requests": 0, "models": {}})
        used = int(day.get("requests", 0))
        if used >= self.max_requests_per_day:
            raise ImageGenerationError(f"Local image quota guard stopped the run: {used}/{self.max_requests_per_day} requests used today.")
        day["requests"] = used + 1
        day.setdefault("models", {})[self.model] = int(day["models"].get(self.model, 0)) + 1
        _write_json_atomic(self.quota_ledger, ledger)
        return today, used + 1

    @staticmethod
    def _extract_payload(response: bytes) -> bytes:
        try:
            decoded = json.loads(response.decode("utf-8"))
            encoded = decoded.get("result", {}).get("image") or decoded.get("image")
            if not encoded:
                raise ImageGenerationError("Cloudflare response did not contain result.image.")
            return base64.b64decode(encoded, validate=True)
        except ImageGenerationError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise ImageGenerationError("Cloudflare returned an invalid image response.") from exc

    def generate(self, request: ImageRequest, *, negative_prompt: str = "text, letters, watermark, logo, extra planets, abstract geometry") -> dict[str, Any]:
        output_path = request.output_path.expanduser().resolve()
        sidecar_path = output_path.with_suffix(output_path.suffix + ".json")
        if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ImageGenerationError("Image output must be .png, .jpg, or .jpeg.")
        if not request.overwrite and (output_path.exists() or sidecar_path.exists()):
            raise ImageGenerationError(f"Output already exists: {output_path}. Use --overwrite deliberately.")
        day, request_number = self._reserve_request()
        endpoint = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}".format(
            urllib.parse.quote(self.account_id, safe=""), urllib.parse.quote(self.model, safe="@/")
        )
        body = json.dumps({
            "prompt": request.prompt,
            "negative_prompt": negative_prompt,
            "width": 1024,
            "height": 1792,
            "num_steps": 20,
            "seed": int(hashlib.sha256(request.scene_id.encode("utf-8")).hexdigest()[:8], 16),
        }).encode("utf-8")
        http_request = urllib.request.Request(endpoint, data=body, headers={"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(http_request, timeout=180) as response:
                payload = response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise ImageGenerationError("Cloudflare image request failed. Check token, account, model access, and free quota.") from exc
        image_bytes = self._extract_payload(payload)
        image_format, width, height = _validate_image(image_bytes)
        _atomic_write(output_path, image_bytes)
        metadata = {
            "schema_version": "1.0", "provider": "Cloudflare Workers AI", "model": self.model,
            "scene_id": request.scene_id, "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
            "prompt": request.prompt, "negative_prompt": negative_prompt,
            "requested_dimensions": {"width": 1024, "height": 1792}, "format": image_format,
            "width": width, "height": height, "bytes": len(image_bytes),
            "sha256": hashlib.sha256(image_bytes).hexdigest(), "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "quota_guard": {"utc_day": day, "request_number": request_number, "daily_limit": self.max_requests_per_day},
            "license_review": "Verify the model license before commercial monetization.",
        }
        _write_json_atomic(sidecar_path, metadata)
        return metadata
