from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from production.finalize_manifest import mark_complete


class ReleaseBoundaryTests(unittest.TestCase):
    def _complete(self, mode: str) -> str:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            final_manifest = root / "final-manifest.json"
            receipt = root / "cleanup.json"
            final_manifest.write_text(json.dumps({
                "status": "READY_FOR_CLEANUP",
                "mode": mode,
                "job_id": "test-job",
            }), encoding="utf-8")
            receipt.write_text(json.dumps({"status": "DRIVE_VERIFIED"}), encoding="utf-8")
            return mark_complete(final_manifest, receipt)["status"]

    def test_preview_can_never_become_production_complete(self) -> None:
        self.assertEqual(self._complete("preview"), "PREVIEW_COMPLETE")

    def test_final_receipt_can_become_production_complete(self) -> None:
        self.assertEqual(self._complete("final"), "PRODUCTION_COMPLETE")


if __name__ == "__main__":
    unittest.main()
