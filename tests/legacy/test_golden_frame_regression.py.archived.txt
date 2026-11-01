"""Mode-aware golden layout checks and preview/final sizing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.golden_frame_regression import EXPECTED, run
from production.render_video_episode import RenderError, SIZES, layout_px


class GoldenFrameModeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def manifest(self, mode):
        data = {
            "engine_profile": EXPECTED["engine_profile"],
            "video_id": "test-episode",
            "output": {"path": "rendered/test-{mode}.mp4"},
            "brand": EXPECTED["brand"],
            "captions": {
                **{k: v for k, v in EXPECTED["captions"].items()
                   if k not in {"alignment", "margin_v"}},
                "style": {"alignment": 2, "margin_v": 320},
            },
            "loop": EXPECTED["loop"],
        }
        path = self.root / "manifest.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        output = self.root / "rendered" / f"test-{mode}.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"mocked media: ffprobe is stubbed")
        return path, self.root / f"report-{mode}.json"

    def check_pass(self, mode):
        path, report_path = self.manifest(mode)
        width, height = SIZES[mode]
        with patch("production.golden_frame_regression.ffprobe",
                   return_value={"width": width, "height": height,
                                 "has_audio": True, "duration": 66.0}):
            self.assertEqual(run(path, mode, report_path), 0)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["expected_dimensions"], [width, height])
        self.assertEqual(report["expected_visual_layout"]["logo_width_px"],
                         540)
        self.assertEqual(report["expected_visual_layout"]["outro_logo_width_px"],
                         820)

    def test_preview_passes_correct_dimensions(self):
        self.check_pass("preview")

    def test_final_passes_canonical_vertical_dimensions(self):
        self.check_pass("final")

    def test_final_accepts_canonical_sized_file(self):
        path, report_path = self.manifest("final")
        with patch("production.golden_frame_regression.ffprobe",
                   return_value={"width": 1080, "height": 1920,
                                 "has_audio": True, "duration": 66.0}):
            self.assertEqual(run(path, "final", report_path), 0)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["errors"], [])

    def test_layout_reference_scale_and_invalid_width(self):
        self.assertEqual(layout_px(540, 1080), 540)
        self.assertEqual(layout_px(540, 1080), 540)
        self.assertEqual(layout_px(72, 1080), 72)
        self.assertEqual(layout_px(820, 1080), 820)
        with self.assertRaises(RenderError):
            layout_px(540, 720)

    def test_final_mux_ffmpeg_graph_preserves_relative_layout(self):
        from production.render_video_episode import mux_audio

        music = self.root / "music.wav"
        music.write_bytes(b"mocked music")
        brand = {"logo_enabled": True, "logo_width": 540,
                 "logo_top": 72, "logo_opacity": 0.82,
                 "logo_anchor": "center_top"}
        loop = {"enabled": True, "outro_seconds": 1.2,
                "logo_width": 820, "logo_anchor": "center_center"}
        with patch("production.render_video_episode.ffprobe",
                   return_value={"video_duration": 60.0}), \
             patch("production.render_video_episode.run") as fake_ffmpeg:
            mux_audio(
                video=self.root / "video.mp4",
                audio=self.root / "voice.wav",
                captions=self.root / "captions.ass",
                output=self.root / "final.mp4",
                narration_duration=60.0,
                music=music,
                music_volume=0.12,
                logo_path=self.root / "brand.png",
                brand=brand,
                width=1080,
                height=1920,
                loop=loop,
                loop_logo_path=self.root / "outro.png",
            )
        command = fake_ffmpeg.call_args.args[0]
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn("scale=540:-1", graph)
        self.assertIn("y=72:", graph)
        self.assertIn("scale=820:-1:flags=lanczos", graph)
        self.assertIn("s=1080x1920", graph)
