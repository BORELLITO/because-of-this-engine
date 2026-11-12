"""Tests for fail-closed historical receipt recovery."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from production.historical_receipt_recovery_v21 import build_recovery_report
from production.mix_receipt_v21 import MASTER_PROOF

ONE = "a" * 64
TWO = "b" * 64
THREE = "c" * 64
FOUR = "d" * 64
FIVE = "e" * 64
SIX = "f" * 64


def master(episode_id: str, number: int) -> dict:
    return {
        "episode_id": episode_id,
        "master_video": {
            "drive_file_id": f"master-{number}",
            "sha256": ONE if number == 1 else TWO,
            "mixed_audio_decoded_48k_mono_s16le_sha256": TWO if number == 1 else ONE,
        },
        "music_asset": {
            "drive_file_id": f"music-{number}",
            "sha256": THREE if number == 1 else FOUR,
            "verified_original_bytes": True,
        },
    }


def receipt(episode_id: str, number: int) -> dict:
    row = master(episode_id, number)["master_video"]
    return {
        "schema_version": "1.0",
        "verification_method": MASTER_PROOF,
        "source_identity_verified_in_mix": True,
        "episode_id": episode_id,
        "master_video_sha256": row["sha256"],
        "mixed_audio_sha256": row["mixed_audio_decoded_48k_mono_s16le_sha256"],
        "narration_sha256": FIVE,
        "mix_command_sha256": SIX,
        "mix_execution_log_sha256": FIVE,
        "artifact_id": f"artifact-{number}",
        "music_sources": [{
            "identity": f"music-{number}",
            "sha256": THREE if number == 1 else FOUR,
            "source_bytes_sha256": THREE if number == 1 else FOUR,
            "source_bytes_verified": True,
            "audible_use_verified": True,
        }],
        "sfx_sources": [],
        "sfx_usage_status": "VERIFIED_NONE",
    }


class HistoricalReceiptRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "rendered_masters": [master("episode-a", 1), master("episode-b", 2)]
        }

    def test_missing_receipts_remain_blocked(self):
        report = build_recovery_report(self.registry)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["ready_count"], 0)
        self.assertTrue(all("strict_mix_receipt" in row["receipt_failures"]
                            for row in report["rows"]))

    def test_only_hash_matched_strict_receipts_are_ready(self):
        evidence = {"receipts": [receipt("episode-a", 1), receipt("episode-b", 2)]}
        report = build_recovery_report(self.registry, evidence)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["ready_count"], 2)

    def test_receipt_for_wrong_episode_cannot_be_reused(self):
        evidence = {"receipts": [receipt("episode-a", 1), receipt("episode-a", 1)]}
        report = build_recovery_report(self.registry, evidence)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("strict_mix_receipt" in row["receipt_failures"]
                            for row in report["rows"]))

    def test_registry_hash_mismatch_blocks_even_valid_receipt(self):
        candidate = receipt("episode-a", 1)
        candidate["master_video_sha256"] = SIX
        report = build_recovery_report(self.registry, {"receipts": [candidate]})
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("receipt master_video_sha256 does not match registry",
                      report["rows"][0]["receipt_failures"])

    def test_malformed_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            build_recovery_report(self.registry, {"unexpected": []})

    def test_report_does_not_mutate_inputs(self):
        original = copy.deepcopy(self.registry)
        build_recovery_report(self.registry, {"receipts": [receipt("episode-a", 1)]})
        self.assertEqual(self.registry, original)


if __name__ == "__main__":
    unittest.main()
