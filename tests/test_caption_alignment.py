from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "align_captions.py"
SPEC = importlib.util.spec_from_file_location("align_captions", MODULE_PATH)
align_captions = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(align_captions)


def test_alignment_searches_across_segment_gap_without_guessing_times() -> None:
    asr_words = [
        {"word": f"noise{index}", "start": float(index), "end": float(index) + 0.1}
        for index in range(20)
    ]
    asr_words.extend(
        [
            {"word": "then", "start": 20.0, "end": 20.2},
            {"word": "the", "start": 20.2, "end": 20.4},
            {"word": "lights", "start": 20.4, "end": 20.7},
            {"word": "went", "start": 20.7, "end": 20.9},
            {"word": "out", "start": 20.9, "end": 21.1},
        ]
    )

    start, end, cursor, positions = align_captions._align_chunk(
        "Then the lights went out.", asr_words, 0
    )

    assert start == 20.0
    assert end == 21.1
    assert cursor == 25
    assert len(positions) == 5
