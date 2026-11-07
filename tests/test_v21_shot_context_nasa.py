"""Real episode shot binding and verifiable credit delivery tests.

The user delegates visual approval to the engine, not permission to falsify
historical identities, license evidence, released outputs or publication.
"""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from production.shot_context_v21 import inspect, inspect_repository, NASA_CREDIT, NASA_DISCLOSURE
ROOT=Path(__file__).resolve().parents[1]
EP=ROOT/"episodes/episode-005"
REC=EP/"production-record.json"
MAN=EP/"visual/scene-asset-manifest.json"
EVD=ROOT/"reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json"
CREDIT=EP/"delivery/source-credits-pending.json"


class ActualShotSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=json.loads(REC.read_text(encoding="utf-8"))
        cls.scene=json.loads(MAN.read_text(encoding="utf-8"))
        cls.evidence=json.loads(EVD.read_text(encoding="utf-8"))
        cls.credit=json.loads(CREDIT.read_text(encoding="utf-8"))

    def test_real_active_episode_blocks_risky_s01_and_nasa(self):
        report=inspect_repository(self.record,repo_root=ROOT)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertEqual(report["actual_assignments"]["S01"],"pexels-11764431")
        self.assertEqual(report["actual_assignments"]["S03"],"pixabay-radio-vintage-old-171435")
        self.assertEqual(report["actual_assignments"]["S12"],"nasa-svs-geos5-clouds-no-labels-4819")
        self.assertTrue(any("actual scene S01" in x for x in report["failures"]))
        self.assertTrue(any("NASA S12: draft credit has not been verified" in x for x in report["failures"]))
        self.assertTrue(any("source_role S03 != actual assignment S01" in x for x in report["notices"]))
        self.assertEqual(report["publication"],"NOT_RUN")

    def test_official_nasa_credit_and_truth_are_precise_but_not_delivered(self):
        n=self.credit["nasa_svs_4819"]
        self.assertEqual(n["credit"],NASA_CREDIT)
        self.assertEqual(n["disclosure"],NASA_DISCLOSURE)
        self.assertEqual(n["source_url"],"https://svs.gsfc.nasa.gov/4819/")
        self.assertFalse(n["delivery_verified"])
        self.assertFalse(n["ready_for_publication"])
        self.assertIsNone(n["final_video_sha256"])
        self.assertIn("Trent L. Schindler",n["suggested_video_description_english"])
        self.assertIn("1983",n["suggested_video_description_english"])

    def test_missing_or_fake_credits_block(self):
        for field,value in (("source_url","https://nasa-credits.example/4819"),
                            ("disclosure","Real 1983 soviet sensor footage"),
                            ("mode","ARCHIVAL"),
                            ("credit","NASA endorsed")):
            forged=copy.deepcopy(self.credit)
            forged["nasa_svs_4819"][field]=value
            out=inspect(self.record,self.scene,self.evidence,forged)
            self.assertEqual(out["status"],"BLOCKED")
            self.assertTrue(any("NASA S12:" in x for x in out["failures"]))

    def test_fake_delivery_boolean_cannot_authorize_unidentified_actor_or_release(self):
        forged=copy.deepcopy(self.credit)
        forged["nasa_svs_4819"]["delivery_verified"]=True
        forged["nasa_svs_4819"]["ready_for_publication"]=False
        result=inspect(self.record,self.scene,self.evidence,forged)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("actual scene S01" in x for x in result["failures"]))
        self.assertFalse(self.record["production_enablement"])

    def test_missing_actual_shot_binding_is_rejected(self):
        changed=copy.deepcopy(self.scene)
        changed["shot_assignments"][0]["assignment"]["candidate_id"]="nonexistent-asset"
        out=inspect(self.record,changed,self.evidence,self.credit)
        self.assertEqual(out["status"],"BLOCKED")
        self.assertTrue(any("selected source not in active" in x for x in out["failures"]))

    def test_duplicated_active_media_is_rejected(self):
        changed=copy.deepcopy(self.scene)
        changed["shot_assignments"][0]["assignment"]["candidate_id"]=changed["shot_assignments"][1]["assignment"]["candidate_id"]
        out=inspect(self.record,changed,self.evidence,self.credit)
        self.assertEqual(out["status"],"BLOCKED")
        self.assertTrue(any("must not be reused" in x for x in out["failures"]))

if __name__=="__main__":
    unittest.main()
