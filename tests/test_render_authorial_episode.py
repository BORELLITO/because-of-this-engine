import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.render_authorial_episode import (
    RenderError,
    SIZES,
    scene_filter,
    validate_manifest,
    xfade_filter,
)


class AuthorialRenderTests(unittest.TestCase):
    def _manifest(self, root: Path) -> dict:
        audio = root / "voice.wav"
        audio.write_bytes(b"placeholder")
        for name in ("s01.png", "s02.png"):
            (root / name).write_bytes(b"image")
        return {
            "video_id": "demo-001",
            "audio": {"path": "voice.wav"},
            "scenes": [
                {"scene_id": "S01", "image": "s01.png", "duration": 4.6, "zoom_end": 1.08},
                {"scene_id": "S02", "image": "s02.png", "duration": 4.6, "zoom_end": 1.07},
            ],
            "transition_duration": 0.33,
        }

    def test_preview_and_final_sizes_are_explicit(self):
        self.assertEqual(SIZES["preview"], (1080, 1920))
        self.assertEqual(SIZES["final"], (2160, 3840))

    def test_scene_filter_has_smooth_zoom_and_fixed_fps(self):
        value = scene_filter(1080, 1920, 115, 1.08)
        self.assertIn("zoompan", value)
        self.assertIn("d=115", value)
        self.assertIn("fps=25", value)

    def test_xfade_offsets_account_for_previous_transitions(self):
        value = xfade_filter(3, [4.6, 4.6, 4.6], 0.33)
        self.assertIn("offset=4.270", value)
        self.assertIn("offset=8.540", value)

    def test_missing_scene_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self._manifest(root)
            manifest["scenes"][1]["image"] = "missing.png"
            with self.assertRaises(RenderError):
                validate_manifest(manifest, root)

    def test_validate_only_requires_real_wav_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self._manifest(root)
            with patch("production.render_authorial_episode.wave.open") as opener:
                wav = opener.return_value.__enter__.return_value
                wav.getnchannels.return_value = 1
                wav.getsampwidth.return_value = 2
                wav.getframerate.return_value = 24000
                wav.getnframes.return_value = 24000
                spec = validate_manifest(manifest, root)
                self.assertEqual(spec["audio_duration"], 1.0)


if __name__ == "__main__":
    unittest.main()
