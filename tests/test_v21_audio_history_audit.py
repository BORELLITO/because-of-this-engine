"""V2.1 audio source evidence vs actual mastered soundtrack proof.

Synthetic positive tests never promote or modify real historical audio.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from production.audio_history_audit_v21 import audit, MASTER_PROOF

ROOT = Path(__file__).resolve().parents[1]
ONE = "a" * 64
TWO = "b" * 64


class V21AudioHistoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.episodes = self.root / "episodes"
        self.episodes.mkdir()
        for idx in (1, 2):
            ep = f"episode-{idx:03d}"
            folder = self.episodes / ep
            folder.mkdir()
            (folder / "manifest.json").write_text(json.dumps({
                "video_id": ep,
                "music": {"drive_file_id": f"distinct-track-{idx}"},
            }), encoding="utf-8")
        self.registry = self.episodes / "audio-memory-registry.json"
        self.source = [
            {
                "episode_id": f"episode-{idx:03d}",
                "kind": "music_bed",
                "historical_manifest": f"episodes/episode-{idx:03d}/manifest.json",
                "drive_file_id": f"distinct-track-{idx}",
                "source_file_sha256": ONE if idx == 1 else TWO,
                "actual_master_audio_verified": True,
                "master_release_evidence": {
                    "verification_method": MASTER_PROOF,
                    "episode_id": f"episode-{idx:03d}",
                    "source_identity_verified_in_mix": True,
                    "master_video_sha256": ONE,
                    "mixed_audio_sha256": TWO,
                    "artifact_id": "fixture-mix-artifact",
                    "mix_execution_log_sha256": ONE,
                },
            }
            for idx in (1, 2)
        ]
        self._write("VERIFIED_COMPLETE", "VERIFIED_COMPLETE", self.source)

    def _write(self, coverage, sfx, tracks):
        self.registry.write_text(json.dumps({
            "coverage_status": coverage,
            "sfx_coverage_status": sfx,
            "tracks": tracks,
        }), encoding="utf-8")

    def test_independent_receipts_allow_synthetic_complete_coverage_only(self):
        report = audit(self.root)
        self.assertEqual(report["status"], "PASS", report)
        self.assertTrue(report["historical_use_verified"])
        self.assertEqual(report["verified_master_audio_count"], 2)
        self.assertEqual(report["publication"], "NOT_RUN")

    def test_missing_registry_episode_blocks(self):
        self._write("VERIFIED_COMPLETE", "VERIFIED_COMPLETE", self.source[:1])
        result = audit(self.root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("episode-002" in x for x in result["failures"]))

    def test_complete_flag_alone_cannot_launder_source_file(self):
        tracks = copy.deepcopy(self.source)
        tracks[0]["actual_master_audio_verified"] = False
        self._write("VERIFIED_COMPLETE", "VERIFIED_COMPLETE", tracks)
        self.assertEqual(audit(self.root)["status"], "BLOCKED")

    def test_master_receipt_without_mix_provenance_blocks(self):
        tracks = copy.deepcopy(self.source)
        tracks[1]["master_release_evidence"]["source_identity_verified_in_mix"] = False
        self._write("VERIFIED_COMPLETE", "VERIFIED_COMPLETE", tracks)
        self.assertTrue(any("master audio-mix receipt" in s for s in audit(self.root)["failures"]))

    def test_sfx_must_be_separately_complete(self):
        self._write("VERIFIED_COMPLETE", "PENDING", self.source)
        self.assertTrue(any("SFX usage" in s for s in audit(self.root)["failures"]))

    def test_source_reuse_collision_blocks_even_with_fake_complete_flags(self):
        p = self.episodes / "episode-002" / "manifest.json"
        m = json.loads(p.read_text())
        m["music"]["drive_file_id"] = "distinct-track-1"
        p.write_text(json.dumps(m))
        tracks = copy.deepcopy(self.source)
        tracks[1]["drive_file_id"] = "distinct-track-1"
        self._write("VERIFIED_COMPLETE", "VERIFIED_COMPLETE", tracks)
        report = audit(self.root)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("collision unresolved" in s for s in report["failures"]))

    def test_real_source_sha_verified_but_masters_unproven(self):
        report = audit(ROOT)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["manifest_music_count"], 5)
        self.assertEqual(report["registry_track_count"], 5)
        self.assertEqual(report["verified_original_source_count"], 3)
        self.assertEqual(report["verified_master_audio_count"], 0)
        self.assertTrue(any("master audio usage is not verified" in f for f in report["failures"]))
        self.assertTrue(any("historical music source identity collision" in f for f in report["failures"]))
        self.assertTrue(any("historical SFX usage" in f for f in report["failures"]))
        self.assertTrue(any("because-of-this-episode-001" in c["declared_by"]
                            and "because-of-this-episode-002" in c["declared_by"]
                            for c in report["historical_identity_collisions"]))


if __name__ == "__main__":
    unittest.main()
