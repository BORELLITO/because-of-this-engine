"""Only-one-engine policy regression and workflow guard wiring."""
import json
import tempfile
import unittest
from pathlib import Path

from production import engine_singleton_guard as guard
from production.master_prompt_contract import MASTER_PROMPT_PATH, SCHEMA_PATH


class SingletonGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        prod = self.root / "production"
        prod.mkdir()
        canonical_root = Path(__file__).resolve().parents[1]

        prompt_path = self.root / MASTER_PROMPT_PATH
        prompt_path.parent.mkdir(parents=True)
        prompt_path.write_bytes((canonical_root / guard.MASTER_PROMPT_PATH).read_bytes())
        schema_path = self.root / SCHEMA_PATH
        schema_path.parent.mkdir(parents=True)
        schema_path.write_bytes((canonical_root / guard.SCHEMA_PATH).read_bytes())

        (prod / "active_engine_policy.json").write_text(json.dumps({
            "active_engine_profile": guard.CANONICAL_PROFILE_ID,
            "active_engine_fingerprint": guard.CANONICAL_PROFILE_FINGERPRINT,
            "update_rule": "approved_update_supersedes_previous_active_engine",
            "retired_versions": "must_not_remain_executable_in_active_tree",
            "master_prompt_version": guard.MASTER_PROMPT_VERSION,
            "master_prompt_sha256": guard.MASTER_PROMPT_SHA256,
            "production_schema": guard.SCHEMA_ID,
            "publication_policy": "manual_only",
        }), encoding="utf-8")
        (prod / "canonical_config.py").write_text(
            "CANONICAL_PROFILE_ID = 'active'\n"
            "CANONICAL_PROFILE_FINGERPRINT = 'fingerprint'\n", encoding="utf-8"
        )

    def test_single_current_profile_passes(self):
        self.assertEqual(guard.run(self.root), 0)

    def test_retired_executable_tree_is_blocked(self):
        legacy = self.root / "production" / "legacy"
        legacy.mkdir()
        (legacy / "runner.py").write_text("print('old')\n", encoding="utf-8")
        self.assertEqual(guard.run(self.root), 1)

    def test_policy_fingerprint_mismatch_is_blocked(self):
        policy_path = self.root / "production" / "active_engine_policy.json"
        policy = json.loads(policy_path.read_text())
        policy["active_engine_fingerprint"] = "outdated"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        self.assertEqual(guard.run(self.root), 1)

    def test_production_workflow_guards_are_wired(self):
        root = Path(__file__).resolve().parents[1]
        render = (root / ".github/workflows/render-video-episode.yml").read_text()
        ci = (root / ".github/workflows/video-engine-ci.yml").read_text()
        for marker in ("Require latest main revision at checkout",
                       "Recheck latest main revision before render",
                       "Block stale revision before Drive delivery",
                       "engine_singleton_guard.py",
                       "manifest_readiness.py"):
            self.assertIn(marker, render)
        for marker in ("engine_singleton_guard.py",
                       "manifest_readiness.py",
                       "unittest discover"):
            self.assertIn(marker, ci)
