"""Active Episode 005 has one mandatory actor disclosure and no NASA source."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from production.scene_disclosures_v21 import ACTOR_ID,ACTOR_SHOT,ACTOR_SAMPLE_SHA256,validate_disclosure,audit_repository,ffmpeg_actor_overlay,load_for_preview
ROOT=Path(__file__).resolve().parents[1]
SCENE_PATH=ROOT/"episodes/episode-005/visual/scene-asset-manifest.json"
DISCLOSURE_PATH=ROOT/"episodes/episode-005/visual/scene-disclosures-v21.json"
RECORD_PATH=ROOT/"episodes/episode-005/production-record.json"
class SceneDisclosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=json.loads(SCENE_PATH.read_text())
        cls.disclosures=json.loads(DISCLOSURE_PATH.read_text())
        cls.record=json.loads(RECORD_PATH.read_text())
    def test_active_disclosure_is_exact_and_no_nasa(self):
        result=validate_disclosure(self.scene,self.disclosures)
        self.assertEqual(result["status"],"PASS",result)
        self.assertEqual(set(result["checked_shots"]),{ACTOR_SHOT})
        self.assertEqual(set(load_for_preview(SCENE_PATH,self.scene)),{ACTOR_ID})
        self.assertNotIn("nasa",self.disclosures["policy_id"])
        self.assertEqual(audit_repository(self.record,repo_root=ROOT)["status"],"PASS")
    def test_actor_receipt_and_text_are_bound(self):
        actor=self.disclosures["disclosures"][0]
        self.assertEqual(actor["asset_id"],ACTOR_ID)
        self.assertEqual(actor["verification"]["sample_video_sha256"],ACTOR_SAMPLE_SHA256)
        self.assertIn("DRAMATIZATION - NOT ARCHIVAL FOOTAGE",ffmpeg_actor_overlay(actor))
    def test_tampered_actor_receipt_blocks(self):
        changed=copy.deepcopy(self.disclosures)
        changed["disclosures"][0]["verification"]["sample_video_sha256"]="f"*64
        self.assertEqual(validate_disclosure(self.scene,changed)["status"],"BLOCKED")
if __name__=="__main__":
    unittest.main()
