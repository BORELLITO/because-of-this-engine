"""YouTube Audio Library ingestion must never override old tracks or assert TikTok rights."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from production.ingest_youtube_audio_library import ingest


class AudioIngestV11Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ep = self.root / "episodes/new"
        self.ep.mkdir(parents=True)
        self.source = self.root / "track.mp3"
        self.source.write_bytes(b"fictional MP3 fixture - no protected audio")
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.meta = self.root / "track-metadata.json"
        self.meta.write_text(json.dumps({
            "title": "Synthetic", "artist": "Test", "attribution_required": False,
            "similarity_review": {"status": "PASS"},
            "device_tests": {"phone": "PASS", "headphones": "PASS", "low_volume": "PASS"},
            "track_id": "synthetic-001",
        }))
        self.manifest = self.ep / "manifest.json"
        self.manifest.write_text(json.dumps({"video_id": "new-release", "music": {}}))
        self.registry = self.root / "episodes/audio-memory-registry.json"
        self.write_registry([])

    def write_registry(self, tracks):
        self.registry.write_text(json.dumps({"schema_version": "2.0", "tracks": tracks}))

    def run_ingest(self, path=None):
        return ingest(self.source, self.meta, self.ep, self.manifest,
                      path or self.registry, True)

    def test_duplicate_same_file_hash_different_label_fails_before_any_writes(self):
        self.write_registry([{
            "episode_id": "already-used", "track_id": "another-label",
            "sha256": self.digest,
        }])
        old_manifest = self.manifest.read_bytes()
        old_registry = self.registry.read_bytes()
        with self.assertRaisesRegex(ValueError, "Cannot reuse"):
            self.run_ingest()
        self.assertEqual(self.manifest.read_bytes(), old_manifest)
        self.assertEqual(self.registry.read_bytes(), old_registry)
        self.assertFalse((self.ep / "assets/music/youtube-audio-library.mp3").exists())

    def test_duplicate_label_with_different_sha_fails(self):
        self.write_registry([{
            "episode_id": "already-used", "track_id": "synthetic-001",
            "sha256": "a" * 64,
        }])
        with self.assertRaises(ValueError):
            self.run_ingest()

    def test_missing_registry_never_creates_unsafe_empty_history(self):
        self.registry.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_ingest()
        self.assertFalse(self.registry.exists())

    def test_episode_local_ledger_is_rejected(self):
        local = self.ep / "music-license-register.json"
        with self.assertRaisesRegex(ValueError, "global"):
            self.run_ingest(local)

    def test_music_is_registered_as_off_platform_rights_pending(self):
        result = self.run_ingest()
        m = json.loads(self.manifest.read_text())
        r = json.loads(self.registry.read_text())
        self.assertEqual(result["status"], "AUDIO_REGISTERED_PENDING_OFFPLATFORM_RIGHTS")
        self.assertEqual(len(r["tracks"]), 1)
        self.assertTrue(m["music"]["preview_only"])
        self.assertEqual(m["music"]["license_status"], "REVIEW_REQUIRED")
        self.assertFalse(m["music"]["off_platform_rights_verified"])
        self.assertEqual(m["music"]["sha256"], self.digest)

    def test_repeated_identical_ingest_is_idempotent_in_registry(self):
        self.run_ingest()
        self.run_ingest()
        r = json.loads(self.registry.read_text())
        self.assertEqual(len(r["tracks"]), 1)

    def test_existing_different_master_is_not_overwritten(self):
        target = self.ep / "assets/music/youtube-audio-library.mp3"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"other existing master")
        old = self.manifest.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.run_ingest()
        self.assertEqual(self.manifest.read_bytes(), old)
        self.assertEqual(target.read_bytes(), b"other existing master")


if __name__ == "__main__":
    unittest.main()
