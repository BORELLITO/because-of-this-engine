from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "align_captions.py"
SPEC = importlib.util.spec_from_file_location("align_captions_grammar", MODULE_PATH)
align_captions = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(align_captions)


def test_canonical_vocabulary_contains_script_words_and_number_alternatives() -> None:
    vocabulary = align_captions._canonical_vocabulary(
        "At exactly 3:17, the lights went out."
    )

    assert "lights" in vocabulary
    assert "three" in vocabulary
    assert "seventeen" in vocabulary
    assert "3" in vocabulary
    assert "17" in vocabulary
