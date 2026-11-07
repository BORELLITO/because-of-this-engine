"""Versioned QA evidence tests: source review is NOT rendering authorization."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EP005S09AndRightsReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = json.loads((ROOT / "reports/EP005_S09_CANDIDATE_COMPARISON_20261107.json").read_text(encoding="utf-8"))
        cls.rights = json.loads((ROOT / "reports/EP005_SIX_ASSET_LICENSE_REVIEW_20261107.json").read_text(encoding="utf-8"))
        cls.plan = json.loads((ROOT / "episodes/episode-005/visual/asset-acquisition-plan.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "episodes/episode-005/visual/scene-asset-manifest.json").read_text(encoding="utf-8"))
        cls.record = json.loads((ROOT / "episodes/episode-005/production-record.json").read_text(encoding="utf-8"))

    def test_old_snapshot_and_new_manifest_approval_remain_distinct_from_render_rights(self):
        s = self.selection
        self.assertEqual(s["selection_decision"], "PREFERRED_CANDIDATE_PENDING_HUMAN_AND_REUSE_QA")
        self.assertFalse(s["render_allowed"])
        self.assertFalse(s["publication_allowed"])
        self.assertEqual(s["source_beats"]["existing_active_asset_id"], "pexels-12213087")
        self.assertTrue(any(x["candidate_id"] == "pexels-8888977" and x["rights_status"] == "APPROVED_FOR_MANIFEST_ONLY" for x in self.plan["candidates"]))
        self.assertTrue(any(x["candidate_id"] == "pexels-8888977" and x["approved_for_render"] is False for x in self.manifest["assets"]))
        self.assertTrue(any(x["asset_id"] == "pexels-8888977" and x["rights_status"] == "APPROVED" and x["approved_for_render"] is True and x["render_approval_status"] == "AUTO_APPROVED_EVIDENCE_BOUND_V21" for x in self.record["rights_ledger"]))

    def test_qa_only_source_hash_and_approvals_are_fail_closed(self):
        x = next(x for x in self.selection["history"] if x["asset_id"] == "pexels-8888977")
        self.assertTrue(re.fullmatch("[a-f0-9]{64}", x["sha256"]))
        self.assertEqual(x["source_resolution"], "4096x2160@25fps")
        self.assertEqual(x["evidence"]["qa_sample_count"], 5)
        self.assertEqual(x["evidence"]["drive_restoration"], "SHA256_MATCH_AND_ZIP_CRC_PASS")
        self.assertEqual(x["preview_qa"]["source_fps"], 25)
        self.assertEqual(x["preview_qa"]["output_fps"], 60)
        self.assertEqual(x["preview_qa"]["frame_rate_conversion"], "DUPLICATED_FRAMES_NOT_NATIVE_60")
        for field in ("approved_for_render","approved_for_manifest","global_catalog_updated","production_enablement"):
            self.assertIs(x["approval_state"][field], False, field)
        for field in ("human_visual","independent_render_rights","global_no_reuse_fingerprint"):
            self.assertEqual(x["approval_state"][field], "PENDING", field)

    def test_first_candidate_rejected_for_specific_visual_reason(self):
        history = {x["asset_id"]:x for x in self.selection["history"]}
        self.assertIn("vectorscope", history["pexels-6442793"]["technical_problem"])
        self.assertFalse(history["pexels-6442793"]["approved_for_render"])

    def test_six_license_records_do_not_grant_render_rights(self):
        self.assertEqual(self.rights["rights_reviewed_count"], 6)
        self.assertEqual(self.rights["source_metadata_consistent_count"], 6)
        self.assertEqual(self.rights["render_approved_count"], 0)
        self.assertFalse(self.rights["rights_promotion"])
        self.assertFalse(self.rights["active_rights_ledger_changed"])
        for asset in self.rights["assets"]:
            self.assertTrue(asset["source_manifest_byte_match"], asset["asset_id"])
            self.assertFalse(asset["approved_for_render"])
            self.assertFalse(asset["approval_inferred"])
            self.assertEqual(asset["specific_render_rights"], "PENDING_INDEPENDENT_RECONCILIATION")
            self.assertTrue(asset["official_terms_url"].startswith("https://"))

    def test_new_evidence_does_not_unblock_real_episode(self):
        from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
        result = validate_visual_rights_consistency(self.record, repo_root=ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(any("visual assets missing render rights" in x for x in result["failures"]))
        self.assertFalse(any("pexels-8888977: render rights not independently approved" in x for x in result["failures"]))
        self.assertFalse(any("nasa-svs-geos5-clouds-no-labels-4819: render rights not independently approved" in x for x in result["failures"]))
        self.assertFalse(any("nasa-svs-geos5-clouds-no-labels-4819" in x for x in result["failures"]))
        self.assertFalse(any("pexels-8888977: plan does not record human manifest approval" in x for x in result["failures"]))


if __name__ == "__main__":
    unittest.main()
