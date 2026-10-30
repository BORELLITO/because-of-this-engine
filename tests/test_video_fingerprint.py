import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.video_asset_contract import (
    FINGERPRINT_FRAME_BYTES,
    perceptual_hash,
    sha256_file,
    validate_asset_record,
)


class VideoFingerprintTests(unittest.TestCase):
    def _run(self, calls, command, **kwargs):
        calls.append(command)
        timestamp = float(command[command.index("-ss") + 1])
        path = command[command.index("-i") + 1]
        # Simulate distinct RGB content at every sampled position.  The
        # important regression is that the detector never depends on frame 0.
        base = 32 if "clip-a" in path else 64
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

    def test_hydrated_fingerprint_overrides_toolchain_drift_after_sha_check(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as handle:
            path = Path(handle.name)
            path.write_bytes(b"runner-hydrated-bytes")
            record = {
                "asset_id": "asset-runtime",
                "path": path.name,
                "provider": "pexels",
                "source_page_url": "https://www.pexels.com/video/123",
                "license": "approved-preview-license",
                "sha256": sha256_file(path),
                "perceptual_hash": "a" * 64,
                "hydrated_perceptual_hash": "b" * 64,
                "rights_status": "PREVIEW_ONLY",
                "approved_for_render": False,
                "preview_only": True,
                "preview_only_reason": "human review pending",
            }
            with patch("production.video_asset_contract.ffprobe", return_value={"duration": 1.0}), \
                 patch("production.video_asset_contract._validate_clean_frame_layout"), \
                 patch("production.video_asset_contract.perceptual_hash", return_value="b" * 64):
                result = validate_asset_record(record, path.parent, "because-of-this-video-001", mode="draft-preview")
            self.assertEqual(result["animation_fingerprint"], "b" * 64)


if __name__ == "__main__":
    unittest.main()
