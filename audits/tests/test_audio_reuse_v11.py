"""Fail-closed audio-memory tests. Synthetic bytes and manifests; no TTS or music generation."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.audio_reuse_brain import AudioReuseError, audit, identity_keys
from production.quality_gates import _audio_history


class AudioReuseV11Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "episodes").mkdir()
        (self.root / "audits").mkdir()
        self.dest = self.root / "episodes" / "new"
        self.dest.mkdir()
        self.audio = self.dest / "music.wav"
        self.audio.write_bytes(b"fixture audio bytes, not a real WAV")
        self.digest = hashlib.sha256(self.audio.read_bytes()).hexdigest()
        self.registry = self.root / "episodes" / "audio-memory-registry.json"
        self.write_registry([])
        self.target = self.write_manifest(
            "new", "new-release", "new-id", self.digest, file_id="Drive-AxY7")

    def write_registry(self, entries, effects=None):
        self.registry.write_text(json.dumps({
            "schema_version": "2.0", "tracks": entries, "effects": effects or [],
        }), encoding="utf-8")

    def write_manifest(self, folder, video_id, track_id, sha, *, file_id=None,
                       filename="manifest.json", effects=None,
                       source="engine_generated", approved=True):
        p = self.root / "episodes" / folder
        p.mkdir(exist_ok=True)
        music = {
            "track_id": track_id, "path": "music.wav",
            "sha256": sha, "drive_file_id": file_id or "",
            "license": "Original procedural generated",
            "commercial_use": True,
            "license_status": "APPROVED" if approved else "PREVIEW_ONLY",
            "preview_only": not approved,
            "source": source,
            "generation": {"script": "production/generate_suspense_bed.py",
                           "duration_seconds": 70, "sample_rate_hz": 48000},
            "similarity_review": {"status": "PASS"},
        }
        d = {"video_id": video_id, "music": music, "effects": effects or []}
        path = p / filename
        path.write_text(json.dumps(d), encoding="utf-8")
        return path

    def test_full_track_collision_different_track_id_same_drive(self):
        old = self.write_manifest("old", "historic", "old-label",
                                  "b" * 64, file_id="Drive-AxY7")
        report = audit(self.target, self.root)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertGreater(report["identity_collision_count"], 0)
        self.assertIn("drive_file_id:Drive-AxY7", report["checked_target_keys"])

    def test_full_track_collision_different_drive_same_sha(self):
        self.write_manifest("old", "historic", "old-label",
                            self.digest, file_id="different-ID")
        self.assertEqual(audit(self.target, self.root)["status"], "BLOCKED")

    def test_draft_snapshot_only_still_counts(self):
        self.write_manifest("old", "historic", "other-label",
                            self.digest, filename="preview-manifest.json")
        self.assertEqual(audit(self.target, self.root)["status"], "BLOCKED")

    def test_same_episode_final_and_preview_alias_are_not_foreign(self):
        self.write_manifest("new", "draft-alias", "new-id",
                            self.digest, filename="preview-manifest.json",
                            file_id="Drive-AxY7")
        self.assertEqual(audit(self.target, self.root)["status"], "PASS")

    def test_empty_registry_is_disclosed_not_silently_claimed_complete(self):
        report = audit(self.target, self.root)
        self.assertEqual(report["ledger_track_count"], 0)
        self.assertTrue(any("zero registered" in x for x in report["notes"]))

    def test_absent_registry_raises_and_fails_closed(self):
        self.registry.unlink()
        with self.assertRaises(AudioReuseError):
            audit(self.target, self.root)

    def test_malformed_ledger_raises(self):
        self.registry.write_text('{"schema_version":"2.0","tracks":{}}')
        with self.assertRaises(AudioReuseError):
            audit(self.target, self.root)

    def test_empty_track_identity_blocks(self):
        val = json.loads(self.target.read_text())
        for field in ("track_id", "sha256", "drive_file_id"):
            val["music"].pop(field, None)
        self.target.write_text(json.dumps(val))
        self.assertEqual(audit(self.target, self.root)["status"], "BLOCKED")

    def test_strict_final_requires_registered_track_even_if_bytes_are_real(self):
        report = audit(self.target, self.root, strict=True)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("durable" in x for x in report["errors"]))

    def test_strict_final_succeeds_with_actual_sha_and_registered_track(self):
        self.write_registry([{"episode_id": "new-release", "track_id": "new-id",
                              "sha256": self.digest, "drive_file_id": "Drive-AxY7"}])
        report = audit(self.target, self.root, strict=True)
        self.assertEqual(report["status"], "PASS", report["errors"])

    def test_fake_actual_bytes_checksum_blocks(self):
        self.write_registry([{"episode_id": "new-release", "track_id": "new-id",
                              "sha256": "a" * 64}])
        data = json.loads(self.target.read_text())
        data["music"]["sha256"] = "a" * 64
        self.target.write_text(json.dumps(data))
        result = audit(self.target, self.root, strict=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("actual bytes" in x for x in result["errors"]))

    def test_verified_historical_bytes_hash_blocks_rebranded_track(self):
        data = {"schema_version": "1.1", "entries": [
            {"sha256": self.digest, "drive_file_ids": ["historical-drive-file"]}
        ]}
        (self.root / "audits" / "audio_verified_history_v11.json").write_text(json.dumps(data))
        report = audit(self.target, self.root)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(len(report["actual_sha256_reuse_hits"]), 1)

    def test_sfx_cooldown_declared_only_cannot_override_history(self):
        effects = [{"effect_id": "door-slam", "sha256": "d" * 64,
                    "reuse_status": "APPROVED_REUSE", "cooldown_videos": 999,
                    "license": "free"}]
        self.write_manifest("old", "old-story", "older-track",
                            "c" * 64, effects=effects)
        new = json.loads(self.target.read_text())
        new["effects"] = effects
        self.target.write_text(json.dumps(new))
        res = audit(self.target, self.root)
        self.assertEqual(res["status"], "BLOCKED")
        self.assertGreater(res["sfx_reuse_review_required_count"], 0)

    def test_drive_id_preserves_case(self):
        a = identity_keys({"drive_file_id": "AbC_12-xy"})
        b = identity_keys({"drive_file_id": "abc_12-xy"})
        self.assertNotEqual(a, b)

    def test_g5_bridge_blocks_on_live_audio_registry_errors(self):
        with patch("production.quality_gates.audit_audio_reuse", return_value={
            "status": "BLOCKED", "errors": ["duplicate actual SHA"],
        }) as live:
            status, evidence = _audio_history(self.target, "final")
            self.assertEqual(status, "BLOCKED")
            self.assertIn("duplicate actual SHA", evidence)
            self.assertTrue(live.called)

    def test_g5_bridge_requires_strict_final(self):
        with patch("production.quality_gates.audit_audio_reuse", return_value={
            "status": "PASS", "scanned_manifest_count": 2, "ledger_track_count": 1,
        }) as live:
            status, evidence = _audio_history(self.target, "final")
            self.assertEqual(status, "PASS")
            self.assertIn("2", evidence)
            self.assertTrue(live.call_args.kwargs["strict"])

    def test_actual_historical_evidence_file_contains_verified_identical_wavs(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / "audits/audio_verified_history_v11.json").read_text())
        self.assertEqual(data["schema_version"], "1.1")
        self.assertEqual(len(data["entries"]), 1)
        self.assertEqual(data["entries"][0]["sha256"],
                         "4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24")
        self.assertEqual(len(data["entries"][0]["drive_file_ids"]), 2)
        self.assertFalse(data["approval_for_new_episodes"])


if __name__ == "__main__":
    unittest.main()
