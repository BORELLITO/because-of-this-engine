import json
import tempfile
import unittest
from pathlib import Path

from production.brazil_files_clip_receipt_gate_v1 import (
    MIN_REQUIRED_RECEIPTS,
    RECEIPTS_ROOT,
    evaluate_clip_receipt_gate,
)


def _receipt(index: int, *, digest: str | None = None) -> dict:
    candidate_id = f"B{index:02d}-C01"
    return {
        "schema_version": "1.0",
        "receipt_id": f"receipt-{candidate_id.lower()}",
        "case_id": "official-ufo-night-1986",
        "beat_id": f"B{index:02d}",
        "candidate_id": candidate_id,
        "source_id": "PIXABAY",
        "source_url": f"https://pixabay.com/videos/{index}/",
        "media_url": f"https://cdn.pixabay.com/video/{index}.mp4",
        "license_url": "https://pixabay.com/service/license-summary/",
        "source_page_evidence": {
            "license_claim": "Free for use under the Pixabay Content License",
        },
        "download_evidence": {
            "file_name": f"{index}.mp4",
            "sha256": digest or f"{index:064x}",
            "container": "MP4",
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": 1920,
            "height": 1080,
            "duration_seconds": 10.0,
            "integrity_check": "sha256_verified_against_downloaded_bytes",
        },
        "rights_status": "VERIFIED",
        "fingerprint_status": "VERIFIED",
        "semantic_review": "PROVISIONAL_PASS",
        "selected_for_production": False,
        "production_started": False,
        "runflow_handoff": "BLOCKED_UNTIL_FULL_DOSSIER_AND_ALL_RECEIPTS",
    }


class ClipReceiptGateTests(unittest.TestCase):
    def test_real_staged_inventory_is_blocked_with_eight_missing(self):
        report = evaluate_clip_receipt_gate(Path(__file__).resolve().parents[1])
        self.assertEqual(report["status"], "CLIP_RECEIPTS_BLOCKED")
        self.assertEqual(report["receipt_file_count"], 14)
        self.assertEqual(report["verified_receipt_count"], 14)
        self.assertEqual(report["missing_receipts"], 8)
        self.assertFalse(report["production_started"])
        self.assertEqual(report["runflow_handoff"], "BLOCKED")

    def test_gate_passes_only_when_all_required_receipts_are_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_dir = root / RECEIPTS_ROOT
            receipt_dir.mkdir(parents=True)
            for index in range(1, MIN_REQUIRED_RECEIPTS + 1):
                (receipt_dir / f"B{index:02d}-C01.json").write_text(
                    json.dumps(_receipt(index)) + "\n",
                    encoding="utf-8",
                )
            report = evaluate_clip_receipt_gate(root)
            self.assertEqual(report["status"], "CLIP_RECEIPTS_PASS")
            self.assertEqual(report["verified_receipt_count"], MIN_REQUIRED_RECEIPTS)
            self.assertEqual(report["missing_receipts"], 0)

    def test_duplicate_fingerprint_blocks_even_with_twenty_two_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_dir = root / RECEIPTS_ROOT
            receipt_dir.mkdir(parents=True)
            for index in range(1, MIN_REQUIRED_RECEIPTS + 1):
                digest = "a" * 64 if index == 2 else None
                (receipt_dir / f"B{index:02d}-C01.json").write_text(
                    json.dumps(_receipt(index, digest=digest)) + "\n",
                    encoding="utf-8",
                )
            (receipt_dir / "B99-C01.json").write_text(
                json.dumps(_receipt(99, digest="a" * 64)) + "\n",
                encoding="utf-8",
            )
            report = evaluate_clip_receipt_gate(root)
            self.assertEqual(report["status"], "CLIP_RECEIPTS_BLOCKED")
            self.assertTrue(any("duplicate sha256 fingerprint" in error for error in report["errors"]))

    def test_invalid_receipt_does_not_count_even_if_status_fields_look_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_dir = root / RECEIPTS_ROOT
            receipt_dir.mkdir(parents=True)
            receipt = _receipt(1)
            del receipt["download_evidence"]["file_name"]
            (receipt_dir / "B01-C01.json").write_text(
                json.dumps(receipt) + "\n",
                encoding="utf-8",
            )
            report = evaluate_clip_receipt_gate(root)
            self.assertEqual(report["status"], "CLIP_RECEIPTS_BLOCKED")
            self.assertEqual(report["verified_receipt_count"], 0)
            self.assertEqual(report["missing_receipts"], MIN_REQUIRED_RECEIPTS)

    def test_unverified_rights_never_count_as_a_valid_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_dir = root / RECEIPTS_ROOT
            receipt_dir.mkdir(parents=True)
            receipt = _receipt(1)
            receipt["rights_status"] = "HOLD"
            (receipt_dir / "B01-C01.json").write_text(
                json.dumps(receipt) + "\n",
                encoding="utf-8",
            )
            report = evaluate_clip_receipt_gate(root)
            self.assertEqual(report["status"], "CLIP_RECEIPTS_BLOCKED")
            self.assertEqual(report["verified_receipt_count"], 0)
            self.assertEqual(report["missing_receipts"], MIN_REQUIRED_RECEIPTS)


if __name__ == "__main__":
    unittest.main()
