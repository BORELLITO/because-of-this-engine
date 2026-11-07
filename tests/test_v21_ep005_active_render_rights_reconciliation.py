"""Real Episode 005 rights migration: preserve history; never inherit old approvals.

No network, no audio generation, no renders, no catalog mutation.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from production.ledgers_v21 import validate_rights_ledger
from production.visual_rights_consistency_v21 import validate_visual_rights_consistency
from production.visual_reconciliation_dossier_v21 import build_dossier
from production.visual_plan_contract import validate_visual_plan

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "episodes" / "episode-005"
ARCHIVE = ROOT / "reports" / "archives" / "EP005_RIGHTS_LEDGER_BEFORE_ACTIVE_RECONCILIATION_20261107.json"
ORIGINAL_REPLACEMENTS = {
    "pexels-11764431",
    "pixabay-radio-vintage-old-171435",
    "nasa-svs-geos5-clouds-no-labels-4819",
    "pixabay-radar-black-green-target-symbol-57670",
    "pexels-5523892",
    "pexels-12590338",
    "pexels-8888977",
}
PENDING = set()
AUTO_APPROVED = ORIGINAL_REPLACEMENTS - PENDING


class ActiveEpisodeRightsReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((BASE / "production-record.json").read_text(encoding="utf-8"))
        cls.plan = json.loads((BASE / "visual" / "asset-acquisition-plan.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((BASE / "visual" / "scene-asset-manifest.json").read_text(encoding="utf-8"))
        cls.archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))

    def test_exactly_sixteen_rights_entries_match_current_sixteen_assets(self):
        rights = self.record["rights_ledger"]
        active = self.manifest["assets"]
        self.assertEqual(len(active), 16)
        self.assertEqual(len(rights), 16)
        self.assertEqual(len({x["asset_id"] for x in rights}), 16)
        self.assertEqual({x["asset_id"] for x in rights}, {a["candidate_id"] for a in active})

    def test_nine_original_active_approvals_untouched(self):
        before = {x["asset_id"]: x for x in self.archive["full_original_rights_ledger"]}
        current = {x["asset_id"]: x for x in self.record["rights_ledger"]}
        unchanged = set(before) & set(current)
        self.assertEqual(len(unchanged), 9)
        for key in unchanged:
            self.assertEqual(current[key], before[key], key)
            self.assertTrue(current[key]["approved_for_render"])
            self.assertEqual(current[key]["rights_status"], "APPROVED")

    def test_seven_retired_approved_records_are_preserved_only_in_archive(self):
        before = {x["asset_id"]: x for x in self.archive["full_original_rights_ledger"]}
        archived = {x["asset_id"]: x for x in self.archive["stale_entries_original"]}
        live = {x["asset_id"]: x for x in self.record["rights_ledger"]}
        self.assertEqual(len(self.archive["full_original_rights_ledger"]), 16)
        self.assertEqual(len(archived), 7)
        self.assertTrue(set(archived).isdisjoint(live))
        for key, value in archived.items():
            self.assertEqual(value, before[key])
            self.assertEqual(value["rights_status"], "APPROVED")
            self.assertTrue(value["approved_for_render"])

    def test_seven_new_assets_eligible_only_for_labelled_scoped_render(self):
        by_id = {x["asset_id"]: x for x in self.record["rights_ledger"]}
        self.assertEqual({k for k in ORIGINAL_REPLACEMENTS if by_id[k]["rights_status"] == "APPROVED"}, AUTO_APPROVED)
        self.assertEqual({k for k in ORIGINAL_REPLACEMENTS if by_id[k]["rights_status"] == "PENDING_INDEPENDENT_RENDER_RIGHTS"}, PENDING)
        for key in PENDING:
            entry=by_id[key]
            self.assertFalse(entry["approved_for_render"])
            self.assertFalse(entry["commercial_use"])
            self.assertIsNone(entry["approval_scope"])
            self.assertEqual(entry["used_by"],[])
            self.assertFalse(entry["global_catalog_updated"])
            self.assertFalse(entry["derived_rights_from_prior_asset"])
        for key in AUTO_APPROVED:
            entry=by_id[key]
            self.assertTrue(entry["approved_for_render"])
            self.assertTrue(entry["commercial_use"])
            self.assertEqual(entry["approval_scope"],"episode-005-render")
            self.assertEqual(entry["render_approval_status"],"AUTO_APPROVED_EVIDENCE_BOUND_V21")
            self.assertEqual(entry["used_by_semantics"],"AUTHORIZED_INTENDED_EPISODE_NOT_PROOF_OF_RELEASE_OR_PUBLICATION")
            self.assertFalse(entry["published_or_distributed"])

    def test_new_rights_identities_match_intake_bytes_and_perceptual_hashes(self):
        entries = {x["asset_id"]: x for x in self.record["rights_ledger"]}
        plans = {x["candidate_id"]: x for x in self.plan["candidates"]}
        visuals = {x["candidate_id"]: x for x in self.manifest["assets"]}
        for key in ORIGINAL_REPLACEMENTS:
            e, c, a = entries[key], plans[key], visuals[key]
            self.assertEqual(e["sha256"], c["intake_artifact"]["sha256"])
            self.assertEqual(e["perceptual_fingerprint"], c["intake_artifact"]["perceptual_hash"])
            self.assertEqual(e["source_url"], a["source_page_url"])
            self.assertEqual(e["provider"], a["provider"])
            self.assertEqual(e["license_name"], a["license_name"])
            self.assertEqual(e["sha256"], a["sha256"])
            self.assertEqual(e["perceptual_fingerprint"], a["perceptual_hash"])
            self.assertEqual(e["fingerprint_algorithm"], a["fingerprint_algorithm"])

    def test_license_source_review_is_not_a_render_license(self):
        self.assertEqual({x["provider"] for x in self.record["rights_ledger"] if x["asset_id"] in ORIGINAL_REPLACEMENTS}, {"nasa", "pexels", "pixabay"})
        nasa = next(x for x in self.record["rights_ledger"] if x["asset_id"].startswith("nasa-svs-"))
        self.assertTrue(nasa["credits_required"])
        self.assertIn("Greg Shirah", nasa["required_credit_text"])
        self.assertIn("2020", nasa["nasa_context_note"])
        s09 = next(x for x in self.record["rights_ledger"] if x["asset_id"] == "pexels-8888977")
        self.assertIn("NOT a true 1983 Soviet terminal", s09["narrative_risk_note"])
        self.assertEqual(s09["visual_qa_run_id"], 42388510746)

    def test_reconciled_rights_and_audio_still_block_real_release(self):
        canonical = validate_rights_ledger(self.record)
        self.assertEqual(canonical["status"], "PASS")
        self.assertEqual(canonical["failures"], [])
        self.assertEqual(validate_visual_plan(self.plan, self.manifest)["status"], "VISUAL_PLAN_CONTRACT_PASS")
        visual = validate_visual_rights_consistency(self.record, repo_root=ROOT)
        self.assertEqual(visual["status"], "PASS")
        self.assertEqual(visual["failures"], [])
        self.assertFalse(any("visual assets missing render rights" in x for x in visual["failures"]))
        report = build_dossier(self.record, self.plan, self.manifest)
        self.assertEqual(report["status"], "EVIDENCE_CONSISTENT_NOT_RENDER_AUTHORIZED")
        self.assertEqual(report["missing_render_rights"], [])
        self.assertEqual(report["stale_render_rights"], [])
        self.assertEqual(set(report["pending_recorded_rights"]), PENDING)
        self.assertEqual(set(report["pending_render_rights"]), PENDING)
        self.assertEqual(report["render_rights_matched_count"], 16)
        self.assertEqual(report["render"], "NOT_RUN")
        from production.audio_history_audit_v21 import audit as audit_audio_history
        self.assertEqual(audit_audio_history(ROOT)["status"], "BLOCKED")
        self.assertFalse(self.record["production_enablement"])


    def test_forged_pending_person_approval_does_not_pass_autonomous_gate(self):
        from production.rights_autonomy_v21 import audit_repository
        altered = copy.deepcopy(self.record)
        target = next(x for x in altered["rights_ledger"] if x["asset_id"] == "pexels-11764431")
        target["sha256"] = "f" * 64
        self.assertEqual(audit_repository(altered, repo_root=ROOT)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
