import json
import tempfile
import unittest
from pathlib import Path

from production.v21_visual_contract import (
    ACTIVE_WORD_COLOR,
    CAPTION_MARGIN_V,
    CAPTION_MAX_LINES,
    IN_VIDEO_LOGO_OPACITY,
    IN_VIDEO_LOGO_WIDTH,
    IN_VIDEO_LOGO_Y,
    LOGO_ASSET,
    LOGO_SHA256,
    OUTRO_LOGO_WIDTH,
    OUTRO_SECONDS,
    reject_legacy_layout,
)


class V21VisualContractTests(unittest.TestCase):
    def test_contract_uses_approved_layout(self):
        self.assertEqual(LOGO_ASSET, "brand/because-of-this-wordmark-transparent.png")
        self.assertEqual(LOGO_SHA256, "5c062475dd174b5b314f53ea9e9f7be64ad534ae529c791ea8668265cc5dc33b")
        self.assertEqual(IN_VIDEO_LOGO_WIDTH, 360)
        self.assertEqual(IN_VIDEO_LOGO_Y, 190)
        self.assertEqual(IN_VIDEO_LOGO_OPACITY, 0.90)
        self.assertEqual(CAPTION_MARGIN_V, 650)
        self.assertEqual(CAPTION_MAX_LINES, 2)
        self.assertEqual(ACTIVE_WORD_COLOR, "#F04444")
        self.assertEqual(OUTRO_LOGO_WIDTH, 620)
        self.assertEqual(OUTRO_SECONDS, 5.5)

    def test_caption_policy_matches_visual_contract(self):
        policy = json.loads(Path("production/caption_policy_v21.json").read_text(encoding="utf-8"))
        layout = policy["layout"]
        self.assertEqual(layout["alignment"], 2)
        self.assertEqual(layout["margin_l"], 100)
        self.assertEqual(layout["margin_r"], 100)
        self.assertEqual(layout["margin_v"], CAPTION_MARGIN_V)
        self.assertEqual(layout["max_lines"], CAPTION_MAX_LINES)
        self.assertEqual(policy["alignment"]["active_word_color"], ACTIVE_WORD_COLOR)

    def test_legacy_layout_is_blocked(self):
        with self.assertRaises(ValueError):
            reject_legacy_layout({"logo_y": 72})
        with self.assertRaises(ValueError):
            reject_legacy_layout({"caption_margin_v": 320})
        with self.assertRaises(ValueError):
            reject_legacy_layout({"logo_width": 540})

    def test_preview_renderer_uses_the_contract(self):
        source = Path("production/render_v21_preview.py").read_text(encoding="utf-8")
        self.assertIn("production.v21_visual_contract", source)
        self.assertIn("validate_caption_ass", source)
        self.assertIn("validate_logo_path", source)
        self.assertNotIn("IN_VIDEO_LOGO_Y = 72", source)
        self.assertNotIn('"caption_margin_v": 320', source)


if __name__ == "__main__":
    unittest.main()
