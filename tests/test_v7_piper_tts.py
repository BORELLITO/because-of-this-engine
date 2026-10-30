import json
import tempfile
import unittest
from pathlib import Path

from production.piper_tts import PiperTTSError, build_text, profile_from_manifest, synthesize_chunks

ROOT = Path(__file__).resolve().parents[1]


class V7PiperTTSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))

    def test_profile_is_piper_tts_only(self):
        profile = profile_from_manifest(self.manifest)
        self.assertEqual(profile["provider"], "piper_tts_local")
        self.assertEqual(profile["voice_name"], "en_US-ryan-high")
        self.assertEqual(profile["language_code"], "en-US")

    def test_text_normalization_and_local_substitution(self):
        clean = build_text('Elias & the "red" corridor', substitutions={"Elias": "ee-LY-us"})
        self.assertEqual(clean, 'ee-LY-us & the "red" corridor')

    def test_manifest_voice_override_is_rejected(self):
        manifest = dict(self.manifest)
        manifest["narration"] = dict(self.manifest["narration"])
        manifest["narration"]["voice_name"] = "en_US-lessac-medium"
        with self.assertRaises(PiperTTSError):
            profile_from_manifest(manifest)

    def test_dry_run_is_idempotent_and_writes_no_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = profile_from_manifest(self.manifest)
            first = synthesize_chunks(self.manifest["narration"]["beats"], Path(directory), profile, dry_run=True)
            second = synthesize_chunks(self.manifest["narration"]["beats"], Path(directory), profile, dry_run=True)
            self.assertEqual(first["status"], "PIPER_TTS_DRY_RUN")
            self.assertEqual(first["chunks"], second["chunks"])
            self.assertFalse(list(Path(directory).glob("*.wav")))


if __name__ == "__main__":
    unittest.main()
