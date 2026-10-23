import json
import tempfile
import unittest
import wave
from pathlib import Path

from production.master_timeline import (
    MasterTimelineError,
    build_timeline,
    parse_rate,
    source_fingerprint,
)


class MasterTimelineTests(unittest.TestCase):
    def _episode(self):
        root = Path(tempfile.mkdtemp())
        (root / "assets").mkdir()
        audio = root / "assets" / "voice.wav"
        with wave.open(str(audio), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(b"\x00\x00" * 24000)
        captions = root / "assets" / "captions.ass"
        captions.write_text("[Events]\nFormat: Layer, Start, End, Style, Text\n", encoding="utf-8")
        image = root / "assets" / "scene.bin"
        image.write_bytes(b"scene")
        manifest = {
            "video_id": "test-001",
            "timeline_version": "1.0",
            "fps": 25,
            "timebase": "1/25",
            "audio_sample_rate": 24000,
            "audio": {"path": "assets/voice.wav"},
            "captions": {
                "path": "assets/captions.ass",
                "sync_policy": "narration_locked",
                "alignment_mode": "phrase_level_manual_reviewed",
                "word_level_available": False,
                "sync_tolerance_frames": 3,
                "end_tolerance_seconds": 0.1,
            },
            "scenes": [{"scene_id": "S01", "image": "assets/scene.bin"}],
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, manifest, root

    def test_frame_rate_and_parse_rate(self):
        self.assertEqual(parse_rate("25/1"), 25)
        self.assertAlmostEqual(float(parse_rate("30000/1001")), 30000 / 1001, places=8)
        self.assertIsNone(parse_rate(""))

    def test_master_timeline_uses_single_clock(self):
        path, manifest, _ = self._episode()
        events = [(0.0, 1.0, "hello world")]
        timeline = build_timeline(path, manifest, events)
        self.assertEqual(timeline["timebase"], "1/25")
        self.assertEqual(timeline["audio_sample_count"], 24000)
        self.assertEqual(timeline["caption_count"], 1)
        self.assertEqual(timeline["caption_end_gap_seconds"], 0.0)
        self.assertEqual(timeline["anchors"][-1]["target_frame"], 25)

    def test_source_fingerprint_changes_with_source(self):
        path, manifest, root = self._episode()
        before = source_fingerprint(path, manifest)["source_fingerprint"]
        (root / "assets" / "scene.bin").write_bytes(b"changed")
        after = source_fingerprint(path, manifest)["source_fingerprint"]
        self.assertNotEqual(before, after)

    def test_end_gap_is_hard_locked(self):
        path, manifest, _ = self._episode()
        with self.assertRaises(MasterTimelineError):
            build_timeline(path, manifest, [(0.0, 0.7, "hello")])


if __name__ == "__main__":
    unittest.main()
