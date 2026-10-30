from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from experimental.v72.reuse_first import plan, ReuseFirstError
ROOT = Path(__file__).resolve().parents[1]
C = ROOT / "experimental/v72/verified_preview_001.json"
M = ROOT / "episodes/video-001/preview-manifest.json"
S = ROOT / "episodes/video-001/script.txt"
class ReuseFirstTests(unittest.TestCase):
    def test_successful_original_preview_is_reused_as_candidate(self):
        report = plan(M, S, C)
        self.assertEqual(report["status"],"EXISTING_PREVIEW_FOUND_INPUTS_MATCH")
        self.assertEqual(report["artifacts_found"],9)
        self.assertFalse(report["rerender_requested"])
        self.assertFalse(report["tts_called"])
        self.assertFalse(report["release_approved"])
        self.assertFalse(report["drive_byte_hashes_verified_in_this_plan"])
        self.assertIn("MISSING_DELIVERED",report["stages"]["caption_alignment"])
    def test_script_change_invalidates(self):
        with tempfile.TemporaryDirectory() as td:
            script=Path(td)/"script.txt"
            script.write_bytes(S.read_bytes()+b" changed")
            report=plan(M,script,C)
            self.assertEqual(report["status"],"INPUTS_CHANGED_REVIEW_REQUIRED")
            self.assertEqual(report["stages"]["narration"],"INVALIDATE_AND_REASSESS")
    def test_manifest_change_invalidates(self):
        with tempfile.TemporaryDirectory() as td:
            manifest=Path(td)/"preview-manifest.json"
            x=json.loads(M.read_text(encoding="utf-8")); x["voice"]["speaking_rate"]=0.7
            manifest.write_text(json.dumps(x),encoding="utf-8")
            report=plan(manifest,S,C)
            self.assertEqual(report["status"],"INPUTS_CHANGED_REVIEW_REQUIRED")
    def test_cross_episode_reuse_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            manifest=Path(td)/"manifest.json"
            x=json.loads(M.read_text(encoding="utf-8"));x["video_id"]="episode-002"
            manifest.write_text(json.dumps(x),encoding="utf-8")
            with self.assertRaisesRegex(ReuseFirstError,"Cross-episode"):
                plan(manifest,S,C)
    def test_bad_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"catalog.json"
            data=json.loads(C.read_text(encoding="utf-8"))
            data["artifacts"][0]["md5"]=""
            p.write_text(json.dumps(data))
            with self.assertRaises(ReuseFirstError):
                plan(M,S,p)
if __name__=="__main__":unittest.main()
