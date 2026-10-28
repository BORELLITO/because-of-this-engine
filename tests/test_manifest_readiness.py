"""Old episodes must not acquire synthetic approval metadata."""
import unittest
from production.manifest_readiness import audit, PIXEL_QC_REQUIREMENTS
from production.asset_preflight import EXPECTED_PIXEL_QC


def approved_asset():
    return {
        "asset_class": "evidence",
        "scene_approval": "APPROVED",
        "visual_evidence": {"pixel_qc": dict(PIXEL_QC_REQUIREMENTS)},
    }


class ManifestReadinessTest(unittest.TestCase):
    def manifest(self, asset=None, lifecycle="DRAFT_AUDIO_PENDING", editorial="PENDING"):
        return {
            "video_id": "test-episode",
            "lifecycle_status": lifecycle,
            "scenes": [{"scene_id": "S01", "asset": asset if asset is not None else approved_asset()}],
            "editorial_qa": {"status": editorial, "reviewer": "reviewer",
                             "reviewed_at": "2026-10-28T00:00:00Z"},
        }

    def test_readiness_contract_matches_visual_preflight(self):
        self.assertEqual(PIXEL_QC_REQUIREMENTS, EXPECTED_PIXEL_QC)

    def test_approved_scene_allows_preview_but_not_unapproved_final(self):
        m = self.manifest()
        self.assertEqual(audit(m, "preview")["status"], "PASS")
        self.assertEqual(audit(m, "final")["status"], "BLOCKED")
        m["editorial_qa"]["status"] = "PASS"
        self.assertEqual(audit(m, "final")["status"], "PASS")

    def test_archived_episode_is_blocked(self):
        self.assertEqual(audit(self.manifest(lifecycle="ARCHIVED_HISTORICAL"),
                               "preview")["status"], "BLOCKED")

    def test_legacy_missing_approval_is_reported_not_invented(self):
        old = {"visual_evidence": {"reviewed": True},
               "approved_for_render": True}
        m = self.manifest(asset=old)
        result = audit(m, "preview")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertGreaterEqual(len(result["errors"]), 4)
        self.assertNotIn("asset_class", m["scenes"][0]["asset"])
        self.assertNotIn("scene_approval", m["scenes"][0]["asset"])

    def test_wrong_clean_frame_data_is_rejected(self):
        a = approved_asset()
        a["visual_evidence"]["pixel_qc"]["external_branding"] = "PRESENT"
        self.assertEqual(audit(self.manifest(asset=a), "preview")["status"],
                         "BLOCKED")

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.manifest(), "legacy")
