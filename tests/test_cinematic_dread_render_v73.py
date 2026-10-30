from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.cinematic_dread import PROFILE, plan
from production.atmosphere_qa import luma_metrics, verify_report_against_media, AtmosphereQAError
from production.render_video_episode import scene_filter


class DreadRenderAndQATests(unittest.TestCase):
    def test_grain_and_vignette_are_picture_only(self):
        base={"enabled":True,"brightness":-0.03,"contrast":1.1,"saturation":0.8,"gamma":0.98,
              "vignette":True,"cinematic_suspense":{"enabled":True,"cool_shadows":0.05,
              "warm_highlights":0.004,"motion_strength":0.02,"push_in":0.03},
              "_dread_grain_strength":4,"_dread_vignette_angle":"PI/4.8"}
        graph=scene_filter(1080,1920,0.5,0.5,base,7.0)
        self.assertIn("noise=alls=4:allf=t",graph)
        self.assertIn("vignette=PI/4.8",graph)
        self.assertNotIn("drawtext",graph)
        self.assertNotIn("subtitles",graph)
    def test_unknown_grain_or_vignette_fails_closed(self):
        from production.render_video_episode import RenderError
        base={"enabled":True,"vignette":True,"_dread_grain_strength":99}
        with self.assertRaises(RenderError):scene_filter(1080,1920,0.5,0.5,base)
        base["_dread_grain_strength"]=2
        base["_dread_vignette_angle"]="eval=delete"
        with self.assertRaises(RenderError):scene_filter(1080,1920,0.5,0.5,base)
    def test_luma_gate_rejects_all_black_or_clipped_highlights(self):
        self.assertEqual(luma_metrics(bytes([0])*9216)["status"],"BLOCKED")
        self.assertEqual(luma_metrics(bytes([255])*9216)["status"],"BLOCKED")
        self.assertEqual(luma_metrics(bytes([80])*9216)["status"],"PASS")
    def test_missing_qa_report_blocks_opt_in_release(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            manifest=root/"manifest.json"
            manifest.write_text(json.dumps({"video_id":"e1",
                "atmosphere":{"enabled":True,"profile":PROFILE,"director_review":"PENDING"},
                "scenes":[{"scene_id":"S01","story_beat":"hook","duration":8}]}))
            mp4=root/"foo.mp4";mp4.write_bytes(b"rendered")
            with self.assertRaisesRegex(AtmosphereQAError,"Missing"):verify_report_against_media(manifest,mp4,"draft-preview")
    def test_old_manifest_never_requires_new_qa(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"manifest.json";p.write_text(json.dumps({"video_id":"e1"}))
            self.assertEqual(verify_report_against_media(p,Path(td)/"absent.mp4","draft-preview")["status"],"NOT_APPLICABLE")
    def test_stale_sha_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/"rendered").mkdir()
            p=root/"manifest.json";m={"video_id":"e1","atmosphere":{"enabled":True,
                 "profile":PROFILE,"director_review":"PENDING"},"scenes":[{"scene_id":"S01","duration":6,"story_beat":"hook"}]}
            p.write_text(json.dumps(m))
            vid=root/"rendered"/"x.mp4";vid.write_bytes(b"media")
            (root/"rendered"/"atmosphere-qa-draft-preview.json").write_text(json.dumps({
               "status":"ATMOSPHERE_TECHNICAL_PASS","profile":PROFILE,"mode":"draft-preview",
               "manifest_sha256":"wrong","render_sha256":"wrong","scene_count":1,"blocked_scenes":[]}))
            with self.assertRaisesRegex(AtmosphereQAError,"Stale"):verify_report_against_media(p,vid,"draft-preview")

if __name__ == "__main__": unittest.main()
