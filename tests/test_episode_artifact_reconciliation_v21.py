"""Tests for EP005 persisted TTS/caption artifact reconciliation."""
import unittest

from production.episode_artifact_reconciliation_v21 import reconcile_artifacts


class EpisodeArtifactReconciliationTests(unittest.TestCase):
    def _record(self):
        return {
            "episode_id": "episode-005",
            "production_enablement": False,
            "narration_artifact_evidence": {
                "status": "VERIFIED_GITHUB_ACTIONS_ARTIFACT",
                "artifact_name": "episode005-gemini-charon-narration",
                "workflow_run_id": 42278191077,
                "audio_sha256": "a" * 64,
                "duration_seconds": 73.84,
            },
            "caption_artifact_evidence": {
                "status": "VERIFIED_GITHUB_ACTIONS_ARTIFACT",
                "artifact_name": "episode005-gemini-charon-captioned",
                "workflow_run_id": 42278428885,
            },
        }

    def _architecture(self):
        return {
            "narration": {
                "execution_status": "GEMINI_CHARON_NARRATION_READY",
                "latest_attempt": {
                    "artifact": "episode005-gemini-charon-narration",
                    "workflow_run_id": 42278191077,
                    "audio_sha256": "a" * 64,
                    "duration_seconds": 73.84,
                },
                "captions": {
                    "artifact": "episode005-gemini-charon-captioned",
                    "workflow_run_id": 42278428885,
                },
            }
        }

    def test_matching_artifacts_reconcile_without_release(self):
        result = reconcile_artifacts(self._record(), self._architecture())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["narration_artifact_verified"])
        self.assertTrue(result["captions_artifact_verified"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["final_mix_bound"])

    def test_missing_record_evidence_blocks_reconciliation(self):
        record = self._record()
        del record["narration_artifact_evidence"]
        result = reconcile_artifacts(record, self._architecture())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["release_authorized"])
        self.assertIn("production record narration_artifact_evidence is missing", result["failures"])

    def test_no_artifact_claim_is_non_applicable(self):
        result = reconcile_artifacts({"episode_id": "episode-006"}, {})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "NOT_APPLICABLE_NO_PERSISTED_ARTIFACT_CLAIM")


if __name__ == "__main__":
    unittest.main()
