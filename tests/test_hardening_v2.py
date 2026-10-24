import json
import tempfile
import unittest
from pathlib import Path

from production.pipeline_state import PipelineStateError, load_or_initialize, transition


class PipelineStateTests(unittest.TestCase):
    def _manifest(self, root: Path) -> Path:
        path = root / "manifest.json"
        path.write_text(json.dumps({
            "schema_version": "2.0",
            "video_id": "state-test-001",
            "job_id": "state-test-001",
        }), encoding="utf-8")
        return path

    def test_job_state_is_stable_and_transitions_are_ordered(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            first = load_or_initialize(manifest)
            second = load_or_initialize(manifest)
            self.assertEqual(first["job_id"], second["job_id"])
            self.assertEqual(first["state"], "CREATED")
            transition(manifest, "ASSETS_APPROVED", "assets")
            transition(manifest, "TIMELINE_READY", "timeline")
            state = transition(manifest, "RENDERED", "render")
            self.assertEqual(state["state"], "RENDERED")

    def test_invalid_transition_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            with self.assertRaises(PipelineStateError):
                transition(manifest, "COMPLETE", "complete")

    def test_manifest_change_cannot_reuse_existing_job_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._manifest(root)
            load_or_initialize(manifest)
            manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(PipelineStateError):
                load_or_initialize(manifest)


class V2HardLockTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_workflow_has_no_literal_shell_or_secret_escapes(self):
        workflow = (self.ROOT / ".github" / "workflows" / "render-video-episode.yml").read_text(encoding="utf-8")
        self.assertNotIn(r"\${", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)
        self.assertIn("--require-drive-assets", workflow)
        self.assertIn("--job-id", workflow)
        self.assertIn("finalize_manifest.py", workflow)

    def test_old_engine_paths_are_not_reintroduced(self):
        paths = [path.relative_to(self.ROOT).as_posix() for path in self.ROOT.rglob("*") if path.is_file()]
        forbidden = ("mar" + "s-", "author" + "ial", "image_" + "provider", "render_" + "author" + "ial", "stock_" + "video_research")
        offenders = [path for path in paths if any(token in path.lower() for token in forbidden)]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
