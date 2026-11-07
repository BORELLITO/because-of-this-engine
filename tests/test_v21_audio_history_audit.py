"""Coverage checks: historical manifest metadata is not proof of publication."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from production.audio_history_audit_v21 import audit

ROOT = Path(__file__).resolve().parents[1]


class V21AudioHistoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.episodes = self.root / "episodes"
        self.episodes.mkdir()
        for index in (1, 2):
            episode_id = f"episode-{index:03d}"
            folder = self.episodes / episode_id
            folder.mkdir()
            (folder / "manifest.json").write_text(json.dumps({
                "video_id": episode_id,
                "music": {"drive_file_id": "audio-test-id", "provider": "fixture"},
            }), encoding="utf-8")
        self.registry = self.episodes / "audio-memory-registry.json"
        self._write_registry("VERIFIED_COMPLETE", [1, 2])

    def _write_registry(self, status, ids):
        self.registry.write_text(json.dumps({
            "coverage_status": status,
            "tracks": [{
                "episode_id": f"episode-{i:03d}",
                "drive_file_id": "audio-test-id",
                "evidence_level": "FIXTURE_ONLY",
            } for i in ids],
        }), encoding="utf-8")

    def test_complete_synthetic_registry_passes_coverage_not_publication(self):
        report = audit(self.root)
        self.assertEqual(report["status"], "PASS", report)
        self.assertFalse(report["historical_use_verified"])
        self.assertEqual(len(report["historical_identity_collisions"]), 1)
        self.assertEqual(report["publication"], "NOT_RUN")

    def test_missing_registry_entry_blocks(self):
        self._write_registry("VERIFIED_COMPLETE", [1])
        report = audit(self.root)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("episode-002: no matching" in x for x in report["failures"]))

    def test_unverified_coverage_blocks(self):
        self._write_registry("PENDING", [1, 2])
        self.assertEqual(audit(self.root)["status"], "BLOCKED")

    def test_real_historical_registry_remains_incomplete(self):
        report = audit(ROOT)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertGreaterEqual(report["manifest_music_count"], 5)
        self.assertEqual(report["registry_track_count"], 0)
        self.assertTrue(any(
            "because-of-this-episode-001" in collision["declared_by"]
            and "because-of-this-episode-002" in collision["declared_by"]
            for collision in report["historical_identity_collisions"]
        ))


if __name__ == "__main__":
    unittest.main()
