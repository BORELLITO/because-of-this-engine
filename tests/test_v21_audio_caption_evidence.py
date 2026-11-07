"""Synthetic regression of read-only artifact integrity, not perceptual voice QA."""
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from production.audio_caption_evidence_v21 import audit


class CaptionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / "audio.wav"
        self.script = self.root / "script.txt"
        self.ass = self.root / "captions.ass"
        self.sidecar = self.root / "sidecar.json"
        self.profile = self.root / "profile.json"
        with wave.open(str(self.audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(24000)
            stream.writeframes(b"\0\0" * (24000 * 60))
        self.script.write_text("One final decision.", encoding="utf-8")
        self.ass.write_text(
            "[Events]\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,One final decision.\n",
            encoding="utf-8"
        )
        self.words = [
            {"canonical": "One", "start": 0.1, "end": 0.3},
            {"canonical": "final", "start": 0.3, "end": 0.6},
            {"canonical": "decision", "start": 0.6, "end": 0.9},
        ]
        self.data = {
            "status": "WHISPER_FORCED_ALIGNMENT_PASS",
            "audio_duration_seconds": 60.0,
            "words": self.words,
            "captions": [{"text": "One final decision.", "words": self.words}],
        }
        self.voice = {
            "provider": "gemini_tts", "voice_name": "Charon",
            "audio_sha256": hashlib.sha256(self.audio.read_bytes()).hexdigest(),
            "script_sha256": hashlib.sha256(self.script.read_bytes()).hexdigest(),
        }
        self._write()

    def _write(self):
        self.sidecar.write_text(json.dumps(self.data), encoding="utf-8")
        self.profile.write_text(json.dumps(self.voice), encoding="utf-8")

    def _result(self):
        return audit(self.audio, self.script, self.ass, self.sidecar, self.profile)

    def test_structure_pass_does_not_claim_perceptual_approval(self):
        result = self._result()
        self.assertEqual(result["status"], "AUDIO_CAPTION_STRUCTURAL_PASS", result)
        self.assertEqual(result["perceptual_audio_caption_qa"], "REQUIRES_HUMAN_REVIEW")
        self.assertFalse(result["publication_authorized"])

    def test_trailing_newline_uses_exact_tts_script_hash(self):
        self.script.write_text("One final decision.\n", encoding="utf-8")
        # The narration workflow sends .strip() to the provider. A newline
        # in the source text is not a different acoustic prompt.
        result = self._result()
        self.assertEqual(result["status"], "AUDIO_CAPTION_STRUCTURAL_PASS", result)

    def test_real_episode006_source_matches_frozen_checkpoint_script_identity(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "episodes/episode-006/narration/en-US-charon-v1.txt").read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(source.strip().encode("utf-8")).hexdigest(),
            "412c4bfa1c26abd7631ec1cad74cae2e07b6d33012631bbbac53df8c8e0b3112",
        )
        self.assertNotEqual(
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "412c4bfa1c26abd7631ec1cad74cae2e07b6d33012631bbbac53df8c8e0b3112",
        )

    def test_script_mismatch_blocks(self):
        self.script.write_text("A totally different transcript.", encoding="utf-8")
        self.assertEqual(self._result()["status"], "BLOCKED")

    def test_overlapping_words_block(self):
        self.data["words"][1] = dict(self.words[1], start=0.2)
        self._write()
        self.assertIn("overlaps", " ".join(self._result()["errors"]))

    def test_audio_sha_mismatch_blocks(self):
        self.voice["audio_sha256"] = "f" * 64
        self._write()
        self.assertIn("SHA-256", " ".join(self._result()["errors"]))


if __name__ == "__main__":
    unittest.main()
