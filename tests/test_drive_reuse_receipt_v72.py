from __future__ import annotations
import json, unittest
from pathlib import Path
from experimental.v72.verify_drive_receipt import validate_metadata,ReceiptError
ROOT=Path(__file__).resolve().parents[1]
class DriveReuseReceiptTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((ROOT/"experimental/v72/verified_preview_001.json").read_text())
        self.entries=[{"id":a["drive_file_id"],"name":a["name"],"size":str(a["bytes"]),
           "md5Checksum":a["md5"],"mimeType": "video/mp4" if a["kind"]=="preview_mp4" else
             "audio/x-wav" if a["kind"]=="narration_wav" else "application/json",
           "trashed":False} for a in self.c["artifacts"]]
    def test_all_original_receipts_match(self):
        self.assertEqual(validate_metadata(self.c,self.entries)["status"],
                         "RECORDED_PREVIEW_DRIVE_METADATA_VERIFIED")
    def test_modified_media_hash_blocks_reuse(self):
        self.entries[0]["md5Checksum"]="0"*32
        with self.assertRaises(ReceiptError):validate_metadata(self.c,self.entries)
    def test_missing_artifact_blocks_reuse(self):
        with self.assertRaises(ReceiptError):validate_metadata(self.c,self.entries[:-1])
    def test_publication_is_never_approved(self):
        self.assertFalse(validate_metadata(self.c,self.entries)["release_approved"])
if __name__=="__main__":unittest.main()
