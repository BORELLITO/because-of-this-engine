"""Tests for the fail-closed Drive evidence reconciliation."""
import unittest

from production.drive_evidence_reconciliation_v21 import build_reconciliation_report


def _registry():
    return {
        "rendered_masters": [
            {
                "episode_id": "episode-001",
                "master_video": {"sha256": "a" * 64},
                "music_asset": {"drive_file_id": "canonical-music"},
            }
        ]
    }


class DriveEvidenceReconciliationTests(unittest.TestCase):
    def test_production_complete_manifest_does_not_promote(self):
        report = build_reconciliation_report(
            _registry(),
            {
                "artifacts": [
                    {
                        "episode_id": "episode-001",
                        "manifest_drive_file_id": "manifest",
                        "manifest_status": "PRODUCTION_COMPLETE",
                        "qa_status": "VIDEO_RELEASE_VALIDATED",
                        "delivery_status": "DRIVE_VERIFIED",
                        "evidence_scope": "MANIFEST_CONTEXT_ONLY",
                        "strict_receipt_promotable": False,
                        "narration_sha256": "b" * 64,
                        "music_declaration": {"drive_file_id": "declared-music"},
                    }
                ]
            },
        )
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["promotion_status"], "BLOCKED")
        self.assertEqual(report["strict_receipt_count"], 0)
        row = report["rows"][0]
        self.assertEqual(row["promotion_status"], "BLOCKED")
        self.assertIn("no replayable strict_mix_receipt supplied", row["blocking_reasons"])
        self.assertIn("Drive manifest music declaration differs from canonical source ID", row["blocking_reasons"])

    def test_missing_artifact_is_explicitly_blocked(self):
        report = build_reconciliation_report(_registry(), {"artifacts": []})
        row = report["rows"][0]
        self.assertEqual(row["evidence_status"], "NOT_LOCATED")
        self.assertFalse(row["contextual_evidence_present"])
        self.assertFalse(row["strict_receipt_promotable"])
        self.assertEqual(row["promotion_status"], "BLOCKED")


    def test_explicit_not_located_artifact_is_not_contextual(self):
        report = build_reconciliation_report(
            _registry(),
            {
                "artifacts": [
                    {
                        "episode_id": "episode-001",
                        "evidence_status": "NOT_LOCATED",
                        "evidence_scope": "TARGETED_DRIVE_SEARCH_NO_MATCH",
                        "strict_receipt_promotable": False,
                    }
                ]
            },
        )
        row = report["rows"][0]
        self.assertEqual(row["evidence_status"], "NOT_LOCATED")
        self.assertFalse(row["contextual_evidence_present"])
        self.assertEqual(report["contextual_evidence_count"], 0)
        self.assertEqual(row["promotion_status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
