from __future__ import annotations

import base64
import importlib.util
import io
import json
import sys
import tempfile
import time
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "narrate.py"
SPEC = importlib.util.spec_from_file_location("narrate", MODULE_PATH)
narrate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(narrate)


def make_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 2400)
    return buffer.getvalue()


class NarrationTests(unittest.TestCase):
    def test_generates_wav_and_provenance_sidecar_with_mocked_api(self) -> None:
        expected_audio = make_wav()
        calls: list[dict] = []

        class FakeInteractions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return types.SimpleNamespace(
                    id="mock-request-id",
                    output_audio=types.SimpleNamespace(
                        data=base64.b64encode(expected_audio).decode("ascii")
                    ),
                )

        class FakeClient:
            def __init__(self, *, api_key: str):
                self.interactions = FakeInteractions()

        fake_google = types.ModuleType("google")
        fake_google.genai = types.SimpleNamespace(Client=FakeClient)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voice.wav"
            with patch.dict(sys.modules, {"google": fake_google}):
                metadata = narrate.generate_narration(
                    "A short test script.",
                    output_path,
                    api_key="test-key-never-sent",
                    transport="sdk",
                )

            self.assertEqual(output_path.read_bytes(), expected_audio)
            sidecar = json.loads(output_path.with_suffix(".wav.json").read_text())
            self.assertEqual(metadata["duration_seconds"], 0.1)
            self.assertEqual(metadata["request_id"], "mock-request-id")
            self.assertEqual(sidecar["voice"], narrate.DEFAULT_VOICE)
            self.assertEqual(calls[0]["model"], narrate.DEFAULT_MODEL)
            self.assertEqual(calls[0]["generation_config"]["speech_config"][0]["voice"], "Charon")
            self.assertEqual(len(calls), 1)



    def test_rest_stream_collects_pcm_chunks_and_writes_wav(self) -> None:
        pcm = b"\x00\x00" * 2400
        encoded = base64.b64encode(pcm).decode("ascii")
        body = (
            "event: step.delta\n"
            + "data: "
            + json.dumps({"delta": {"type": "audio", "data": encoded}})
            + "\n\n"
            + "event: interaction.completed\n"
            + 'data: {"id":"stream-request","status":"completed"}\n\n'
        ).encode("utf-8")

        class FakeResponse:
            status = 200

            def __init__(self) -> None:
                self.stream = io.BytesIO(body)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def readline(self):
                return self.stream.readline()

        with patch.object(narrate.urllib.request, "urlopen", return_value=FakeResponse()):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "stream.wav"
                metadata = narrate.generate_narration(
                    "A streaming test script.",
                    output_path,
                    api_key="test-key-never-sent",
                    overwrite=True,
                    request_timeout_seconds=5,
                    transport="rest_stream",
                )

        self.assertEqual(metadata["transport"], "rest_stream")
        self.assertEqual(metadata["request_id"], "stream-request")
        self.assertEqual(metadata["duration_seconds"], 0.1)
        self.assertTrue(output_path.read_bytes().startswith(b"RIFF"))

    def test_api_timeout_fails_fast_without_writing_output(self) -> None:
        class SlowInteractions:
            def create(self, **kwargs):
                time.sleep(0.2)
                return None

        class SlowClient:
            def __init__(self, *, api_key: str):
                self.interactions = SlowInteractions()

        fake_google = types.ModuleType("google")
        fake_google.genai = types.SimpleNamespace(Client=SlowClient)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voice.wav"
            with patch.dict(sys.modules, {"google": fake_google}):
                with self.assertRaisesRegex(narrate.NarrationError, "timed out"):
                    narrate.generate_narration(
                        "A short test script.",
                        output_path,
                        api_key="test-key-never-sent",
                        request_timeout_seconds=0.02,
                        transport="sdk",
                    )
            self.assertFalse(output_path.exists())

    def test_existing_output_is_not_overwritten_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "voice.wav"
            output_path.write_bytes(b"existing")
            with self.assertRaises(narrate.NarrationError):
                narrate.generate_narration("Text", output_path, api_key="unused")
            self.assertEqual(output_path.read_bytes(), b"existing")

    def test_empty_script_is_rejected_before_api_request(self) -> None:
        with self.assertRaises(narrate.NarrationError):
            narrate._read_script(Path("/a/path/that/does/not/exist.txt"))

    def test_non_wav_payload_is_rejected(self) -> None:
        fake_interaction = types.SimpleNamespace(
            output_audio=types.SimpleNamespace(data=base64.b64encode(b"not wav").decode())
        )
        with self.assertRaises(narrate.NarrationError):
            narrate._extract_audio(fake_interaction)


if __name__ == "__main__":
    unittest.main()
