"""Non-promoting, deterministic report tests for visual rights reconciliation."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from production.visual_reconciliation_dossier_v21 import build_dossier, inspect_repo

ROOT = Path(__file__).resolve().parents[1]
RECORD = "episodes/episode-005/production-record.json"
IDS_PENDING_RIGHTS = {
    "pexels-11764431",
    "pixabay-radio-vintage-old-171435",
    "nasa-svs-geos5-clouds-no-labels-4819",
    "pixabay-radar-black-green-target-symbol-57670",
    "pexels-5523892",
    "pexels-12590338",
}
S09 = "pexels-8888977"


class V21VisualReconciliationDossierTests(unittest.TestCase):
    def _sources(self):
        rec = json.loads((ROOT / RECORD).read_text(encoding="utf-8"))
        man = json.loads((ROOT / rec["visual_manifest_reference"]).read_text(encoding="utf-8"))
        plan = json.loads((ROOT / man["source_plan"]).read_text(encoding="utf-8"))
        return rec, plan, man

    def test_real_episode_is_reconciliation_required_not_approved(self):
        result = inspect_repo(ROOT, RECORD)
        self.assertEqual(result["status"], "RECONCILIATION_REQUIRED")
        self.assertEqual(result["asset_count"], 16)
        self.assertEqual(result["render_rights_matched_count"], 9)
        self.assertEqual(result["missing_render_rights"], [])
        self.assertEqual(set(result["pending_render_rights"]), IDS_PENDING_RIGHTS | {S09})
        self.assertEqual(set(result["pending_recorded_rights"]), IDS_PENDING_RIGHTS | {S09})
        self.assertEqual(result["stale_render_rights"], [])
        self.assertEqual(set(result["approved_manifest_only_pending_render_rights"]), IDS_PENDING_RIGHTS | {S09})
        self.assertEqual(result["pending_visual_approval"], [])
        self.assertEqual(result["source_provenance_mismatches"], [])
        self.assertEqual(len(result["draft_pending_rights_not_canonical"]), 0)
        self.assertEqual(result["rights_ledger_entry_count"], 16)
        self.assertEqual(result["render"], "NOT_RUN")
        self.assertFalse(result["production_enablement"])
        self.assertFalse(any(x["approved_for_render"] for x in result["draft_pending_rights_not_canonical"]))

    def test_dossier_does_not_mutate_inputs_or_promote_published_rights(self):
        rec, plan, man = self._sources()
        backup = copy.deepcopy((rec, plan, man))
        report = build_dossier(rec, plan, man)
        self.assertEqual((rec, plan, man), backup)
        self.assertTrue(all(x["render_rights_status"] == "PENDING_INDEPENDENT_RENDER_RIGHTS" for x in report["assets"] if x["asset_id"] in IDS_PENDING_RIGHTS | {S09}))
        self.assertTrue(all(x["user_approval_inferred"] is False for x in report["assets"]))

    def test_missing_human_approval_blocks_even_if_manifest_claims_approved(self):
        rec, plan, man = self._sources()
        plan["candidates"][0]["qa"]["human_approval"] = "PENDING"
        report = build_dossier(rec, plan, man)
        self.assertIn(plan["candidates"][0]["candidate_id"], report["pending_visual_approval"])

    def test_tampered_intake_sha_detected(self):
        rec, plan, man = self._sources()
        target = "pexels-11764431"
        candidate = next(x for x in plan["candidates"] if x["candidate_id"] == target)
        candidate["intake_artifact"]["sha256"] = "f" * 64
        report = build_dossier(rec, plan, man)
        self.assertIn(target, report["source_provenance_mismatches"])
        self.assertNotIn(target, report["approved_manifest_only_pending_render_rights"])

    def test_duplicate_asset_ids_are_reported_not_overwritten(self):
        rec, plan, man = self._sources()
        man["assets"].append(copy.deepcopy(man["assets"][0]))
        report = build_dossier(rec, plan, man)
        self.assertEqual(report["status"], "RECONCILIATION_REQUIRED")
        self.assertTrue(any("duplicate" in e for e in report["structural_issues"]))

    def test_coherent_synthetic_evidence_does_not_authorize_render(self):
        rec, plan, man = self._sources()
        # Test-only synthetic status/ledger transformations, never stored.
        for candidate in plan["candidates"]:
            if candidate["candidate_id"] == S09:
                candidate["rights_status"] = "APPROVED_FOR_MANIFEST_ONLY"
                candidate["qa"]["human_approval"] = "APPROVED_FOR_MANIFEST"
        for asset in man["assets"]:
            if asset["candidate_id"] == S09:
                asset["perceptual_hash"] = next(
                    p["intake_artifact"]["perceptual_hash"]
                    for p in plan["candidates"] if p["candidate_id"] == S09
                )
            # SYNTHETIC TEST FIXTURE ONLY: prove the all-approved path without
            # changing the actual episode. No license or release is granted.
            entry = next(e for e in rec["rights_ledger"] if e["asset_id"] == asset["candidate_id"])
            entry.update({
                "source_url": asset["source_page_url"],
                "sha256": asset["sha256"],
                "perceptual_fingerprint": asset["perceptual_hash"],
                "rights_status": "APPROVED",
                "approved_for_render": True,
                "approval_scope": "episode-005-render",
            })
        report = build_dossier(rec, plan, man)
        self.assertEqual(report["status"], "EVIDENCE_CONSISTENT_NOT_RENDER_AUTHORIZED", report)
        self.assertEqual(report["render_rights_matched_count"], 16)
        self.assertEqual(report["draft_pending_rights_not_canonical"], [])
        self.assertEqual(report["render"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
