import json
import tempfile
import unittest
import wave
from pathlib import Path

from production.narration_cache import (
    NORMALIZATION_VERSION,
    NarrationCacheError,
    annotate_local,
    cache_key,
    local_hit,
    manifest_cache_spec,
)


def write_wav(path: Path, seconds: int = 60) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\0\0" * 24000 * seconds)


def write_episode(root: Path) -> Path:
    episode = root / "episodes" / "cache-test"
    (episode / "audio").mkdir(parents=True)
    (episode / "audio" / "narration.wav").write_bytes(b"")
    (episode / "script.txt").write_text("A short canonical script.", encoding="utf-8")
    manifest = {
        "video_id": "cache-test",
        "script": {"path": "script.txt"},
        "voice": {
            "model": "gemini-3.8-flash-tts",
            "voice": "Charon",
            "language": "en-US",
            "style": "restrained suspense",
        },
        "audio": {"path": "audio/narration.wav"},
    }
    path = episode / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    write_wav(episode / "audio" / "narration.wav")
    return path


class NarrationCacheTests(unittest.TestCase):
    def test_key_changes_when_any_generation_input_changes(self) -> None:
        base = cache_key(
            "same script",
            model="m",
            voice="v",
            language="en-US",
            style="s",
        )
        self.assertNotEqual(base, cache_key("different script", model="m", voice="v", language="en-US", style="s"))
        self.assertNotEqual(base, cache_key("same script", model="m2", voice="v", language="en-US", style="s"))
        self.assertNotEqual(base, cache_key("same script", model="m", voice="v2", language="en-US", style="s"))
        self.assertNotEqual(base, cache_key("same script", model="m", voice="v", language="pt-BR", style="s"))
        self.assertNotEqual(base, cache_key("same script", model="m", voice="v", language="en-US", style="s2"))
        self.assertNotEqual(base, cache_key("same script", model="m", voice="v", language="en-US", style="s", normalization_version="v2"))

    def test_annotated_wav_is_a_verified_local_hit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = write_episode(Path(directory))
            spec = manifest_cache_spec(manifest_path)
            result = annotate_local(spec)
            self.assertEqual(result["status"], "NARRATION_CACHE_HIT")
            self.assertEqual(result["duration_seconds"], 60.0)
            hit = local_hit(spec)
            self.assertIsNotNone(hit)
            sidecar = json.loads(spec["sidecar_path"].read_text(encoding="utf-8"))
            self.assertEqual(sidecar["normalization_version"], NORMALIZATION_VERSION)
            self.assertEqual(sidecar["cache_key"], spec["cache_key"])

    def test_tampered_sidecar_is_a_cache_miss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = write_episode(Path(directory))
            spec = manifest_cache_spec(manifest_path)
            annotate_local(spec)
            sidecar = json.loads(spec["sidecar_path"].read_text(encoding="utf-8"))
            sidecar["voice"] = "DifferentVoice"
            spec["sidecar_path"].write_text(json.dumps(sidecar), encoding="utf-8")
            self.assertIsNone(local_hit(spec))

    def test_piper_cache_requires_actual_model_and_all_voice_parameters(self) -> None:
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_episode(root)
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["voice"] = {
                "provider": "piper_tts_local", "voice_name": "en_US-ryan-high",
                "voice": "en_US-ryan-high", "model_or_voice_type": "piper_neural_high",
                "language_code": "en-US", "language": "en-US",
                "style": "suspense", "speaking_rate": 0.68, "pitch": 0,
                "sample_rate_hz": 24000, "volume_gain_db": 0,
            }
            manifest["narration"] = {"beats":[{"beat_id":"b1","text":"A short canonical script."}]}
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.dict(os.environ, {"PIPER_MODEL_DIR": str(root / "missing")}):
                with self.assertRaises(NarrationCacheError):
                    manifest_cache_spec(path)
            model_dir = root / "models"
            model_dir.mkdir()
            (model_dir / "en_US-ryan-high.onnx").write_bytes(b"model-v1")
            (model_dir / "en_US-ryan-high.onnx.json").write_text('{"sample_rate":24000}')
            with patch.dict(os.environ, {"PIPER_MODEL_DIR": str(model_dir)}):
                first = manifest_cache_spec(path)
                annotate_local(first)
                self.assertIsNotNone(local_hit(first))
                manifest["voice"]["speaking_rate"] = 0.7
                path.write_text(json.dumps(manifest), encoding="utf-8")
                changed_rate = manifest_cache_spec(path)
                self.assertNotEqual(first["cache_key"], changed_rate["cache_key"])
                manifest["voice"]["speaking_rate"] = 0.68
                manifest["narration"]["beats"][0]["text"] = "A changed TTS beat."
                path.write_text(json.dumps(manifest), encoding="utf-8")
                changed_beat = manifest_cache_spec(path)
                self.assertNotEqual(first["cache_key"], changed_beat["cache_key"])
                (model_dir / "en_US-ryan-high.onnx").write_bytes(b"model-v2")
                changed_model = manifest_cache_spec(path)
                self.assertNotEqual(changed_beat["cache_key"], changed_model["cache_key"])

if __name__ == "__main__":
    unittest.main()
