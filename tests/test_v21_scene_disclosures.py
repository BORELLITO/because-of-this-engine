"""S01 actor + NASA 2020 source truth gates, including real ffmpeg smoke tests.

These tests never render an episode, publish, or use voice/TTS.
"""
from __future__ import annotations
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from production.scene_disclosures_v21 import (
    ACTOR_ID, ACTOR_SHOT, NASA_ID, NASA_SHOT, ACTOR_SAMPLE_SHA256,
    NASA_SAMPLE_SHA256, validate_disclosure, audit_repository,
    ffmpeg_actor_overlay, ffmpeg_nasa_overlay, load_for_preview,
)
from production.render_v21_preview import render_scene, PreviewRenderError

ROOT = Path(__file__).resolve().parents[1]
SCENE_PATH = ROOT / "episodes/episode-005/visual/scene-asset-manifest.json"
DISCLOSURE_PATH = ROOT / "episodes/episode-005/visual/scene-disclosures-v21.json"
RECORD_PATH = ROOT / "episodes/episode-005/production-record.json"


class ScientificAndActorTruthLabelsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
        cls.disclosures = json.loads(DISCLOSURE_PATH.read_text(encoding="utf-8"))
        cls.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))

    def test_both_critical_disclosures_exact_and_release_not_proven(self):
        result = validate_disclosure(self.scene, self.disclosures)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(set(result["checked_shots"]), {ACTOR_SHOT, NASA_SHOT})
        self.assertEqual(result["scene_count"], 2)
        self.assertTrue(result["on_frame_sample_qa_pass"])
        self.assertFalse(result["final_video_verified"])
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(audit_repository(self.record, repo_root=ROOT)["status"], "PASS")
        self.assertEqual(set(load_for_preview(SCENE_PATH, self.scene)), {ACTOR_ID, NASA_ID})

    def test_known_sample_hashes_and_display_text_binding(self):
        actor, nasa = self.disclosures["disclosures"]
        self.assertEqual(actor["asset_id"], ACTOR_ID)
        self.assertEqual(nasa["asset_id"], NASA_ID)
        self.assertEqual(actor["verification"]["sample_video_sha256"], ACTOR_SAMPLE_SHA256)
        self.assertEqual(nasa["overlay_qa_receipt"]["sample_video_sha256"], NASA_SAMPLE_SHA256)
        self.assertEqual(actor["overlay"]["line_1"], "DRAMATIZATION - NOT ARCHIVAL FOOTAGE")
        self.assertEqual(nasa["overlay"]["line_1"], "NASA GEOS-5 MODEL (2020)")
        self.assertEqual(nasa["overlay"]["line_2"], "Illustration - NOT 1983 sensor footage")
        self.assertIn("NOT Stanislav Petrov", actor["delivery_description_footer"])
        self.assertIn("Greg Shirah", nasa["delivery_description_footer"])
        self.assertIn("Ryan Fitzgibbons", nasa["delivery_description_footer"])

    def test_no_self_certification_of_final_video_or_publication(self):
        for entry in self.disclosures["disclosures"]:
            self.assertFalse(entry["final_assembled_video_metadata_verified"])
            self.assertFalse(entry["final_publication_verified"])
        self.assertEqual(self.disclosures["publication_policy"], "manual_only")
        self.assertFalse(self.disclosures["production_enablement"])

    def test_moving_actor_to_old_s03_source_role_is_blocked(self):
        scene = copy.deepcopy(self.scene)
        actor = next(x for x in scene["shot_assignments"] if x["shot_id"] == ACTOR_SHOT)
        actor["shot_id"] = "S03"
        report = validate_disclosure(scene, self.disclosures)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("S01" in msg for msg in report["failures"]))

    def test_edited_model_source_sha_or_date_is_blocked(self):
        changed = copy.deepcopy(self.disclosures)
        nasa = next(x for x in changed["disclosures"] if x["asset_id"] == NASA_ID)
        nasa["sha256"] = "f" * 64
        nasa["source_release_date"] = "1983-09-26"
        checked = validate_disclosure(self.scene, changed)
        self.assertEqual(checked["status"], "BLOCKED")
        self.assertTrue(any("source" in x for x in checked["failures"]))
        self.assertTrue(any("truth" in x for x in checked["failures"]))

    def test_deleting_actor_label_blocks(self):
        changed = copy.deepcopy(self.disclosures)
        actor = next(x for x in changed["disclosures"] if x["asset_id"] == ACTOR_ID)
        actor["overlay"]["line_1"] = "THIS IS ACTUAL STANISLAV PETROV"
        self.assertEqual(validate_disclosure(self.scene, changed)["status"], "BLOCKED")

    def test_false_final_render_status_blocks(self):
        changed = copy.deepcopy(self.disclosures)
        changed["disclosures"][0]["final_assembled_video_metadata_verified"] = True
        self.assertEqual(validate_disclosure(self.scene, changed)["status"], "BLOCKED")

    def test_missing_svs_credits_or_platform_footer_blocks(self):
        changed = copy.deepcopy(self.disclosures)
        nasa = next(x for x in changed["disclosures"] if x["asset_id"] == NASA_ID)
        nasa["credits"]["visualizers"] = ["Unknown"]
        nasa["delivery_description_footer"] = "NASA model, free to use"
        self.assertEqual(validate_disclosure(self.scene, changed)["status"], "BLOCKED")

    def test_tampered_sample_receipt_blocks(self):
        changed = copy.deepcopy(self.disclosures)
        changed["disclosures"][0]["verification"]["sample_video_sha256"] = "f" * 64
        self.assertEqual(validate_disclosure(self.scene, changed)["status"], "BLOCKED")

    def test_ffmpeg_filters_are_frozen_not_dynamic(self):
        actor, nasa = self.disclosures["disclosures"]
        self.assertIn("DRAMATIZATION - NOT ARCHIVAL FOOTAGE", ffmpeg_actor_overlay(actor))
        self.assertIn("NASA GEOS-5 MODEL (2020)", ffmpeg_nasa_overlay(nasa))
        self.assertIn("NOT 1983 sensor footage", ffmpeg_nasa_overlay(nasa))
        with self.assertRaises(ValueError):
            ffmpeg_actor_overlay({"overlay": {"line_1": "UNVERIFIED"}})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires real ffmpeg")
    def test_actual_ffmpeg_scene_renderer_burns_both_truth_labels(self):
        with tempfile.TemporaryDirectory(prefix="v21-scene-truth-") as temp:
            path = Path(temp)
            sample = path / "synthetic-nonhistorical-source.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                "-i", "color=c=black:s=540x960:r=25",
                "-t", "1.0", "-c:v", "libx264",
                "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                str(sample)
            ], check=True, timeout=45)
            for candidate_id in (ACTOR_ID, NASA_ID):
                entry = next(x for x in self.disclosures["disclosures"]
                             if x["asset_id"] == candidate_id)
                output = path / (candidate_id[:6] + ".mp4")
                render_scene({
                    "candidate_id": candidate_id, "shot_id": entry["shot_id"],
                    "duration": 0.6,
                }, sample, output, disclosure=entry)
                self.assertTrue(output.is_file() and output.stat().st_size > 1000)
                meta = subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries",
                    "stream=width,height", "-of", "json", str(output)
                ], timeout=20)
                video = json.loads(meta)["streams"][0]
                self.assertEqual((video["width"], video["height"]), (1080, 1920))
                # Drawtext places white pixels in dark test frames, even with
                # cinematic grade/fade. No OCR or TTS is necessary.
                raw = subprocess.check_output([
                    "ffmpeg", "-v", "error", "-ss", "0.30", "-i", str(output),
                    "-frames:v", "1", "-vf", "crop=800:150:140:350",
                    "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"
                ], timeout=30)
                self.assertGreater(max(raw), 170, candidate_id)
                self.assertLess(min(raw), 90, candidate_id)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires real ffmpeg")
    def test_renderer_refuses_unlabeled_real_actor_even_when_video_exists(self):
        with tempfile.TemporaryDirectory() as root:
            input_file = Path(root) / "clip.mp4"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi",
                "-i","color=black:s=320x560:r=25","-t","0.8",
                "-pix_fmt","yuv420p",str(input_file)],check=True,timeout=45)
            with self.assertRaisesRegex(PreviewRenderError, "mandatory"):
                render_scene({"candidate_id":ACTOR_ID,"duration":0.5},
                             input_file,Path(root)/"forbidden.mp4",disclosure=None)


if __name__ == "__main__":
    unittest.main()
