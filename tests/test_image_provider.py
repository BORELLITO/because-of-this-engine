from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "image_provider.py"
SPEC = importlib.util.spec_from_file_location("image_provider", MODULE_PATH)
image_provider = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = image_provider
SPEC.loader.exec_module(image_provider)


def make_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (512, 512), (12, 24, 48)).save(buffer, format="PNG")
    return buffer.getvalue()


class ImageProviderTests(unittest.TestCase):
    def test_generates_image_and_sidecar_once_with_mocked_api(self) -> None:
        payload = make_png()
        calls: list[dict] = []

        class FakeInteractions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return types.SimpleNamespace(
                    id="image-request-id",
                    output_image=types.SimpleNamespace(data=base64.b64encode(payload).decode("ascii")),
                )

        class FakeClient:
            def __init__(self, *, api_key: str):
                self.interactions = FakeInteractions()

        fake_google = types.ModuleType("google")
        fake_google.genai = types.SimpleNamespace(Client=FakeClient)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "s01.png"
            with patch.dict(os.environ, {"GEMINI_ALLOW_IMAGE_BILLING": "1"}), patch.dict(sys.modules, {"google": fake_google}):
                provider = image_provider.GeminiImageProvider(
                    api_key="test-key-never-sent", quota_ledger=root / "usage.json", max_requests_per_day=1
                )
                result = provider.generate(image_provider.ImageRequest("S01", "A test prompt", output))

            self.assertEqual(output.read_bytes(), payload)
            sidecar = json.loads(output.with_suffix(".png.json").read_text())
            self.assertEqual(result["request_id"], "image-request-id")
            self.assertEqual(sidecar["scene_id"], "S01")
            self.assertEqual(calls[0]["model"], image_provider.DEFAULT_MODEL)
            self.assertEqual(calls[0]["response_format"]["aspect_ratio"], "9:16")
            usage = json.loads((root / "usage.json").read_text())
            self.assertEqual(next(iter(usage["days"].values()))["requests"], 1)

    def test_premium_is_blocked_without_explicit_opt_in(self) -> None:
        with patch.dict(os.environ, {"GEMINI_ALLOW_IMAGE_BILLING": "1"}, clear=True):
            with self.assertRaises(image_provider.ImageGenerationError):
                image_provider.GeminiImageProvider(api_key="test-key", model=image_provider.PREMIUM_MODEL)

    def test_daily_guard_stops_before_second_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.dict(os.environ, {"GEMINI_ALLOW_IMAGE_BILLING": "1"}):
                provider = image_provider.GeminiImageProvider(
                    api_key="test-key", quota_ledger=root / "usage.json", max_requests_per_day=1
                )
            provider._reserve_request()
            with self.assertRaises(image_provider.ImageGenerationError):
                provider._reserve_request()


if __name__ == "__main__":
    unittest.main()
