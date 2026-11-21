import json
import tempfile
import unittest
from pathlib import Path

from production.runflow import RunflowError, build_plan, load_request


class RunflowContractTests(unittest.TestCase):
    def make_repo(self, *, episode="episode-005"):
        root = Path(tempfile.mkdtemp(prefix="runflow-fixture-")) / "because-of-this-engine"
        (root / "episodes" / episode / "visual").mkdir(parents=True)
        (root / "episodes" / episode / "production-record.json").write_text(json.dumps({
            "episode_id": episode,
            "canonical_engine_version": 2.1,
        }))
        (root / "episodes" / episode / "story-architecture.json").write_text(json.dumps({}))
        (root / "episodes" / episode / "visual" / "scene-asset-manifest.json").write_text(json.dumps({}))
        return root

    def test_plan_is_ready_for_isolated_episode_package(self):
        root = self.make_repo()
        request = {"episode_id": "episode-005", "mode": "preview", "source_run_id": "123", "source_artifact_name": "checkpoint"}
        plan = build_plan(request, repo_root=root)
        self.assertEqual(plan["status"], "RUNFLOW_READY")
        self.assertTrue(plan["execution_policy"]["single_entrypoint"])
        self.assertFalse(plan["execution_policy"]["new_tts_call"])

    def test_foreign_project_is_rejected(self):
        root = self.make_repo()
        request = root / "request.json"
        request.write_text(json.dumps({
            "episode_id": "episode-005", "mode": "preview", "source_run_id": "123",
            "source_artifact_name": "verbo-no-chao-checkpoint",
        }))
        with self.assertRaises(RunflowError):
            load_request(request, repo_root=root)

    def test_bad_episode_id_is_rejected(self):
        root = self.make_repo()
        request = root / "request.json"
        request.write_text(json.dumps({
            "episode_id": "episode-5", "mode": "preview", "source_run_id": "123",
            "source_artifact_name": "checkpoint",
        }))
        with self.assertRaises(RunflowError):
            load_request(request, repo_root=root)


if __name__ == "__main__":
    unittest.main()
