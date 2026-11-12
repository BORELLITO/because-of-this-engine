"""Canonical integration test for the Drive evidence sub-audit."""
import json
import tempfile
import unittest
from pathlib import Path

from production.canonical_entrypoint import evaluate


class CanonicalDriveEvidenceGateTests(unittest.TestCase):
    def test_drive_context_is_nested_and_non_promoting(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "episodes").mkdir()
            (root / "reports").mkdir()
            (root / "episodes" / "audio-rendered-master-registry.json").write_text(
                json.dumps(
                    {
                        "rendered_masters": [
                            {
                                "episode_id": "episode-001",
                                "master_video": {"sha256": "a" * 64},
                                "music_asset": {"drive_file_id": "canonical"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "reports" / "historical-receipt-recovery-v21.json").write_text(
                "{}", encoding="utf-8"
            )
            (root / "reports" / "drive-evidence-reconciliation-v21.json").write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {
                                "episode_id": "episode-001",
                                "manifest_status": "PRODUCTION_COMPLETE",
                                "qa_status": "VIDEO_RELEASE_VALIDATED",
                                "delivery_status": "DRIVE_VERIFIED",
                                "evidence_scope": "MANIFEST_CONTEXT_ONLY",
                                "strict_receipt_promotable": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = evaluate({}, registry=[], repo_root=root)
            audio = next(
                item for item in report["checks"]
                if item.get("gate") == "AUDIO_HISTORY_COVERAGE"
            )
            nested = audio["drive_evidence_reconciliation"]
            self.assertEqual(nested["status"], "BLOCKED")
            self.assertEqual(nested["promotion_status"], "BLOCKED")
            self.assertEqual(
                audio["drive_evidence_reconciliation_status"], "BLOCKED"
            )
            self.assertIn(
                "historical Drive evidence reconciliation is blocked",
                audio["failures"],
            )


if __name__ == "__main__":
    unittest.main()
