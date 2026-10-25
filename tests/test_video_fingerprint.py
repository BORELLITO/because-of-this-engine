import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from production.video_asset_contract import (
    FINGERPRINT_FRAME_BYTES,
    perceptual_hash,
)


class VideoFingerprintTests(unittest.TestCase):
    def _run(self, calls, command, **kwargs):
        calls.append(command)
        timestamp = float(command[command.index("-ss") + 1])
        path = command[command.index("-i") + 1]
        # Simulate distinct RGB content at every sampled position.  The
        # important regression is that the detector never depends on frame 0.
        base = 1 if "clip-a" in path else 2
        value = min(255, base + int(timestamp * 10))
        return subprocess.CompletedProcess(command, 0, stdout=bytes([value]) * FINGERPRINT_FRAME_BYTES, stderr=b"")

    def test_fingerprint_samples_multiple_temporal_positions(self) -> None:
        calls = []
        with patch("production.video_asset_contract.subprocess.run", side_effect=lambda command, **kwargs: self._run(calls, command, **kwargs)):
            first = perceptual_hash(Path("clip-a.mp4"), duration=10.0)
            second = perceptual_hash(Path("clip-b.mp4"), duration=10.0)

        self.assertEqual(len(calls), 10)
        self.assertEqual(
            [float(command[command.index("-ss") + 1]) for command in calls[:5]],
            [1.5, 3.5, 5.0, 6.5, 8.5],
        )
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, "f" * 64)
        self.assertEqual(len(first), 64)


if __name__ == "__main__":
    unittest.main()
