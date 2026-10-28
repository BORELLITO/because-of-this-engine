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
                         540 if mode == "preview" else 1080)
        self.assertEqual(report["expected_visual_layout"]["outro_logo_width_px"],
                         820 if mode == "preview" else 1640)

    def test_preview_passes_correct_dimensions(self):
        self.check_pass("preview")

    def test_final_passes_4k_vertical_dimensions(self):
        self.check_pass("final")

    def test_final_rejects_preview_sized_file(self):
        path, report_path = self.manifest("final")
        with patch("production.golden_frame_regression.ffprobe",
                   return_value={"width": 1080, "height": 1920,
                                 "has_audio": True, "duration": 66.0}):
            self.assertEqual(run(path, "final", report_path), 1)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIn("rendered_dimensions:", " ".join(report["errors"]))

    def test_layout_reference_scale_and_invalid_width(self):
        self.assertEqual(layout_px(540, 1080), 540)
        self.assertEqual(layout_px(540, 2160), 1080)
        self.assertEqual(layout_px(72, 2160), 144)
        self.assertEqual(layout_px(820, 2160), 1640)
        with self.assertRaises(RenderError):
            layout_px(540, 720)
