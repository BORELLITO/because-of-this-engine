import json
import tempfile
import unittest
from pathlib import Path

from production.cloud_tts import build_ssml, profile_from_manifest, synthesize_chunks


ROOT = Path(__file__).resolve().parents[1]


class V7CloudTTSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "episodes/video-001/manifest.json").read_text(encoding="utf-8"))

    def test_profile_is_google_cloud_tts_only(self):
        profile = profile_from_manifest(self.manifest)
        self.assertEqual(profile["provider"], "google_cloud_tts")
        self.assertEqual(profile["voice_name"], "en-US-Standard-B")
        self.assertEqual(profile["language_code"], "en-US")

    def test_ssml_escapes_text_and_supports_local_substitution(self):
        ssml = build_ssml('Elias & the "red" corridor', break_before_ms=120, substitutions={"Elias": "ee-LY-us"})
        self.assertTrue(ssml.startswith("<speak><break time=\"120ms\"/>") )
        self.assertIn('<sub alias="ee-LY-us">Elias</sub>', ssml)
        self.assertIn("&amp;", ssml)

    def test_dry_run_is_idempotent_and_writes_no_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            first = synthesize_chunks(self.manifest["narration"]["beats"], Path(directory), profile_from_manifest(self.manifest), dry_run=True)
            second = synthesize_chunks(self.manifest["narration"]["beats"], Path(directory), profile_from_manifest(self.manifest), dry_run=True)
            self.assertEqual(first["status"], "CLOUD_TTS_DRY_RUN")
            self.assertEqual(first["chunks"], second["chunks"])
            self.assertFalse(list(Path(directory).glob("*.wav")))


if __name__ == "__main__":
    unittest.main()
