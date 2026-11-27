import json
import tempfile
import unittest
from pathlib import Path

from production.brazil_files_ep001_preflight_v1 import (
    BRIEF_PATH,
    DOSSIER_PATH,
    NARRATIVE_DOSSIER_PATH,
    NAMESPACE_LOCK_PATH,
    LEGACY_NAMESPACE_ROOT,
    RECEIPTS_PATH,
    evaluate_preflight,
)
from production.brazil_files_orchestrator import validate_case_brief


ROOT = Path(__file__).resolve().parents[1]


class BrazilFilesEpisode001PreflightTests(unittest.TestCase):
    def test_staged_selected_case_brief_is_valid(self):
        brief = json.loads((ROOT / BRIEF_PATH).read_text(encoding="utf-8"))
        report = validate_case_brief(brief)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_id"], "official-ufo-night-1986")
        self.assertEqual(brief["staging_namespace"], "episodes/brazil-files/episode-001")

    def test_real_preflight_blocks_missing_evidence_and_namespace_collision(self):
        report = evaluate_preflight(ROOT)
        self.assertEqual(report["status"], "BRAZIL_FILES_PREFLIGHT_BLOCKED")
        self.assertFalse(report["production_started"])
        self.assertEqual(report["runflow_handoff"], "BLOCKED")
        self.assertTrue(report["namespace_collision"])
        self.assertTrue(report["namespace_protected"])
        self.assertFalse(any(error.startswith("namespace:episodes/episode-001") for error in report["errors"]))
        self.assertEqual(report["narrative"]["status"], "PASS")
        self.assertTrue(any(error.startswith("dossier:") for error in report["errors"]))
        self.assertTrue(any(error.startswith("receipts:") for error in report["errors"]))

    def test_narrative_dossier_is_valid_but_not_clip_approval(self):
        narrative = json.loads((ROOT / NARRATIVE_DOSSIER_PATH).read_text(encoding="utf-8"))
        self.assertEqual(narrative["status"], "NARRATIVE_DOSSIER_READY_CLIP_RESEARCH_PENDING")
        self.assertEqual(narrative["beat_count"], 16)
        self.assertEqual(len(narrative["beats"]), 16)
        self.assertEqual(narrative["clip_selection_status"], "NOT_STARTED")
        self.assertEqual(narrative["rights_status"], "NOT_STARTED")
        self.assertFalse(narrative["production_started"])
        self.assertEqual(narrative["runflow_handoff"], "BLOCKED")
        self.assertEqual(narrative["beats"][-1]["representation_type"], "CTA")

    def test_preflight_does_not_treat_partial_files_as_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = root / BRIEF_PATH
            staged.parent.mkdir(parents=True)
            source = ROOT / BRIEF_PATH
            staged.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            (root / LEGACY_NAMESPACE_ROOT).mkdir(parents=True)
            (root / LEGACY_NAMESPACE_ROOT / "manifest.json").write_text(
                json.dumps({"truth_mode": "DECLARED_FICTION"}) + "\n",
                encoding="utf-8",
            )
            (root / NAMESPACE_LOCK_PATH).parent.mkdir(parents=True, exist_ok=True)
            (root / NAMESPACE_LOCK_PATH).write_text(json.dumps({
                "schema_version": "1.0",
                "legacy_namespace": str(LEGACY_NAMESPACE_ROOT),
                "staging_namespace": str(Path("episodes/brazil-files/episode-001")),
                "legacy_preserved": True,
                "staging_isolated": True,
                "overwrite_legacy": False,
                "migration_status": "PRESERVE_LEGACY_USE_STAGING",
            }) + "\n", encoding="utf-8")
            (root / DOSSIER_PATH).parent.mkdir(parents=True, exist_ok=True)
            (root / DOSSIER_PATH).write_text("{}\n", encoding="utf-8")
            (root / RECEIPTS_PATH).write_text("{}\n", encoding="utf-8")
            report = evaluate_preflight(root)
            self.assertEqual(report["status"], "BRAZIL_FILES_PREFLIGHT_BLOCKED")
            self.assertTrue(any(error.startswith("dossier:") for error in report["errors"]))
            self.assertTrue(any(error.startswith("receipts:") for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
