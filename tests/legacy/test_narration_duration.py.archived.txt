from __future__ import annotations

import importlib.util
import io
import tempfile
import wave
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "production" / "normalize_narration_duration.py"
SPEC = importlib.util.spec_from_file_location("normalize_narration_duration", MODULE_PATH)
normalize_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(normalize_module)


def _write_wav(path: Path, seconds: float) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x00\x00" * int(seconds * 24000))


def test_duration_contract_blocks_short_narration_before_render() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        audio = root / "narration.wav"
        _write_wav(audio, 59.0)
        manifest = root / "manifest.json"
        manifest.write_text(
            '{"audio": {"path": "narration.wav"}}',
            encoding="utf-8",
        )

        try:
            normalize_module.normalize(manifest, "ffmpeg")
        except normalize_module.NarrationDurationError as exc:
            assert "below the 60-75s contract" in str(exc)
        else:
            raise AssertionError("short narration must be blocked")
