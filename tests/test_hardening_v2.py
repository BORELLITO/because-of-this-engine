import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.finalize_manifest import finalize
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
        self.assertNotIn("actions/upload-" + "artifact", workflow)
        self.assertIn("--require-drive-assets", workflow)
        self.assertIn("--job-id", workflow)
        self.assertIn("finalize_manifest.py", workflow)
        self.assertIn("narrate.py", workflow)
        self.assertIn("GEMINI_API_KEY", workflow)
        self.assertIn("generate_phrase_captions.py", workflow)
        self.assertIn("canonical_config.py", workflow)
        self.assertIn("enforce_canonical=True", (self.ROOT / "production" / "render_video_episode.py").read_text(encoding="utf-8"))
        self.assertIn("engine_profile", (self.ROOT / "production" / "pipeline_state.py").read_text(encoding="utf-8"))
        render = (self.ROOT / "production" / "render_video_episode.py").read_text(encoding="utf-8")
        self.assertNotIn("_bounded_weighted_allocation", render)
        self.assertNotIn("write_brand_ass", render)
        self.assertNotIn("allow_legacy", render)
        self.assertIn("requirements.lock.txt", workflow)
        self.assertIn("Historical archived manifests", workflow)



    def test_old_engine_paths_are_not_reintroduced(self):
        paths = [path.relative_to(self.ROOT).as_posix() for path in self.ROOT.rglob("*") if path.is_file()]
        forbidden = ("mar" + "s-", "author" + "ial", "image_" + "provider", "render_" + "author" + "ial", "stock_" + "video_research")
        offenders = [path for path in paths if any(token in path.lower() for token in forbidden)]
        self.assertEqual(offenders, [])

    def test_workflows_pin_external_actions_by_commit(self):
        workflow_dir = self.ROOT / ".github" / "workflows"
        refs = {
            "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
            "actions/github-script": "f28e40c7f34bde8b3046d885e986cb6290c5673b",
        }
        for workflow in workflow_dir.glob("*.yml"):
            content = workflow.read_text(encoding="utf-8")
            for action, commit in refs.items():
                if action in content:
                    self.assertIn(f"{action}@{commit}", content)

    def test_final_manifest_hashes_nested_asset_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rendered").mkdir()
            (root / "audio").mkdir()
            (root / "captions").mkdir()
            for relative in (
                "script.txt",
                "audio/narration.wav",
                "captions/narration.ass",
                "captions/narration.alignment.json",
                "rendered/hash-test-001-preview.mp4",
            ):
                path = root / relative
                path.write_bytes(b"test")
            manifest = {
                "schema_version": "2.0",
                "video_id": "hash-test-001",
                "job_id": "hash-test-001",
                "output": {"path": "rendered/{video_id}-{mode}.mp4"},
                "script": {"path": "script.txt"},
                "audio": {"path": "audio/narration.wav"},
                "captions": {
                    "path": "captions/narration.ass",
                    "alignment_sidecar": "captions/narration.alignment.json",
                    "alignment_mode": "forced_alignment",
                    "alignment_source": "test",
                    "word_level_available": True,
                },
                "scenes": [{
                    "scene_id": "S01",
                    "duration": 1,
                    "asset": {"asset_id": "asset-001", "sha256": "asset-hash-001"},
                    "visual_match": "EXACT",
                    "visual_truth": "DECLARED_FICTION",
                }],
            }
            (root / "manifest.json").write_bytes(b"manifest")
            (root / "release.json").write_text(json.dumps({"status": "VIDEO_RELEASE_VALIDATED"}), encoding="utf-8")
            (root / "delivery.json").write_text(json.dumps({"status": "DRIVE_VERIFIED"}), encoding="utf-8")
            with patch("production.finalize_manifest.load_manifest", return_value=manifest):
                result = finalize(
                    root / "manifest.json",
                    root / "release.json",
                    root / "delivery.json",
                    "preview",
                )
            self.assertEqual(result["status"], "FINAL_MANIFEST_WRITTEN")
            payload = json.loads((root / "rendered" / "final-manifest-hash-test-001-preview.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["fingerprints"]["footage_sha256"], "0515b3da9dcde5c270e0386efc69ee94f234164ef19f646e750ad56394682546")

    def test_hud_and_stream_duration_are_hard_locked(self):
        render = (self.ROOT / "production" / "render_video_episode.py").read_text(encoding="utf-8")
        release = (self.ROOT / "production" / "validate_video_release.py").read_text(encoding="utf-8")
        contract = (self.ROOT / "production" / "video_asset_contract.py").read_text(encoding="utf-8")
        self.assertIn('logo_anchor = str(brand.get("logo_anchor", "center_top"))', render)
        self.assertIn("x=(main_w-overlay_w)/2:y=", render)
        self.assertIn(",8,40,40,110,1", render)
        self.assertIn("tpad=stop_mode=clone", render)
        self.assertIn("Assembled video clock drifted", render)
        self.assertIn('"video_duration": video_duration', contract)
        self.assertIn("Video stream duration", release)
        self.assertIn("stream_duration_delta_seconds", release)

    def test_direct_production_scripts_bootstrap_repository_root(self):
        expected = "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))"
        for filename in (
            "production/google_drive_assets.py",
            "production/render_video_episode.py",
            "production/validate_video_release.py",
            "production/finalize_manifest.py",
            "production/quality_gates.py",
        ):
            content = (self.ROOT / filename).read_text(encoding="utf-8")
            self.assertIn(expected, content, filename)


if __name__ == "__main__":
    unittest.main()
