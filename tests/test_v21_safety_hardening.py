"""Regression tests for destructive cleanup, singleton provider and evidence gates.

Tests do NOT contact cloud providers, synthesize speech, render media or upload files.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from production.v21_singleton_guard import audit


class V21SafetyHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "production").mkdir()
        self.workflows = self.root / ".github" / "workflows"
        self.workflows.mkdir(parents=True)
        (self.workflows / "v21-integration-readonly.yml").write_text(
            "name: canonical integration\n", encoding="utf-8"
        )
        (self.root / "production" / "active_engine_policy.json").write_text(
            json.dumps({
                "active_engine_version": "2.1",
                "canonical_entrypoint": "production/canonical_entrypoint.py",
                "production_enablement": False,
                "soundtrack_policy_v21": {
                    "status": "ENFORCED_ENGINE_SELECTS_VETTED_MUSIC",
                    "selector": "production/music_autoselect_v21.py",
                    "music_required_in_every_final": True,
                    "music_to_last_frame": True,
                    "music_gain_max": 0.12,
                    "music_fade_out_seconds": 1.2,
                    "narration_ducking": "SIDECHAIN_COMPRESSOR_V21",
                    "no_clear_music_action": "FAIL_CLOSED_NO_SILENT_SUBSTITUTE",
                },
                "final_render_entrypoint": "production/render_v21_final.py",
                "final_render_route": {
                    "status": "IMPLEMENTED_FAIL_CLOSED_NO_PRODUCTION_AUTHORIZATION",
                    "generate_new_TTS": False,
                    "publication": "manual_only",
                },
                "final_drive_delivery_enablement": False,
                "final_delivery_audio_gate": {
                    "adapter": "production/final_delivery_v21.py",
                    "drive_adapter": "production/google_drive_delivery.py",
                    "receipt_required": True
                },
                "legacy_policy": {"status": "legacy_rollback_only"},
            }), encoding="utf-8"
        )

        (self.root / "production" / "render_v21_final.py").write_text(
            'validate_request(record, repo_root=repo_root, mode="final")\n'
            'validate_completed_audio_mix(\n'
            'build_audio_mix_command(\n'
            'select_for_story(\n'
            'sidechaincompress=\n'
            'afade=t=out\n',
            encoding="utf-8",
        )
        (self.root / "production" / "music_autoselect_v21.py").write_text(
            "# isolated soundtrack selector fixture\n",encoding="utf-8"
        )
        (self.root / "production" / "final_delivery_v21.py").write_text(
            "# test fixture: final-drive delivery proof boundary\n", encoding="utf-8")
        (self.root / "production" / "google_drive_delivery.py").write_text(
            'verify_drive_video_delivery(\nif final_gate["status"] == "BLOCKED":\n',
            encoding="utf-8",
        )

    def test_active_gemini_charon_workflow_is_allowed(self):
        (self.workflows / "episode006-gemini-charon.yml").write_text(
            "name: Charon\nrun: python -m production.gemini_tts\n",
            encoding="utf-8",
        )
        self.assertEqual(audit(self.root)["status"], "V21_SINGLETON_PASS")

    def test_old_edge_workflow_name_is_rejected(self):
        (self.workflows / "edge-tts-episode005-preview.yml").write_text(
            "name: Retired voice\n", encoding="utf-8"
        )
        result = audit(self.root)
        self.assertEqual(result["status"], "V21_SINGLETON_BLOCKED")
        self.assertTrue(any("retired provider workflow" in f for f in result["failures"]))

    def test_legacy_runtime_command_is_rejected(self):
        (self.workflows / "manual-legacy.yml").write_text(
            "run: python production/microsoft_edge_tts.py\n", encoding="utf-8"
        )
        result = audit(self.root)
        self.assertEqual(result["status"], "V21_SINGLETON_BLOCKED")

    def test_candidate_cannot_enable_production(self):
        policy_path = self.root / "production" / "active_engine_policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["production_enablement"] = True
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        self.assertEqual(audit(self.root)["status"], "V21_SINGLETON_BLOCKED")

    def test_housekeeping_does_not_delete_any_artefact_or_run(self):
        path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "github-housekeeping.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("READ ONLY", text)
        self.assertIn("actions: read", text)
        for method in ("deleteArtifact(", "deleteWorkflowRun(", "DELETE /repos/"):
            self.assertNotIn(method, text)

    def test_legacy_edge_workflow_is_archived_outside_actions(self):
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / ".github" / "workflows" / "edge-tts-episode005-preview.yml").exists())
        self.assertTrue((root / "archive" / "v21" / "workflows" / "edge-tts-episode005-preview.yml").exists())


if __name__ == "__main__":
    unittest.main()
