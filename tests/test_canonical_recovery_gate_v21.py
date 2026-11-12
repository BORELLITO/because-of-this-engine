"""Integration tests for the canonical historical-recovery gate."""
import json
import tempfile
import unittest
from pathlib import Path

from production.canonical_entrypoint import evaluate


class CanonicalRecoveryGateTests(unittest.TestCase):
    def test_canonical_inventory_report_enables_recovery_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "episodes").mkdir()
            (root / "reports").mkdir()
            (root / "episodes" / "audio-rendered-master-registry.json").write_text(
                json.dumps({"rendered_masters": []}), encoding="utf-8"
            )
            (root / "reports" / "historical-receipt-recovery-v21.json").write_text(
                "{}", encoding="utf-8"
            )
            report = evaluate({}, registry=[], repo_root=root)
            audio = next(item for item in report["checks"] if item.get("gate") == "AUDIO_HISTORY_COVERAGE")
            self.assertEqual(audio["historical_receipt_recovery_status"], "BLOCKED")
            self.assertEqual(audio["historical_receipt_recovery"]["gate"], "AUDIO_HISTORY_RECEIPT_RECOVERY")
            self.assertIn("historical receipt recovery gate is blocked", audio["failures"])

    def test_legacy_or_synthetic_root_does_not_enable_new_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "episodes").mkdir()
            report = evaluate({}, registry=[], repo_root=root)
            self.assertNotIn("AUDIO_HISTORY_RECEIPT_RECOVERY", report["blocking_gates"])


if __name__ == "__main__":
    unittest.main()
