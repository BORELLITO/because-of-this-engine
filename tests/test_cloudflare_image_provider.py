from __future__ import annotations

import base64
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "cloudflare_image_provider.py"
IMAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "image_provider.py"
IMAGE_SPEC = importlib.util.spec_from_file_location("image_provider", IMAGE_MODULE_PATH)
image_provider = importlib.util.module_from_spec(IMAGE_SPEC)
assert IMAGE_SPEC.loader is not None
sys.modules[IMAGE_SPEC.name] = image_provider
IMAGE_SPEC.loader.exec_module(image_provider)
SPEC = importlib.util.spec_from_file_location("cloudflare_image_provider", MODULE_PATH)
provider_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = provider_module
SPEC.loader.exec_module(provider_module)


def make_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (512, 512), (12, 24, 48)).save(buffer, format="PNG")
    return buffer.getvalue()


class CloudflareProviderTests(unittest.TestCase):
    def test_extracts_base64_image(self) -> None:
        payload = make_png()
        response = json.dumps({"success": True, "result": {"image": base64.b64encode(payload).decode("ascii")}}).encode()
        self.assertEqual(provider_module.CloudflareImageProvider._extract_payload(response), payload)

    def test_missing_credentials_are_rejected(self) -> None:
        with self.assertRaises(provider_module.ImageGenerationError):
            provider_module.CloudflareImageProvider(account_id="", api_token="")

    def test_quota_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = provider_module.CloudflareImageProvider(
                account_id="account", api_token="token", quota_ledger=Path(temp_dir) / "usage.json", max_requests_per_day=1
            )
            provider._reserve_request()
            with self.assertRaises(provider_module.ImageGenerationError):
                provider._reserve_request()


if __name__ == "__main__":
    unittest.main()
