"""Locked ASS mobile geometry cannot be bypassed by event-level overrides.

Synthetic ASS only; no production frames, voice, or final caption files altered.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from production.caption_quality import CaptionQualityError, parse_events
from production.canonical_config import caption_ass_style_line


class LockedCaptionASSV11Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"captions.ass"

    def write(self, *, style="Default", marginl="0", marginr="0",
              marginv="0", effect="", text="He heard the floor creak."):
        self.path.write_text(
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
            "[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,"
            "BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,"
            "Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            + caption_ass_style_line() + "\n"
            + "[Events]\n"
            + "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
            + f"Dialogue: 0,0:00:01.00,0:00:02.00,{style},,{marginl},{marginr},{marginv},{effect},{text}\n",
            encoding="utf-8"
        )

    def test_locked_default_without_geometry_override_passes(self):
        self.write()
        self.assertEqual(len(parse_events(self.path)),1)

    def test_karaoke_color_transforms_still_allowed(self):
        self.write(text=r"{\1c&H00FFFFFF&\t(0,120,\1c&H007777FF&)\t(120,121,\1c&H00FFFFFF&)}He heard it.")
        self.assertEqual(len(parse_events(self.path)),1)

    def test_right_margin_override_rejected(self):
        self.write(marginr="1")
        with self.assertRaisesRegex(CaptionQualityError,"margin"):
            parse_events(self.path)

    def test_vertical_margin_override_rejected(self):
        self.write(marginv="40")
        with self.assertRaises(CaptionQualityError):
            parse_events(self.path)

    def test_event_style_override_rejected(self):
        self.write(style="UIBypass")
        with self.assertRaisesRegex(CaptionQualityError,"Default"):
            parse_events(self.path)

    def test_event_scroll_effect_rejected(self):
        self.write(effect="Scroll up")
        with self.assertRaises(CaptionQualityError):
            parse_events(self.path)

    def test_ass_position_override_rejected(self):
        for snippet in (r"{\pos(1000,1700)}x", r"{\move(0,100,1080,1900)}x",
                        r"{\an9}x", r"{\fs120}x", r"{\clip(0,0,100,100)}x",
                        r"{\t(0,100,\fscx400)}x"):
            with self.subTest(snippet=snippet):
                self.write(text=snippet)
                with self.assertRaisesRegex(CaptionQualityError,"override"):
                    parse_events(self.path)


if __name__ == "__main__":
    unittest.main()
