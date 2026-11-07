"""Regression of exact V2.1 plan/manifest/render rights equivalence.

Test fixtures use synthetic approvals ONLY in temporary files. Real production
records are never rewritten, rendered, posted or granted rights by this suite.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
from production.render_v21_manual import validate_request

ROOT = Path(__file__).resolve().parents[1]
EPISODE = "episode-test"
ID = "fixture-shot-one"
HASH = "a" * 64
PERCEPTUAL = "fixture-phash-a1"
SOURCE = "https://example.test/clip"


class V21VisualRightsConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan_path = "episodes/episode-test/visual/asset-acquisition-plan.json"
        self.manifest_path = "episodes/episode-test/visual/scene-asset-manifest.json"
        self.plan = {
            "episode_id": EPISODE,
            "candidates": [{
                "candidate_id": ID,
                "source_page_url": SOURCE,
                "license_name": "Free Commercial Test",
                "rights_status": "APPROVED_FOR_MANIFEST_ONLY",
                "qa": {"human_approval": "APPROVED_FOR_MANIFEST"},
                "intake_artifact": {"sha256": HASH, "perceptual_hash": PERCEPTUAL},
            }],
        }
        self.scene = {
            "episode_id": EPISODE, "source_plan": self.plan_path,
            "assets": [{
                "candidate_id": ID, "source_page_url": SOURCE,
                "license_name": "Free Commercial Test",
                "sha256": HASH, "perceptual_hash": PERCEPTUAL,
                "rights_status": "APPROVED_FOR_MANIFEST_ONLY",
                "human_approval": "APPROVED_FOR_MANIFEST",
                "approved_for_render": False,
            }],
            "shot_assignments": [{"shot_id": "S01", "assignment": {"candidate_id": ID}}],
        }
        self.record = {
            "episode_id": EPISODE,
            "visual_manifest_reference": self.manifest_path,
            "render_authorization": {"status": "APPROVED"},
            "rights_ledger": [{
                "asset_id": ID, "source_url": SOURCE,
                "sha256": HASH, "perceptual_fingerprint": PERCEPTUAL,
                "license_name": "Free Commercial Test",
                "rights_status": "APPROVED", "approved_for_render": True,
                "approval_scope": "episode-test-render",
                "used_by": [EPISODE],
            }],
        }
        self._save()

    def _save(self):
        for relative, data in ((self.plan_path, self.plan), (self.manifest_path, self.scene)):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data), encoding="utf-8")

    def _check(self):
        self._save()
        return validate_visual_rights_consistency(self.record, repo_root=self.root)

    def test_matching_synthetic_records_pass_without_authorizing_media(self):
        result = self._check()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["render"], "NOT_RUN")
        self.assertEqual(result["publication"], "NOT_RUN")

    def test_missing_rights_blocks_even_if_other_rights_claim_approved(self):
        self.record["rights_ledger"][0]["asset_id"] = "former-asset"
        result = self._check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("missing render rights" in e for e in result["failures"]))
        self.assertTrue(any("inactive visual assets" in e for e in result["failures"]))

    def test_plan_approval_cannot_be_inferred_from_manifest(self):
        self.plan["candidates"][0]["qa"]["human_approval"] = "PENDING"
        result = self._check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("human manifest approval" in e for e in result["failures"]))

    def test_rights_hash_mismatch_blocks(self):
        self.record["rights_ledger"][0]["sha256"] = "f" * 64
        result = self._check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("render rights SHA-256 mismatch" in e for e in result["failures"]))

    def test_perceptual_hash_mismatch_blocks(self):
        self.scene["assets"][0]["perceptual_hash"] = "pending"
        result = self._check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("manifest perceptual identity" in e for e in result["failures"]))

    def test_approval_scope_must_match_episode(self):
        self.record["rights_ledger"][0]["approval_scope"] = "episode-other-render"
        result = self._check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("incorrect render approval scope" in e for e in result["failures"]))

    def test_path_escape_is_rejected(self):
        self.record["visual_manifest_reference"] = "../../other-project/manifest.json"
        result = self._check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("escapes repository" in e for e in result["failures"]))

    def test_real_episode_005_is_blocked_and_unmodified(self):
        production = json.loads((ROOT / "episodes/episode-005/production-record.json").read_text())
        before = copy.deepcopy(production)
        result = validate_visual_rights_consistency(production, repo_root=ROOT)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(production, before)
        self.assertFalse(any("visual assets missing render rights:" in e for e in result["failures"]))
        self.assertFalse(any("pexels-8888977: render rights not independently approved" in e for e in result["failures"]))
        self.assertTrue(any("nasa-svs-geos5-clouds-no-labels-4819: render rights not independently approved" in e for e in result["failures"]))
        self.assertTrue(any("pexels-8888977" in e for e in result["failures"]))
        self.assertFalse(any("pexels-8888977: plan does not record human manifest approval" in e for e in result["failures"]))

    def test_manual_preview_can_pass_only_with_matching_evidence(self):
        self.record["preview_enablement"] = True
        self.record["production_enablement"] = False
        self.record["render_contract"] = {"width": 1080, "height": 1920, "fps": 60, "render_executed": False}
        self.record["thumbnail_manifest"] = {
            "episode_id": EPISODE,
            "story_id": "fixture-story", "incident_id": "fixture-incident",
            "title_variant": "TEST", "thumbnail_text": "TEST", "hero_asset_id": ID,
            "visual_truth_class": "MAP_OR_DIAGRAM", "source_url": SOURCE,
            "rights_status": "APPROVED", "sha256": HASH,
            "dimensions": [1080, 1920], "safe_margin_status": "PASS",
            "mobile_legibility_status": "PASS", "human_review_status": "APPROVED",
            "youtube_thumbnail_mode": "custom_if_supported",
            "tiktok_cover_mode": "approved_video_frame",
            "final_status": "APPROVED",
            "delivery_paths": {
                "thumbnail_master_9x16_png": "synthetic.png",
                "thumbnail_master_9x16_jpg": "synthetic.jpg",
                "thumbnail_source_frame": "synthetic-source.png",
                "thumbnail_preview_mobile": "synthetic-mobile.png",
                "platform_cover_record": "synthetic.json",
            },
        }
        self._save()
        policy = self.root / "test-policy.json"
        policy.write_text(json.dumps({
            "active_engine_version": "2.1",
            "canonical_entrypoint": "production/canonical_entrypoint.py",
            "manual_render_entrypoint": "production/render_v21_manual.py",
            "publication_policy": "manual_only",
            "preview_enablement": True,
            "production_enablement": False,
        }), encoding="utf-8")
        result = validate_request(self.record, repo_root=self.root, mode="preview", policy_path=policy)
        self.assertEqual(result["status"], "V21_MANUAL_RENDER_PREFLIGHT_PASS", result)
        self.assertEqual(result["render"], "NOT_RUN")
        self.assertEqual(result["publication"], "MANUAL_ONLY_NOT_RUN")


if __name__ == "__main__":
    unittest.main()
