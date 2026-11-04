"""Regression: canonical fingerprint must match policy and active episode manifest."""
import json
import unittest
from pathlib import Path

from production.canonical_config import CANONICAL_PROFILE_FINGERPRINT, CANONICAL_PROFILE_ID

ROOT = Path(__file__).resolve().parents[2]


class FingerprintV11Tests(unittest.TestCase):
    def test_policy_matches_canonical_python_config(self):
        policy = json.loads((ROOT / "production/active_engine_policy.json").read_text())
        self.assertEqual(policy["active_engine_profile"], CANONICAL_PROFILE_ID)
        self.assertEqual(policy["active_engine_fingerprint"], CANONICAL_PROFILE_FINGERPRINT)

    def test_episode004_manifest_matches_current_profile(self):
        manifest = json.loads((ROOT / "episodes/video-004/preview-manifest.json").read_text())
        self.assertEqual(manifest["engine_profile"], CANONICAL_PROFILE_ID)
        self.assertEqual(manifest["engine_profile_fingerprint"], CANONICAL_PROFILE_FINGERPRINT)


if __name__ == "__main__":
    unittest.main()
