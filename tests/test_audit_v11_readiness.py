"""Tests cover blocking behavior only; no synthesis/render/Drive API access."""
import json
import tempfile
import unittest
from pathlib import Path
from audits.readiness_guard_v11 import inspect


class AuditV11ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "production").mkdir()
        (self.root / "production/canonical_config.py").write_text('CANONICAL_ENGINE_VERSION = "7.3.1"\n')
        self.policy = {
            "voice_provider": "gemini_tts",
            "active_engine_version": "7.3.1",
            "publication_policy": "manual_only",
            "render_contract": {"duration_min_seconds": 60, "duration_max_seconds": 75}
        }
        self.save()

    def save(self):
        (self.root / "production/active_engine_policy.json").write_text(json.dumps(self.policy))

    @staticmethod
    def codes(result):
        return {i["code"] for i in result["issues"]}

    def test_cloud_provider_conflict_blocks(self):
        result = inspect(self.root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("VOICE_PROVIDER_CONFLICT", self.codes(result))

    def test_no_automatic_publication(self):
        self.policy["publication_policy"] = "auto"
        self.save()
        self.assertIn("AUTOMATIC_PUBLICATION_RISK", self.codes(inspect(self.root)))

    def test_manifest_required_in_active_workflow(self):
        path = self.root / ".github/workflows/episode-004-final-release.yml"
        path.parent.mkdir(parents=True)
        path.write_text("on: workflow_dispatch\n")
        self.assertIn("FINAL_WORKFLOW_MANIFEST_NOT_IN_MAIN", self.codes(inspect(self.root)))

    def test_engine_version_drift(self):
        self.policy["active_engine_version"] = "7.4.0"
        self.save()
        self.assertIn("ENGINE_CONFIG_DRIFT", self.codes(inspect(self.root)))

    def test_new_clip_without_rights_and_fake_fingerprint(self):
        path = self.root / "new.json"
        path.write_text(json.dumps({
            "truth_mode": "DECLARED_FICTION", "lifecycle_status": "DRAFT",
            "scenes": [{"asset": {"sha256": "abc", "perceptual_hash": "abc"}}]
        }))
        found = self.codes(inspect(self.root, path))
        self.assertIn("CANDIDATE_RIGHTS_MISSING", found)
        self.assertIn("SUSPECT_PERCEPTUAL_FINGERPRINT", found)

    def test_new_story_must_not_be_preapproved(self):
        path = self.root / "new.json"
        path.write_text(json.dumps({"truth_mode": "VERIFIED_FACT", "lifecycle_status": "FINAL_APPROVED"}))
        found = self.codes(inspect(self.root, path))
        self.assertIn("NEW_STORY_TRUTH_MODE", found)
        self.assertIn("CANDIDATE_PREAPPROVED", found)

    def test_read_only_repeatable(self):
        p = self.root / "production/active_engine_policy.json"
        original = p.read_bytes()
        a = inspect(self.root)
        b = inspect(self.root)
        self.assertEqual(a, b)
        self.assertEqual(a["mode"], "READ_ONLY")
        self.assertEqual(p.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
