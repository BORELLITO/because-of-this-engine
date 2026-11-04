"""Regression tests for non-destructive remote-Git source-history inventory."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from audits.branch_history_audit_v11 import audit, GitHistoryAuditError


class BranchHistoryV11Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "audit@localhost.invalid")
        self.git("config", "user.name", "Offline Test")
        self.episode = self.root / "episodes" / "video-001"
        self.episode.mkdir(parents=True)
        self.manifest = self.episode / "manifest.json"

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True,
        ).stdout.decode().strip()

    def commit(self, *, source, lifecycle="FINAL_APPROVED", video_id="episode-001"):
        self.manifest.write_text(json.dumps({
            "video_id": video_id, "lifecycle_status": lifecycle,
            "scenes": [{"scene_id": "S01", "asset": {
                "provider": "pexels", "provider_asset_id": source,
                "source_page_url": f"https://www.pexels.com/video/{source}/",
            }}],
        }), encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", f"offline source {source}")
        return self.git("rev-parse", "HEAD")

    def test_older_branch_contains_unseen_source_and_does_not_retire_draft(self):
        old = self.commit(source="111", lifecycle="DRAFT_PREVIEW_ONLY")
        new = self.commit(source="222", lifecycle="FINAL_APPROVED")
        self.git("update-ref", "refs/remotes/origin/old-draft", old)
        self.git("update-ref", "refs/remotes/origin/main", new)
        report = audit(self.root)
        self.assertEqual(report["status"], "HISTORY_METADATA_PARTIAL")
        self.assertEqual(report["branch_ref_count"], 2)
        self.assertEqual(report["local_source_key_count"], 1)
        self.assertEqual(report["git_history_unique_source_key_count"], 2)
        self.assertEqual(report["historical_sources_not_in_current_tree"], 1)
        self.assertEqual(report["historical_extra_by_lifecycle"]["draft_or_other_only"], 1)
        self.assertFalse(report["automatic_draft_retirement"])
        self.assertFalse(report["approval_to_use_in_new_video"])

    def test_finalized_old_branch_is_separately_classified(self):
        old = self.commit(source="111", lifecycle="FINAL_APPROVED")
        new = self.commit(source="222", lifecycle="FINAL_APPROVED")
        self.git("update-ref", "refs/remotes/origin/historical", old)
        self.git("update-ref", "refs/remotes/origin/main", new)
        report = audit(self.root)
        self.assertEqual(report["historical_extra_by_lifecycle"]["final_approved"], 1)
        self.assertEqual(report["malformed_snapshot_count"], 0)

    def test_without_remote_refs_fails_closed(self):
        self.commit(source="111")
        with self.assertRaises(GitHistoryAuditError):
            audit(self.root)


if __name__ == "__main__":
    unittest.main()
