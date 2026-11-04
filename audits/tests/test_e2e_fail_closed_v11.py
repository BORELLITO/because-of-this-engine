"""Integration attack-matrix across real G2/G3/G5/G6/G8/G9/G10/G11.

No network, TTS, render, publication, source archival modification or 3rd-party
media. Synthetic fixtures and mocked *non-target* boundaries are intentional:
G0 canonical schema, expensive G3 scene codec checks, G1 editorial creation,
word recognition and actual ffprobe have independent tests elsewhere.
This suite validates gate composition and fail-closed status wiring, not
production readiness or evidence of real copyright/platform approval.
"""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from production.quality_gates import evaluate


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EndToEndGateAttackMatrixV11(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.ep = self.root/"episodes"/"fixture-new"
        (self.ep/"audio").mkdir(parents=True)
        (self.ep/"rendered").mkdir()
        self.music = self.ep/"music.wav"
        self.music.write_bytes(b"synthetic new music identity not an actual song")
        (self.ep/"audio"/"narration.wav").write_bytes(b"no Gemini generated")
        self.movie = self.ep/"rendered"/"fictional-final.mp4"
        self.movie.write_bytes(b"synthetic file fixture, not a playable film")
        self.manifest = self.ep/"manifest.json"
        self.asset_url="https://mixkit.co/free-stock-video/synthetic-security-test-998877/"
        self.asset_digest="a"*64
        self.m = {
            "video_id":"fictional-fixture",
            "story_profile":{"truth_mode":"DECLARED_FICTION"},
            "story_creation":{"truth":{"disclosure":"Original fictional test only."}},
            "scenes":[{"scene_id":"S01","asset":{
                "asset_id":"fictitious-clip",
                "provider":"mixkit",
                "source_page_url":self.asset_url,
                "provider_asset_id":"998877",
                "license":"synthetic fixture (not commercial rights)",
                "sha256":self.asset_digest,
                "rights_status":"APPROVED",
                "approved_for_render":True,
                "drive_file_id":"Fixture-Drive-AaBb123",
                "author":"Synthetic Test",
                "acquisition_timestamp":"2026-11-04T19:30:00Z",
                "original_filename":"unavailable-in-production-fixture.mp4",
                "mime_type":"video/mp4","duration_seconds":6,
                "width":1080,"height":1920,
                "filesize_bytes":100,
                "job_ownership":"fictional-fixture","scene_usage":"S01",
                "rights_review":{
                    "status":"PASS","reviewer":"synthetic-contract-reviewer",
                    "reviewed_at_utc":"2026-11-04T19:30:00Z",
                    "asset_sha256":self.asset_digest,
                    "source_page_url":self.asset_url,
                    "evidence_url":"https://example.org/offline-fixture-evidence",
                    "authorized_platforms":["youtube","tiktok"],
                }
            }}],
            "voice":{
                "provider":"gemini_tts","voice_name":"Charon",
                "model_or_voice_type":"gemini-3.8-flash-tts",
                "language_code":"en-US","style":"restrained",
            },
            "audio":{"path":"audio/narration.wav"},
            "music":{
                "path":"music.wav","track_id":"fictional-fresh-001",
                "sha256":digest(self.music.read_bytes()),
                "drive_file_id":"Music-Fixture-New",
                "source":"engine_generated",
                "generation":{"script":"production/generate_suspense_bed.py"},
                "license":"Original synthetic test generation",
                "license_status":"APPROVED",
                "commercial_use":True,"preview_only":False,
                "reuse_status":"FRESH",
                "complete_track_reuse":"forbidden",
                "origin_recorded_at":"2026-11-04T19:30:00Z",
                "similarity_review":{"status":"PASS"},
                "device_tests":{"phone":"PASS","headphones":"PASS","low_volume":"PASS"},
            },
            "output":{"path":"rendered/{video_id}-{mode}.mp4"},
            "preview_approval":{
                "status":"PASS","reviewer":"synthetic-qa",
                "approved_at":"2026-11-04T19:30:00Z",
                "approved_video_sha256":digest(self.movie.read_bytes())
            },
            "editorial_qa":{
                "status":"PASS","reviewer":"synthetic-qa",
                "reviewed_at":"2026-11-04T19:30:00Z","score":9
            },
            "approval_package":{
                key:True for key in (
                    "video","script","narration","music_effects","captions_karaoke",
                    "packaging","gate_statuses","rights_origins","failures_fixed","final_hash"
                )
            },
        }
        # Use manifest-template format on the exact media path that the release
        # validator resolves; never place any fixture in the production tree.
        destination = self.ep/"rendered"/"fictional-fixture-final.mp4"
        destination.write_bytes(self.movie.read_bytes())
        self.movie = destination
        self.save()
        self.release = self.ep/"rendered"/"test-release.json"
        self.r={
            "status":"VIDEO_RELEASE_VALIDATED",
            "output_sha256":digest(self.movie.read_bytes()),
            "technical_qa":"PASS",
            "dimensions":"1080x1920","fps":60.0,"duration_seconds":66.5,
            "audio_mix_profile":{
                "master":"narration_locked","music_ducking":"sidechain_compress",
                "music_volume":0.12
            }
        }
        self.write_release()
        (self.root/"episodes"/"asset-memory-registry.json").write_text(
            json.dumps({"schema_version":1,"assets":[]})
        )
        self.audio_registry=self.root/"episodes"/"audio-memory-registry.json"
        self.music_entry={
            "episode_id":"fictional-fixture",
            "track_id":"fictional-fresh-001",
            "sha256":digest(self.music.read_bytes()),
            "drive_file_id":"Music-Fixture-New"
        }
        self.write_audio_registry([self.music_entry])
        (self.ep/"rendered"/"visual-story-qa-final.json").write_text(
            json.dumps({"status":"VISUAL_STORY_QA_PASS"})
        )
        (self.ep/"rendered"/"narration-coverage.json").write_text(
            json.dumps({"status":"STORY_INTELLIGENCE_PASS",
                        "narration_coverage":{"timing_status":"FORCED_ALIGNMENT_SCENE_TIMES_PASS"}})
        )

    def save(self):
        self.manifest.write_text(json.dumps(self.m),encoding="utf-8")

    def write_release(self):
        self.release.write_text(json.dumps(self.r),encoding="utf-8")

    def write_audio_registry(self,tracks):
        self.audio_registry.write_text(json.dumps({"schema_version":"2.0","tracks":tracks}))

    def evaluate_final(self, *, real_mobile_ui_attested=True, post=None):
        """Only unrelated heavyweight feature engines are mocked."""
        with ExitStack() as stack:
            stack.enter_context(patch("production.quality_gates.validate_canonical_manifest",
                                      return_value={"profile_id":"fixture-canonic"}))
            stack.enter_context(patch("production.quality_gates._story_creation",
                                      return_value=("PASS: synthetic editorial",{"status":"STORY_CREATION_PASS"})))
            stack.enter_context(patch("production.quality_gates.validate_manifest",
                                      return_value={"scenes":self.m["scenes"]}))
            stack.enter_context(patch("production.quality_gates.validate_packaging",
                                      return_value={"status":"PASS","errors":[]}))
            stack.enter_context(patch("production.quality_gates._captions",
                                      return_value=("PASS","fixture-only word timing")))
            if real_mobile_ui_attested:
                stack.enter_context(patch("production.quality_gates.inspect_mobile_caption_ui",
                                          return_value={"status":"UI_EVIDENCE_ATTESTED"}))
            stack.enter_context(patch("production.quality_gates.inspect_video_media",
                                      return_value={"width":1080,"height":1920,"fps":60.0,
                                                    "duration":66.5,"has_audio":True}))
            return evaluate(self.manifest,"final","final",
                            release_report_path=self.release,
                            post_publication_receipt_path=post)

    @staticmethod
    def gates(result):
        return {g["code"]:g["status"] for g in result["gates"]}

    def test_valid_fixture_can_reach_manual_publication_not_published(self):
        result=self.evaluate_final()
        self.assertEqual(result["status"],"GATES_PASS",self.gates(result))
        self.assertEqual(result["release_readiness"],"READY_FOR_MANUAL_PUBLICATION")
        self.assertFalse(result["publication_verified"])
        self.assertEqual(self.gates(result)["G11"],"DEFERRED")
        self.assertEqual(result["next_action"],"MANUAL_PUBLICATION_AND_G11_RECEIPT")

    def test_valid_metadata_rights_without_human_attestation_is_rejected(self):
        del self.m["scenes"][0]["asset"]["rights_review"]
        self.save()
        result=self.evaluate_final()
        self.assertEqual(self.gates(result)["G2"],"BLOCKED")
        self.assertIn("G2",result["next_action"])

    def test_valid_rights_attestation_passes_structural_g2_gate(self):
        result=self.evaluate_final()
        self.assertEqual(self.gates(result)["G2"],"PASS")

    def test_unapproved_platform_in_rights_evidence_blocks(self):
        self.m["scenes"][0]["asset"]["rights_review"]["authorized_platforms"]=["youtube"]
        self.save()
        self.assertEqual(self.gates(self.evaluate_final())["G2"],"BLOCKED")

    def test_wrong_bound_asset_hash_in_rights_evidence_blocks(self):
        self.m["scenes"][0]["asset"]["rights_review"]["asset_sha256"]="b"*64
        self.save()
        self.assertEqual(self.gates(self.evaluate_final())["G2"],"BLOCKED")

    def test_source_video_reuse_in_another_episode_blocks_g3(self):
        old=self.root/"episodes"/"old"
        old.mkdir()
        (old/"preview-manifest.json").write_text(json.dumps({
            "video_id":"historic-story",
            "scenes":[self.m["scenes"][0]],
        }))
        r=self.evaluate_final()
        self.assertEqual(self.gates(r)["G3"],"BLOCKED")

    def test_music_file_reused_with_different_track_label_blocks_g5(self):
        old=self.root/"episodes"/"old"
        old.mkdir()
        (old/"manifest.json").write_text(json.dumps({
            "video_id":"historic-story",
            "music":{"track_id":"other-name","sha256":digest(self.music.read_bytes())}
        }))
        result=self.evaluate_final()
        self.assertEqual(self.gates(result)["G5"],"BLOCKED")

    def test_music_removed_from_global_registry_blocks_g5(self):
        self.write_audio_registry([])
        self.assertEqual(self.gates(self.evaluate_final())["G5"],"BLOCKED")

    def test_forged_audio_sha_blocks_g5_despite_registry(self):
        self.m["music"]["sha256"]="b"*64
        self.save()
        self.write_audio_registry([{**self.music_entry,"sha256":"b"*64}])
        self.assertEqual(self.gates(self.evaluate_final())["G5"],"BLOCKED")

    def test_missing_actual_platform_capture_blocks_g6(self):
        self.assertEqual(self.gates(self.evaluate_final(real_mobile_ui_attested=False))["G6"],"BLOCKED")

    def test_release_claim_without_actual_mp4_blocks_g8_g9(self):
        self.movie.unlink()
        g=self.gates(self.evaluate_final())
        self.assertEqual(g["G8"],"BLOCKED")
        self.assertEqual(g["G9"],"BLOCKED")

    def test_release_claim_after_mp4_changes_blocks_g8_g9(self):
        self.movie.write_bytes(b"tampered video bytes")
        g=self.gates(self.evaluate_final())
        self.assertEqual(g["G8"],"BLOCKED")
        self.assertEqual(g["G9"],"BLOCKED")

    def test_wrong_video_profile_blocks_g8_g9(self):
        with ExitStack() as stack:
            stack.enter_context(patch("production.quality_gates.inspect_video_media",
                                      return_value={"width":720,"height":1280,"fps":30.0,
                                                    "duration":45.0,"has_audio":True}))
            # Drive the same isolated check without overriding it with the fixture.
            from production.quality_gates import _release_media_integrity
            status,_,_=_release_media_integrity(self.m,self.ep,"final",self.r)
        self.assertEqual(status,"BLOCKED")

    def test_preview_approval_must_be_bound_to_exact_final_mp4(self):
        self.m["preview_approval"]["approved_video_sha256"]="a"*64
        self.save()
        self.assertEqual(self.gates(self.evaluate_final())["G8"],"BLOCKED")

    def test_missing_human_editorial_approval_blocks_g10(self):
        self.m["editorial_qa"]["status"]="PENDING"
        self.save()
        self.assertEqual(self.gates(self.evaluate_final())["G10"],"BLOCKED")

    def test_forged_publication_receipt_cannot_close_g11(self):
        receipt=self.ep/"rendered"/"claimed-post.json"
        payload={
            "status":"PASS","platform":"youtube","url":"https://example.com/fake",
            "file_available":True,"duration_ok":True,"audio_ok":True,
            "captions_ok":True,"framing_ok":True,"title_ok":True,
            "thumbnail_ok":True,"description_ok":True,"comment_ok":True,
            "divergences":[],
        }
        receipt.write_text(json.dumps(payload))
        result=self.evaluate_final(post=receipt)
        self.assertEqual(self.gates(result)["G11"],"DEFERRED")
        self.assertFalse(result["publication_verified"])
        self.assertEqual(result["next_action"],"VERIFY_PUBLISHED_URLS_EXTERNAL")

    def test_invalid_publication_claim_causes_block(self):
        receipt=self.ep/"rendered"/"claimed-post.json"
        receipt.write_text(json.dumps({"status":"PASS","platform":"youtube"}))
        result=self.evaluate_final(post=receipt)
        self.assertEqual(self.gates(result)["G11"],"BLOCKED")
        self.assertFalse(result["publication_verified"])

    def test_multi_gate_failure_reports_blockers_before_next_action(self):
        self.m["story_creation"]["truth"]["disclosure"]=""
        self.m["editorial_qa"]["status"]="PENDING"
        self.save()
        self.write_audio_registry([])
        self.movie.unlink()
        result=self.evaluate_final(real_mobile_ui_attested=False)
        self.assertEqual(result["status"],"GATES_BLOCKED")
        self.assertTrue(result["next_action"].startswith("RESOLVE_GATES:"))
        for gate in ("G2","G5","G6","G8","G9","G10"):
            self.assertIn(gate,result["next_action"])

    def test_evaluation_does_not_modify_any_fixture_files(self):
        before={str(p.relative_to(self.root)):digest(p.read_bytes()) for p in self.root.rglob("*") if p.is_file()}
        self.evaluate_final()
        after={str(p.relative_to(self.root)):digest(p.read_bytes()) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before,after)


if __name__=="__main__":
    unittest.main()
