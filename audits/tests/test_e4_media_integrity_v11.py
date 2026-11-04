"""E4 verifier tests with generated local video; no credentials or external assets."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from audits.e4_media_integrity_v11 import verify, _correlation


class E4MediaIntegrityV11Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "source.mp4"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error",
             "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=10:duration=2",
             "-pix_fmt", "yuv420p", "-c:v", "libx264", "-y", str(self.video)],
            capture_output=True, check=True, timeout=40,
        )
        self.manifest = self.root / "manifest.json"

    def scene(self, name, source_file, *, sha=None, size=None):
        b = source_file.read_bytes()
        return {
            "scene_id": name,
            "asset": {
                "asset_id": name + "-asset",
                "path": source_file.name,
                "sha256": sha or hashlib.sha256(b).hexdigest(),
                "filesize_bytes": size if size is not None else len(b),
            },
        }

    def save(self, scenes):
        self.manifest.write_text(
            json.dumps({"video_id": "fixture", "scenes": scenes}), encoding="utf-8"
        )

    def test_actual_bytes_and_three_real_frames_pass(self):
        self.save([self.scene("S01", self.video)])
        before = self.video.read_bytes()
        report = verify(self.manifest, self.root)
        self.assertEqual(report["status"], "E4_TECHNICAL_PASS")
        self.assertEqual(report["verified_clip_count"], 1)
        self.assertEqual(report["decoded_frame_count"], 3)
        self.assertFalse(report["approved_for_new_production"])
        self.assertFalse(report["independent_source_license_verified"])
        self.assertEqual(self.video.read_bytes(), before)

    def test_wrong_checksum_blocks_even_if_video_decodes(self):
        self.save([self.scene("S01", self.video, sha="a" * 64)])
        report = verify(self.manifest, self.root)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["verified_clip_count"], 0)

    def test_wrong_size_blocks(self):
        self.save([self.scene("S01", self.video, size=1)])
        self.assertEqual(verify(self.manifest, self.root)["status"], "BLOCKED")

    def test_independent_asset_copies_get_review_not_false_clearance(self):
        twin = self.root / "copy.mp4"
        shutil.copyfile(self.video, twin)
        self.save([self.scene("S01", self.video), self.scene("S02", twin)])
        report = verify(self.manifest, self.root)
        self.assertEqual(report["status"], "E4_TECHNICAL_PASS_WITH_REVIEW")
        self.assertEqual(report["verified_clip_count"], 2)
        self.assertEqual(report["visual_similarity_candidates"][0]["scene_a"], "S01")
        self.assertFalse(report["human_approved"])

    def test_path_traversal_is_blocked(self):
        data = self.scene("S01", self.video)
        data["asset"]["path"] = "../source.mp4"
        data["asset"]["original_filename"] = ""
        self.save([data])
        report = verify(self.manifest, self.root)
        self.assertEqual(report["status"], "BLOCKED")

    def test_cli_requires_review_when_copies_are_visually_identical(self):
        twin = self.root / "copy.mp4"
        shutil.copyfile(self.video, twin)
        self.save([self.scene("S01", self.video), self.scene("S02", twin)])
        cli = Path(__file__).resolve().parents[1] / "e4_media_integrity_v11.py"
        import sys
        result = subprocess.run(
            [sys.executable, str(cli), "--manifest", str(self.manifest),
             "--media-root", str(self.root)],
            capture_output=True, text=True, timeout=80,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("E4_TECHNICAL_PASS_WITH_REVIEW", result.stdout)

    def test_blank_frames_do_not_prove_visual_identity(self):
        self.assertEqual(_correlation(bytes(4096), bytes(4096)), 0.0)


if __name__ == "__main__":
    unittest.main()
