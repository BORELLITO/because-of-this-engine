import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "ingest_youtube_audio_library.py"
SPEC = importlib.util.spec_from_file_location("audio_library_ingest", MODULE_PATH)
ingest_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ingest_module)


class YouTubeAudioLibraryIngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.episode = self.root / "episode"
        self.episode.mkdir()
        self.source = self.root / "track.mp3"
        self.source.write_bytes(b"mock mp3")
        self.metadata = self.root / "metadata.json"
        self.metadata.write_text(json.dumps({
            "title": "Low Orbit", "artist": "Test Artist",
            "attribution_required": True, "attribution_text": "Credit Test Artist",
        }))
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"episode_id": "episode-1", "require_music": True}))
        self.register = self.root / "register.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_copies_track_and_records_license_and_attribution(self):
        result = ingest_module.ingest(self.source, self.metadata, self.episode,
                                      self.manifest, self.register, True)
        manifest = json.loads(self.manifest.read_text())
        register = json.loads(self.register.read_text())
        self.assertEqual(result["path"], "assets/music/youtube-audio-library.mp3")
        self.assertTrue((self.episode / result["path"]).is_file())
        self.assertEqual(manifest["music"]["attribution"], "Credit Test Artist")
        self.assertEqual(register["tracks"][0]["license"], "youtube_audio_library")

    def test_requires_source_confirmation_and_attribution(self):
        with self.assertRaises(ValueError):
            ingest_module.ingest(self.source, self.metadata, self.episode,
                                 self.manifest, self.register, False)
        self.metadata.write_text(json.dumps({
            "title": "Low Orbit", "artist": "Test Artist", "attribution_required": True,
        }))
        with self.assertRaises(ValueError):
            ingest_module.ingest(self.source, self.metadata, self.episode,
                                 self.manifest, self.register, True)


if __name__ == "__main__":
    unittest.main()
