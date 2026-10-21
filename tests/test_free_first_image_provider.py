from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "image_provider.py"
SPEC = importlib.util.spec_from_file_location("image_provider", MODULE_PATH)
image_provider = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = image_provider
SPEC.loader.exec_module(image_provider)

POLICY_PATH = Path(__file__).resolve().parents[1] / "production" / "free_first_image_provider.py"
POLICY_SPEC = importlib.util.spec_from_file_location("free_first_image_provider", POLICY_PATH)
policy = importlib.util.module_from_spec(POLICY_SPEC)
assert POLICY_SPEC.loader is not None
sys.modules[POLICY_SPEC.name] = policy
POLICY_SPEC.loader.exec_module(policy)


class FreeFirstProviderTests(unittest.TestCase):
    def request(self, root: Path):
        return image_provider.ImageRequest(
            scene_id="S01",
            prompt="test prompt",
            output_path=root / "s01.png",
        )

    def test_factual_source_is_selected_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            class Factual:
                def generate(self, request, *, query):
                    return {"provider": "NASA", "width": 1080, "height": 1920}

            class Generative:
                def generate(self, request):
                    raise AssertionError("generative provider must not be called")

            result = policy.FreeFirstImageProvider(
                factual_provider=Factual(),
                generative_provider=Generative(),
            ).generate(self.request(root), query="Mars")
            self.assertEqual(result["selected_source"], "factual_primary")
            self.assertTrue(result["human_review_required"])
            sidecar = json.loads((root / "s01.png.json").read_text())
            self.assertEqual(sidecar["selection_policy"], "free-first-v1")

    def test_fallback_requires_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            class Factual:
                def generate(self, request, *, query):
                    raise image_provider.ImageGenerationError("factual unavailable")

            class Generative:
                def generate(self, request):
                    return {"provider": "Cloudflare", "width": 1024, "height": 1792}

            with self.assertRaises(image_provider.ImageGenerationError):
                policy.FreeFirstImageProvider(
                    factual_provider=Factual(),
                    generative_provider=Generative(),
                ).generate(self.request(root), query="Mars")

    def test_enabled_fallback_is_marked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            class Factual:
                def generate(self, request, *, query):
                    raise image_provider.ImageGenerationError("factual unavailable")

            class Generative:
                def generate(self, request):
                    return {"provider": "Cloudflare", "width": 1024, "height": 1792}

            result = policy.FreeFirstImageProvider(
                factual_provider=Factual(),
                generative_provider=Generative(),
                allow_generative_fallback=True,
            ).generate(self.request(root), query="Mars")
            self.assertEqual(result["selected_source"], "generative_fallback")
            self.assertEqual(result["fallback_reason"], "factual_provider_error")


if __name__ == "__main__":
    unittest.main()
