"""Offline real screenshot-file tests for TikTok/Shorts evidence contract.

Fixtures are generated with FFmpeg and intentionally are NOT genuine app UI
captures. Tests prove receipt binding only, not human interface clearance.
"""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from audits.mobile_caption_ui_v11 import inspect, MobileUIReviewError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MobilePlatformUIV11Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "captions").mkdir()
        (self.root / "rendered").mkdir()
        self.manifest = self.root / "manifest.json"
        self.ass = self.root / "captions/narration.ass"
        self.ass.write_text("ASS fixture bytes")
        self.video = self.root / "rendered/test-output.mp4"
        self.video.write_bytes(b"synthetic video fixture bytes")
        self.manifest.write_text(json.dumps({"video_id":"new-story","captions":{"path":"captions/narration.ass"}}))
        self.receipt = self.root / "rendered/caption-platform-ui-review-v11.json"
        self.screens = []
        for index, color in enumerate(("black", "white"), 1):
            png = self.root / f"rendered/example-{index}.png"
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:r=1",
                "-frames:v", "1", "-update", "1", "-y", str(png)],
                check=True, capture_output=True, timeout=40)
            self.screens.append(png)

    def payload(self):
        return {
            "schema_version":"1.1","video_id":"new-story",
            "video_path":"rendered/test-output.mp4","video_sha256":sha(self.video),
            "caption_sha256":sha(self.ass),
            "platforms":{
                name:{
                    "status":"PASS",
                    "view_mode":"real_platform_ui",
                    "reviewer":"fixture-researcher",
                    "captured_at_utc":"2026-11-04T20:00:00Z",
                    "device_model":"synthetic-tests-not-real-device",
                    "screenshot_path":f"rendered/{self.screens[i].name}",
                    "screenshot_sha256":sha(self.screens[i]),
                }
                for i,name in enumerate(("tiktok","youtube_shorts"))
            }
        }

    def write(self, data):
        self.receipt.write_text(json.dumps(data))

    def test_no_receipt_fails_closed_and_never_claims_mobile_clearance(self):
        result=inspect(self.manifest)
        self.assertEqual(result["status"],"MANUAL_UI_REVIEW_REQUIRED")
        self.assertFalse(result["official_pixel_safe_zone_certified"])

    def test_both_bound_screenshot_files_are_structurally_accepted_only(self):
        self.write(self.payload())
        report=inspect(self.manifest)
        self.assertEqual(report["status"],"UI_EVIDENCE_ATTESTED")
        self.assertFalse(report["all_device_coverage_certified"])
        self.assertFalse(report["approved_for_auto_publication"])

    def test_missing_youtube_shorts_review_blocks(self):
        data=self.payload()
        del data["platforms"]["youtube_shorts"]
        self.write(data)
        self.assertEqual(inspect(self.manifest)["status"],"MANUAL_UI_REVIEW_REQUIRED")

    def test_same_image_recycled_for_two_apps_blocks(self):
        data=self.payload()
        data["platforms"]["youtube_shorts"]["screenshot_path"]=data["platforms"]["tiktok"]["screenshot_path"]
        data["platforms"]["youtube_shorts"]["screenshot_sha256"]=data["platforms"]["tiktok"]["screenshot_sha256"]
        self.write(data)
        report=inspect(self.manifest)
        self.assertEqual(report["status"],"MANUAL_UI_REVIEW_REQUIRED")
        self.assertTrue(any("distinct" in x for x in report["issues"]))

    def test_stale_render_bytes_are_rejected(self):
        self.write(self.payload())
        self.video.write_bytes(b"new output after preview")
        self.assertEqual(inspect(self.manifest)["status"],"MANUAL_UI_REVIEW_REQUIRED")

    def test_stale_caption_bytes_are_rejected(self):
        self.write(self.payload())
        self.ass.write_text("modified but not reviewed")
        self.assertEqual(inspect(self.manifest)["status"],"MANUAL_UI_REVIEW_REQUIRED")

    def test_template_screenshot_not_real_platform_is_rejected(self):
        data=self.payload()
        data["platforms"]["tiktok"]["view_mode"]="mockup_template"
        self.write(data)
        self.assertEqual(inspect(self.manifest)["status"],"MANUAL_UI_REVIEW_REQUIRED")

    def test_image_magic_only_without_decodable_frame_is_rejected(self):
        data=self.payload()
        self.screens[0].write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake")
        data["platforms"]["tiktok"]["screenshot_sha256"]=sha(self.screens[0])
        self.write(data)
        self.assertEqual(inspect(self.manifest)["status"],"MANUAL_UI_REVIEW_REQUIRED")

    def test_path_traversal_rejected(self):
        data=self.payload()
        data["video_path"]="../other-video.mp4"
        self.write(data)
        with self.assertRaises(MobileUIReviewError):
            inspect(self.manifest)


if __name__=="__main__":
    unittest.main()
