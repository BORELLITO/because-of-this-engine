"""Source identity regressions: provider wrapper aliases and case-sensitive Drive IDs."""
import json
import tempfile
import unittest
from pathlib import Path

from production.asset_reuse_brain import source_asset_key, _asset_keys, audit


class SourceIdentityV11Tests(unittest.TestCase):
    def test_pexels_id_identical_under_original_and_stock_wrappers(self):
        url="https://www.pexels.com/video/elevator-doors-opening-to-underground-garage-34779661/"
        original={"provider":"original","source_page_url":url}
        stock={"provider":"pexels","provider_asset_id":"34779661","source_page_url":url}
        self.assertEqual(source_asset_key(original),"pexels:34779661")
        self.assertEqual(source_asset_key(original),source_asset_key(stock))

    def test_drive_source_id_preserves_case(self):
        a={"provider":"original","source_page_url":"https://drive.google.com/file/d/AbC_12-z/view?usp=drivesdk"}
        b={"provider":"original","source_page_url":"https://drive.google.com/file/d/abc_12-z/view?usp=drivesdk"}
        self.assertEqual(source_asset_key(a),"drive_file:AbC_12-z")
        self.assertNotEqual(source_asset_key(a),source_asset_key(b))

    def test_drive_file_id_identity_is_case_sensitive(self):
        a={"drive_file_id":"AbC_12-z"}
        b={"drive_file_id":"abc_12-z"}
        self.assertNotEqual(_asset_keys(a),_asset_keys(b))

    def test_declared_source_identity_cannot_hide_pexels_origin(self):
        asset={"provider":"original", "source_asset_key":"original:made-up",
               "source_page_url":"https://www.pexels.com/video/7701962/"}
        keys=_asset_keys(asset)
        self.assertIn(("source_asset","original:made-up"),keys)
        self.assertIn(("source_asset","pexels:7701962"),keys)

    def test_cross_provider_alias_reuse_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old=root/"episodes/old";new=root/"episodes/new"
            old.mkdir(parents=True);new.mkdir()
            url="https://www.pexels.com/video/7701962/"
            old_manifest={"video_id":"old",
                "scenes":[{"scene_id":"S01","asset":{"asset_id":"o","provider":"original",
                     "source_page_url":url,"sha256":"a"*64}}]}
            new_manifest={"video_id":"new",
                "scenes":[{"scene_id":"S01","asset":{"asset_id":"n","provider":"pexels",
                     "source_page_url":url,"sha256":"b"*64}}]}
            (old/"manifest.json").write_text(json.dumps(old_manifest))
            target=new/"manifest.json";target.write_text(json.dumps(new_manifest))
            result=audit(target,root)
            self.assertEqual(result["status"],"BLOCKED")
            self.assertTrue(result["cross_episode_duplicates"])


if __name__=="__main__":
    unittest.main()
