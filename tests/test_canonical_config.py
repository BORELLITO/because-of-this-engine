import copy
import json
import unittest
from pathlib import Path

from production.canonical_config import (
    CANONICAL_PROFILE_FINGERPRINT,
    CANONICAL_PROFILE_ID,
    CanonicalConfigError,
    validate_canonical_manifest,
)


class CanonicalConfigTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def _load(self, relative: str) -> dict:
        return json.loads((self.ROOT / relative).read_text(encoding="utf-8"))

    def test_template_and_live_manifests_use_the_locked_profile(self):
        paths = (
            "examples/video-only-episode-manifest-v2.template.json",
            "episodes/episode-001/manifest.json",
            "episodes/episode-002/manifest.json",
            "episodes/episode-003/manifest.json",
            "episodes/episode-003/manifest.draft.json",
        )
        for relative in paths:
            report = validate_canonical_manifest(self._load(relative), source_label=relative)
            self.assertEqual(report["profile_id"], CANONICAL_PROFILE_ID)
            self.assertEqual(report["profile_fingerprint"], CANONICAL_PROFILE_FINGERPRINT)

    def test_any_profile_drift_is_blocked(self):
        manifest = self._load("episodes/episode-001/manifest.json")
        manifest["brand"]["logo_width"] = 432
        with self.assertRaisesRegex(CanonicalConfigError, "brand.logo_width"):
            validate_canonical_manifest(manifest)

    def test_legacy_or_missing_profile_is_blocked(self):
        manifest = self._load("episodes/episode-001/manifest.json")
        manifest.pop("engine_profile")
        with self.assertRaisesRegex(CanonicalConfigError, "Legacy or missing profiles are blocked"):
            validate_canonical_manifest(manifest)

    def test_no_live_manifest_retains_known_legacy_settings(self):
        paths = [
            self.ROOT / "examples" / "video-only-episode-manifest-v2.template.json",
            *sorted((self.ROOT / "episodes").glob("*/manifest.json")),
        ]
        forbidden = ('"watermark_enabled": true', '"logo_width": 432', '"volume": 0.06')
        for path in paths:
            content = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, content, f"{value} remains in {path}")

    def test_fixed_visual_identity_locks_cannot_drift(self):
        manifest = self._load("episodes/episode-003/manifest.json")
        cases = (
            ("brand", "logo_anchor", "top_right", "brand.logo_anchor"),
            ("captions", "style", {**manifest["captions"]["style"], "alignment": 7}, "captions.style.alignment"),
            ("loop", "logo_width", 900, "loop.logo_width"),
        )
        for section, key, value, expected in cases:
            changed = copy.deepcopy(manifest)
            changed[section][key] = value
            with self.assertRaisesRegex(CanonicalConfigError, expected):
                validate_canonical_manifest(changed)

    def test_profile_fingerprint_changes_if_profile_changes(self):
        manifest = self._load("episodes/episode-001/manifest.json")
        changed = copy.deepcopy(manifest)
        changed["music"]["volume"] = 0.06
        with self.assertRaises(CanonicalConfigError):
            validate_canonical_manifest(changed)


if __name__ == "__main__":
    unittest.main()
