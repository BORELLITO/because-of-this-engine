import json
import tempfile
import unittest
import wave
from pathlib import Path

from production.narration_cache import (
    NORMALIZATION_VERSION,
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


if __name__ == "__main__":
    unittest.main()
