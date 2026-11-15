"""Episode 005 active rights reconcile exactly with the V2.1 manifest."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from production.ledgers_v21 import validate_rights_ledger
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
from production.visual_reconciliation_dossier_v21 import build_dossier
from production.visual_plan_contract import validate_visual_plan
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"episodes"/"episode-005"
class ActiveEpisodeRightsReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=json.loads((BASE/"production-record.json").read_text())
        cls.plan=json.loads((BASE/"visual"/"asset-acquisition-plan.json").read_text())
        cls.manifest=json.loads((BASE/"visual"/"scene-asset-manifest.json").read_text())
    def test_active_rights_entries_match_current_assets(self):
        self.assertEqual(len(self.manifest["assets"]),16)
        self.assertEqual(len(self.record["rights_ledger"]),16)
        self.assertEqual({x["asset_id"] for x in self.record["rights_ledger"]},{a["candidate_id"] for a in self.manifest["assets"]})
        self.assertNotIn("nasa",{x["provider"] for x in self.record["rights_ledger"]})
    def test_rights_identities_match_plan_manifest(self):
        rights={x["asset_id"]:x for x in self.record["rights_ledger"]}
        plans={x["candidate_id"]:x for x in self.plan["candidates"]}
        assets={x["candidate_id"]:x for x in self.manifest["assets"]}
        for key in assets:
            self.assertEqual(rights[key]["sha256"],assets[key]["sha256"])
            self.assertEqual(rights[key]["perceptual_fingerprint"],assets[key]["perceptual_hash"])
            if key in plans:
                self.assertEqual(rights[key]["sha256"],plans[key]["intake_artifact"]["sha256"])
    def test_visual_plan_passes_but_render_stays_blocked(self):
        self.assertEqual(validate_rights_ledger(self.record)["status"],"PASS")
        self.assertEqual(validate_visual_plan(self.plan,self.manifest)["status"],"VISUAL_PLAN_CONTRACT_PASS")
        self.assertEqual(validate_visual_rights_consistency(self.record,repo_root=ROOT)["status"],"BLOCKED")
        report=build_dossier(self.record,self.plan,self.manifest)
        self.assertEqual(report["status"],"EVIDENCE_CONSISTENT_NOT_RENDER_AUTHORIZED")
        self.assertEqual(report["asset_count"],16)
        self.assertEqual(report["render_rights_matched_count"],16)
        self.assertEqual(report["render"],"NOT_RUN")
        self.assertFalse(self.record["production_enablement"])
    def test_tampered_archive_record_blocks_reconciliation(self):
        rec=copy.deepcopy(self.record)
        next(x for x in rec["rights_ledger"] if x["asset_id"].startswith("archive-"))["sha256"]="f"*64
        self.assertEqual(validate_visual_rights_consistency(rec,repo_root=ROOT)["status"],"BLOCKED")
if __name__=="__main__":
    unittest.main()
