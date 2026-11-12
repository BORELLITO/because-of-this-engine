"""Canonical wiring test for persisted EP005 artifacts."""
import json
import tempfile
import unittest
from pathlib import Path

from production.canonical_entrypoint import evaluate


class CanonicalArtifactReconciliationTests(unittest.TestCase):
    def test_canonical_entrypoint_attaches_artifact_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            episode = root / "episodes" / "episode-005"
            episode.mkdir(parents=True)
            (episode / "story-architecture.json").write_text(
                json.dumps(
                    {
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
                ),
                encoding="utf-8",
            )
            manifest = {
                "episode_id": "episode-005",
                "production_enablement": False,
                "video_title": "THE SIGNAL THAT COULD HAVE STARTED WORLD WAR III",
                "display_name": "05 - THE SIGNAL THAT COULD HAVE STARTED WORLD WAR III",
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
            report = evaluate(manifest, registry=[], repo_root=root)
            gate = next(
                check for check in report["checks"]
                if check.get("gate") == "EP005_ARTIFACT_RECONCILIATION"
            )
            self.assertEqual(gate["status"], "PASS")
            self.assertFalse(gate["release_authorized"])


if __name__ == "__main__":
    unittest.main()
