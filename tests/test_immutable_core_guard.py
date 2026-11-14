from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from production.immutable_core_guard import audit, validate_episode_surface_lock

ROOT = Path(__file__).resolve().parents[1]


class ImmutableCoreGuardTests(unittest.TestCase):
    def test_current_repository_passes(self):
        report = audit(ROOT)
        self.assertEqual(report["status"], "IMMUTABLE_CORE_PASS", report)

    def test_authority_drift_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                "production/immutable_core_policy_v1.json",
                "production/active_engine_policy.json",
                "production/active_surface_lock_v21.py",
                "production/caption_policy_v21.json",
                "production/render_v21_preview.py",
                "production/render_v21_final.py",
                "docs/CANONICAL_VISUAL_EDITORIAL_LOCK_20261112.md",
                "docs/QUALITY_SAFETY_HARDENING_20261107.md",
            ):
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

            caption_path = root / "production/caption_policy_v21.json"
            caption = json.loads(caption_path.read_text(encoding="utf-8"))
            caption["layout"]["margin_v"] = 999
            caption_path.write_text(json.dumps(caption), encoding="utf-8")

            report = audit(root)
            self.assertEqual(report["status"], "IMMUTABLE_CORE_BLOCKED")
            self.assertTrue(any("authority file drift" in item for item in report["failures"]))

    def test_episode_surface_lock_blocks_clip_change(self):
        manifest = {
            "episode_id": "episode-001",
            "shot_assignments": [
                {"shot_id": "S01", "assignment": {"candidate_id": "clip-a", "sha256": "aaa"}}
            ],
        }
        lock = {
            "episode_id": "episode-001",
            "status": "APPROVED_LOCKED",
            "approved_by": "Borelli",
            "approved_at": "2026-11-14T00:00:00-03:00",
            "shot_assignments": [
                {"shot_id": "S01", "candidate_id": "clip-b", "sha256": "bbb"}
            ],
            "branding": {"logo_y": 190, "logo_width": 360},
            "captions": {"margin_v": 650},
        }
        report = validate_episode_surface_lock(manifest, lock)
        self.assertEqual(report["status"], "EPISODE_SURFACE_LOCK_BLOCKED")
        self.assertTrue(any("clip assignments" in item for item in report["failures"]))

    def test_episode_surface_lock_accepts_exact_surface(self):
        manifest = {
            "episode_id": "episode-001",
            "shot_assignments": [
                {"shot_id": "S01", "assignment": {"candidate_id": "clip-a", "sha256": "aaa"}}
            ],
        }
        lock = {
            "episode_id": "episode-001",
            "status": "APPROVED_LOCKED",
            "approved_by": "Borelli",
            "approved_at": "2026-11-14T00:00:00-03:00",
            "shot_assignments": [
                {"shot_id": "S01", "candidate_id": "clip-a", "sha256": "aaa"}
            ],
            "branding": {"logo_y": 190, "logo_width": 360},
            "captions": {"margin_v": 650},
        }
        report = validate_episode_surface_lock(manifest, lock)
        self.assertEqual(report["status"], "EPISODE_SURFACE_LOCK_PASS", report)


if __name__ == "__main__":
    unittest.main()
