"""Offline contract: Cloud Charon candidate must remain non-billable by default."""
import unittest
from experimental.v11.chirp3_cloud_tts_contract import (
    build_request, offline_receipt, Chirp3ContractError, VOICE_NAME
)


class Chirp3ContractTests(unittest.TestCase):
    def test_request_is_documented_synchronous_text_contract(self):
        r = build_request("She opened the envelope.")
        self.assertEqual(r["voice"]["name"], "en-US-Chirp3-HD-Charon")
        self.assertEqual(r["voice"]["languageCode"], "en-US")
        self.assertEqual(r["audioConfig"], {"audioEncoding": "LINEAR16"})
        self.assertNotIn("ssml", r["input"])
        self.assertNotIn("pitch", r["audioConfig"])
        self.assertNotIn("speakingRate", r["audioConfig"])

    def test_empty_text_and_unverified_ssml_are_blocked(self):
        for item in ("", "    ", "<speak>Sound</speak>", "test\x00bad"):
            with self.subTest(item=item), self.assertRaises(Chirp3ContractError):
                build_request(item)

    def test_explicit_nonactivation_receipt(self):
        receipt = offline_receipt("A new original sentence.")
        self.assertFalse(receipt["ready_for_real_tts"])
        self.assertTrue(receipt["requires_explicit_paid_test_approval"])
        self.assertFalse(receipt["api_was_called"])
        self.assertFalse(receipt["audio_generated"])
        self.assertEqual(receipt["voice_name"], VOICE_NAME)
        self.assertEqual(receipt["request_sha256"], offline_receipt("A new original sentence.")["request_sha256"])


if __name__ == "__main__":
    unittest.main()
