import copy
import unittest

from production.mix_receipt_v21 import MASTER_PROOF, validate_mix_receipt

ONE = "a" * 64
TWO = "b" * 64


def receipt():
    return {
        "schema_version": "1.0",
        "verification_method": MASTER_PROOF,
        "episode_id": "episode-001",
        "source_identity_verified_in_mix": True,
        "master_video_sha256": ONE,
        "mixed_audio_sha256": TWO,
        "narration_sha256": ONE,
        "mix_command_sha256": TWO,
        "mix_execution_log_sha256": ONE,
        "artifact_id": "mix-receipt-fixture",
        "music_sources": [{
            "identity": "music-fixture",
            "sha256": ONE,
            "source_bytes_sha256": TWO,
            "source_bytes_verified": True,
            "audible_use_verified": True,
        }],
        "sfx_sources": [],
        "sfx_usage_status": "VERIFIED_NONE",
    }


class V21MixReceiptTests(unittest.TestCase):
    def test_valid_receipt_passes(self):
        self.assertEqual(validate_mix_receipt(receipt(), expected_episode_id="episode-001"), [])

    def test_receipt_requires_explicit_sfx_status(self):
        data = receipt()
        data.pop("sfx_usage_status")
        self.assertTrue(any("sfx_usage_status" in item for item in validate_mix_receipt(data)))

    def test_receipt_rejects_unverified_source_bytes(self):
        data = receipt()
        data["music_sources"][0]["source_bytes_verified"] = False
        self.assertTrue(any("source_bytes_verified" in item for item in validate_mix_receipt(data)))

    def test_receipt_rejects_episode_mismatch(self):
        data = copy.deepcopy(receipt())
        data["episode_id"] = "episode-999"
        self.assertTrue(any("does not match" in item for item in validate_mix_receipt(
            data, expected_episode_id="episode-001"
        )))


if __name__ == "__main__":
    unittest.main()
