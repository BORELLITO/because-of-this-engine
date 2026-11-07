"""Final-drive V2.1 proof cannot be bypassed by flags or missing receipts.

All positive fixtures use mock sub-gates and local fake master bytes;
actual FFmpeg mix/master verification has separate real-media tests.
Nothing in these tests writes to Drive or publishes.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.final_delivery_v21 import verify_drive_video_delivery
from production.google_drive_delivery import DeliveryError, deliver


class FinalDeliveryGateTests(unittest.TestCase):
    def setUp(self):
        self.ctx=tempfile.TemporaryDirectory()
        self.addCleanup(self.ctx.cleanup)
        self.root=Path(self.ctx.name)
        self.master=self.root/"episode-test-final.mp4"
        self.master.write_bytes(b"fake future final master for dry-run tests"*100)
        self.report=self.root/"mix-receipt.json"
        self.report.write_text(json.dumps({"episode_id":"episode-test","ffmpeg_argv":["synthetic"]}))
        self.policy=self.root/"policy.json"
        self.record=self.root/"record.json"
        self.p={
            "active_engine_version":"2.1",
            "canonical_entrypoint":"production/canonical_entrypoint.py",
            "voice_provider":"gemini_tts",
            "voice_policy":{"voice_name":"Charon"},
            "publication_policy":"manual_only",
            "production_enablement":True,
            "final_drive_delivery_enablement":True,
        }
        self.r={
            "episode_id":"episode-test",
            "production_enablement":True,
            "render_authorization":{"status":"APPROVED"},
            "render_contract":{"width":1080,"height":1920,"fps":60,
                               "render_executed":True},
            "tts_contract":{"provider":"gemini_tts","voice_name":"Charon"},
        }
        self._write()

    def _write(self):
        self.policy.write_text(json.dumps(self.p))
        self.record.write_text(json.dumps(self.r))

    def issue(self, *, receipt=True, master=True):
        return verify_drive_video_delivery(
            [self.master],
            production_record_path=self.record,
            audio_receipt_path=self.report if receipt else None,
            master_video_path=self.master if master else None,
            repo_root=self.root,
            policy_path=self.policy,
        )

    def _positive(self):
        from contextlib import ExitStack
        stack=ExitStack()
        self.addCleanup(stack.close)
        for target in (
            "production.audio_history_audit_v21.audit",
            "production.visual_rights_consistency_v21.validate_visual_rights_consistency",
            "production.scene_disclosures_v21.audit_repository",
            "production.rights_autonomy_v21.audit_repository",
        ):
            stack.enter_context(patch(target,return_value={"status":"PASS"}))
        stack.enter_context(patch("production.final_delivery_v21._probe_final_video",
                                  return_value={"width":1080,"height":1920,"fps":60,"duration_seconds":70}))
        stack.enter_context(patch("production.render_v21_manual.validate_completed_audio_mix",
                                  return_value={"status":"V21_AUDIO_POSTFLIGHT_EVIDENCE_PASS",
                                                "source_contributions_confirmed":["narration","music","sfx:test"]}))

    def test_positive_fixture_proves_final_gate_wiring_not_actual_release(self):
        self._positive()
        result=self.issue()
        self.assertEqual(result["status"],"PASS",result)
        self.assertTrue(result["release_ready"])
        self.assertEqual(result["remote_write"],"NOT_RUN")
        self.assertFalse(result["publication_authorized"])

    def test_disabled_live_policy_blocks_before_any_remote_write(self):
        self.p["production_enablement"]=False
        self.p["final_drive_delivery_enablement"]=False
        self._write()
        result=self.issue(receipt=False)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("policy production_enablement=false" in x for x in result["failures"]))
        self.assertTrue(any("final_drive_delivery_enablement" in x for x in result["failures"]))

    def test_current_repository_is_deliberately_blocked(self):
        root=Path(__file__).resolve().parents[1]
        original_policy=json.loads((root/"production/active_engine_policy.json").read_text())
        self.assertFalse(original_policy["production_enablement"])
        self.assertFalse(original_policy["final_drive_delivery_enablement"])
        result=verify_drive_video_delivery(
            [self.master],
            production_record_path=root/"episodes/episode-005/production-record.json",
            audio_receipt_path=None,
            master_video_path=self.master,
            repo_root=root,
        )
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(result["remote_write"],"NOT_RUN")

    def test_no_receipt_or_wrong_master_file_blocks(self):
        self._positive()
        self.assertEqual(self.issue(receipt=False)["status"],"BLOCKED")
        self.assertEqual(self.issue(master=False)["status"],"BLOCKED")
        other=self.root/"other.mp4"
        other.write_bytes(b"not the master")
        result=verify_drive_video_delivery(
            [other], production_record_path=self.record,
            audio_receipt_path=self.report,master_video_path=self.master,
            repo_root=self.root,policy_path=self.policy,
        )
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("exact verified master path" in x for x in result["failures"]))

    def test_fake_human_approval_cannot_enable_production(self):
        self.p["production_enablement"]=False
        self.r["render_authorization"]={"status":"APPROVED"}
        self._write()
        self._positive()
        self.assertEqual(self.issue()["status"],"BLOCKED")

    def test_scene_sfx_and_history_must_all_pass(self):
        self._positive()
        with patch("production.audio_history_audit_v21.audit",return_value={"status":"BLOCKED"}):
            result=self.issue()
        self.assertTrue(any("audio_history:" in x for x in result["failures"]))
        self.assertEqual(result["status"],"BLOCKED")
        with patch("production.scene_disclosures_v21.audit_repository",
                   return_value={"status":"BLOCKED"}):
            self.assertEqual(self.issue()["status"],"BLOCKED")

    def test_fake_postflight_and_missing_music_are_rejected(self):
        self._positive()
        with patch("production.render_v21_manual.validate_completed_audio_mix",
                   return_value={"status":"V21_AUDIO_POSTFLIGHT_BLOCKED"}):
            self.assertEqual(self.issue()["status"],"BLOCKED")
        with patch("production.render_v21_manual.validate_completed_audio_mix",
                   return_value={"status":"V21_AUDIO_POSTFLIGHT_EVIDENCE_PASS",
                                 "source_contributions_confirmed":["narration"]}):
            result=self.issue()
            self.assertTrue(any("narration or music" in x for x in result["failures"]))

    def test_invalid_mp4_probe_blocks(self):
        self._positive()
        with patch("production.final_delivery_v21._probe_final_video",side_effect=ValueError("bad 30 fps")):
            self.assertEqual(self.issue()["status"],"BLOCKED")

    def test_non_video_backup_is_not_blocked_by_final_master_gate(self):
        log=self.root/"evidence.json"
        log.write_text("{}")
        result=verify_drive_video_delivery([log],repo_root=self.root)
        self.assertEqual(result["status"],"NON_VIDEO_BACKUP_ONLY")
        self.assertFalse(result["publication_authorized"])

    def test_adapter_calls_guard_before_google_authentication(self):
        with patch("production.google_drive_delivery.service",
                   side_effect=AssertionError("external Drive network must not be attempted")):
            with self.assertRaisesRegex(DeliveryError,"Final V2.1 media delivery blocked"):
                deliver("fake-root","PRODUCOES","test",[self.master],"job-test",
                        production_record_path=self.record,repo_root=self.root,
                        master_video_path=self.master,policy_path=self.policy)

    def test_directory_scan_cannot_hide_video_by_naming_folder_backup(self):
        folder=self.root/"backup-reports"
        folder.mkdir()
        (folder/"innocent.json").write_text("{}")
        (folder/"master.mp4").write_bytes(b"fake media bytes")
        result=verify_drive_video_delivery([folder],repo_root=self.root)
        self.assertEqual(result["status"],"BLOCKED")


if __name__=="__main__":
    unittest.main()
