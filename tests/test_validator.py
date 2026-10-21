from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "validate_episode.py"
SPEC = importlib.util.spec_from_file_location("validate_episode", MODULE_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class ValidatorTests(unittest.TestCase):
    def test_transcript_normalization_preserves_word_order_and_ass_line_breaks(self) -> None:
        self.assertEqual(
            validator.normalize_words("NASA’s path\\Ndrifted"),
            ["nasa's", "path", "drifted"],
        )

    def test_caption_events_reject_overlaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "captions.ass"
            path.write_text(
                "\n".join(
                    [
                        "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,,One",
                        "Dialogue: 0,0:00:00.50,0:00:02.00,Default,,0,0,,Two",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(validator.ValidationFailure):
                validator.caption_events(path)

    def test_require_path_rejects_escape_from_independent_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            root.mkdir()
            outside = Path(temp_dir) / "outside.txt"
            outside.write_text("x", encoding="utf-8")
            with self.assertRaises(validator.ValidationFailure):
                validator.require_path(root, "../outside.txt", root)


if __name__ == "__main__":
    unittest.main()
