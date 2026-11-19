"""Regression: canonical V2.1 fails closed when Drive evidence lacks its historical inventory.

These tests must not synthesize audio, render media, write Drive, or publish.
"""
import json
import tempfile
import unittest
from pathlib import Path

from production.canonical_entrypoint import evaluate


class CanonicalMissingEvidenceRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "episodes").mkdir()
        (self.root / "reports").mkdir()
        self.registry = self.root / "episodes" / "audio-rendered-master-registry.json"
        self.recovery_report = self.root / "reports" / "historical-receipt-recovery-v21.json"
        (self.root / "reports" / "drive-evidence-reconciliation-v21.json").write_text(
            json.dumps({"artifacts": []}), encoding="utf-8"
        )

    def _assert_blocked_not_crashed(self):
        result = evaluate({}, registry=[], repo_root=self.root)
        audio = next(
            check for check in result["checks"]
            if check.get("gate") == "AUDIO_HISTORY_COVERAGE"
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["production_enablement"], False)
        self.assertEqual(result["tts"], "NOT_RUN")
        self.assertEqual(result["render"], "NOT_RUN")
        self.assertEqual(result["publication"], "MANUAL_ONLY_NOT_RUN")
        self.assertEqual(audio["drive_evidence_reconciliation_status"], "BLOCKED")
        self.assertIn(
            "historical Drive evidence reconciliation is blocked", audio["failures"]
        )

    def test_missing_both_recovery_files_fails_closed(self):
        self._assert_blocked_not_crashed()

    def test_registry_present_but_recovery_report_missing_fails_closed(self):
        self.registry.write_text(json.dumps({"rendered_masters": []}), encoding="utf-8")
        self._assert_blocked_not_crashed()

    def test_corrupt_registry_fails_closed(self):
        self.registry.write_text("{invalid", encoding="utf-8")
        self.recovery_report.write_text("{}", encoding="utf-8")
        self._assert_blocked_not_crashed()

    def test_non_object_registry_fails_closed(self):
        self.registry.write_text("[]", encoding="utf-8")
        self.recovery_report.write_text("{}", encoding="utf-8")
        self._assert_blocked_not_crashed()


if __name__ == "__main__":
    unittest.main()
