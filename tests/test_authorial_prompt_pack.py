from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "build_authorial_prompt_pack.py"
SPEC = importlib.util.spec_from_file_location("build_authorial_prompt_pack", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class AuthorialPromptPackTests(unittest.TestCase):
    def test_builds_cartoon_cinematic_prompt_pack(self) -> None:
        root = Path(__file__).resolve().parents[1]
        style = module._read_json(root / "production" / "authorial-style-because-of-this-v1.json")
        manifest = module._read_json(root / "examples" / "mars-climate-orbiter-authorial-manifest-v1.json")
        result = module.build_pack(manifest, style)
        self.assertEqual(result["visual_style_id"], "because-of-this-cinematic-cartoon-v1")
        self.assertEqual(len(result["scenes"]), 6)
        self.assertIn("Premium cinematic editorial cartoon", result["scenes"][0]["prompt"])
        self.assertIn("no text", result["scenes"][0]["prompt"].lower())
        self.assertTrue(result["human_review_required"])


if __name__ == "__main__":
    unittest.main()
