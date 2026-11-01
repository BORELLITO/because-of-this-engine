import json
import tempfile
import unittest
import wave
from pathlib import Path

from production.caption_quality import CaptionQualityError, quality_report


class CaptionQualityTests(unittest.TestCase):
    def _fixture(self, text: str = "The signal disappeared.") -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "assets").mkdir()
        script = root / "script.txt"
        script.write_text(text, encoding="utf-8")
        audio = root / "assets" / "voice.wav"
        with wave.open(str(audio), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(b"\x00\x00" * 48000)
        captions = root / "assets" / "captions.ass"
        captions.write_text(
            """[Script Info]
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,50,&H00FFFFFF,&H00FFFFFF,&H00101624,&H80101624,-1,0,0,0,100,100,0,0,1,3,1,2,100,100,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.10,0:00:02.00,Default,,0,0,300,,The signal disappeared.
""",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": "1.1",
            "audio": {"path": "assets/voice.wav"},
            "script": {"path": "script.txt"},
            "captions": {
                "path": "assets/captions.ass",
                "alignment_mode": "phrase_level_manual_reviewed",
                "alignment_source": "reviewed_test_fixture",
                "word_level_available": False,
                "max_lines": 2,
                "max_line_chars": 42,
                "max_cps": 24,
                "end_tolerance_seconds": 0.1,
            },
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def test_caption_contract_passes(self):
        report = quality_report(self._fixture())
        self.assertEqual(report["status"], "CAPTION_QA_PASS")
        self.assertEqual(report["event_count"], 1)
        self.assertEqual(report["timing_claim"], "reviewed_phrase_level")

    def test_final_blocks_without_word_level_evidence(self):
        with self.assertRaisesRegex(CaptionQualityError, "word-level"):
            quality_report(self._fixture(), require_word_level=True)

    def test_transcript_mismatch_blocks(self):
        path = self._fixture("Different words.")
        with self.assertRaisesRegex(CaptionQualityError, "exactly match"):
            quality_report(path)

    def test_safe_zone_blocks_bad_alignment(self):
        path = self._fixture()
        captions = Path(path.parent / "assets" / "captions.ass")
        value = captions.read_text(encoding="utf-8").replace(",2,100,100,300,1", ",8,20,20,80,1")
        captions.write_text(value, encoding="utf-8")
        with self.assertRaisesRegex(CaptionQualityError, "lower-third"):
            quality_report(path)


if __name__ == "__main__":
    unittest.main()
