import json
import tempfile
import unittest
from pathlib import Path

from production.canonical_config import CANONICAL_PROFILE_FINGERPRINT
from production.v7_contract import PROMPT_SHA256, validate_manifest, validate_prompt_and_schema


ROOT = Path(__file__).resolve().parents[1]


class V7ContractTests(unittest.TestCase):
    def test_prompt_schema_and_manifest_are_canonical(self):
        prompt = validate_prompt_and_schema(ROOT)
        self.assertEqual(prompt["prompt_sha256"], PROMPT_SHA256)
        manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))
        result = validate_manifest(manifest, require_production=True)
        self.assertEqual(result["status"], "V7_MANIFEST_PASS")

    def test_wrong_profile_is_rejected(self):
        manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))
        manifest["engine_profile_fingerprint"] = "0" * 64
        with self.assertRaises(Exception):
            validate_manifest(manifest)

    def test_template_is_contract_valid_without_assets(self):
        manifest = json.loads((ROOT / "examples/video-only-episode-manifest-v7.template.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["engine_profile_fingerprint"], CANONICAL_PROFILE_FINGERPRINT)
        self.assertEqual(validate_manifest(manifest)["scene_count"], 0)


if __name__ == "__main__":
    unittest.main()
