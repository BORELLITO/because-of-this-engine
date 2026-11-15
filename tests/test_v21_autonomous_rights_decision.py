"""Episode 005 V2.1 rights decisions remain scoped and non-publishing."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from production.rights_autonomy_v21 import audit, audit_repository
from production.ledgers_v21 import validate_rights_ledger
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
ROOT = Path(__file__).resolve().parents[1]
class AutonomousRightsDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=json.loads((ROOT/"episodes/episode-005/production-record.json").read_text())
        cls.plan=json.loads((ROOT/"episodes/episode-005/visual/asset-acquisition-plan.json").read_text())
        cls.scene=json.loads((ROOT/"episodes/episode-005/visual/scene-asset-manifest.json").read_text())
        cls.evidence=json.loads((ROOT/"reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json").read_text())
        cls.disclosure=json.loads((ROOT/"episodes/episode-005/visual/scene-disclosures-v21.json").read_text())
    def test_current_active_rights_are_audited_without_nasa(self):
        report=audit(self.record,self.plan,self.scene,self.evidence,disclosure_contract=self.disclosure)
        self.assertEqual(report["status"],"PASS",report)
        self.assertEqual(report["auto_approved_count"],9)
        self.assertEqual(report["blocked_count"],0)
        self.assertFalse(any(x["provider"]=="nasa" for x in self.record["rights_ledger"]))
        self.assertEqual(audit_repository(self.record,repo_root=ROOT)["status"],"PASS")
        self.assertFalse(report["render_executed"])
        self.assertFalse(report["publication_executed"])
    def test_active_rights_match_manifest_and_remain_render_gated(self):
        self.assertEqual(len(self.record["rights_ledger"]),16)
        self.assertEqual(sum(x["rights_status"]=="APPROVED" for x in self.record["rights_ledger"]),16)
        self.assertEqual(sum(x["approved_for_render"] is True for x in self.record["rights_ledger"]),16)
        self.assertEqual(validate_rights_ledger(self.record)["status"],"PASS")
        self.assertEqual(validate_visual_rights_consistency(self.record,repo_root=ROOT)["status"],"BLOCKED")
        self.assertFalse(self.record["production_enablement"])
    def test_nasa_is_not_active_even_if_old_history_mentions_it(self):
        self.assertNotIn("nasa",{x["provider"] for x in self.record["rights_ledger"]})
        self.assertNotIn("nasa-svs-geos5-clouds-no-labels-4819",{x["candidate_id"] for x in self.scene["assets"]})
    def test_tampered_archive_hash_blocks_audit(self):
        evidence=copy.deepcopy(self.evidence)
        next(x for x in evidence["reviewed_assets"] if x["asset_id"]=="archive-prelinger-onguard1956-s07")["verified_source_sha256"]="f"*64
        report=audit(self.record,self.plan,self.scene,evidence,disclosure_contract=self.disclosure)
        self.assertEqual(report["status"],"BLOCKED")
if __name__=="__main__":
    unittest.main()
