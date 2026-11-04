"""V1.1 post-correction regression tests; no API calls or rendering."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from production.quality_gates import _story_intelligence, _captions, _narration, _provenance


class V74EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        (self.root / "rendered").mkdir()

    def write(self, name, obj):
        p = self.root / "rendered" / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def good_visual(self, filename="visual-story-qa-final.json"):
        self.write(filename, {"status": "VISUAL_STORY_QA_PASS"})

    def good_timing(self):
        self.write("narration-coverage.json", {
            "status": "STORY_INTELLIGENCE_PASS",
            "narration_coverage": {"timing_status": "FORCED_ALIGNMENT_SCENE_TIMES_PASS"},
        })

    def test_missing_both_reports_blocks(self):
        status, report = _story_intelligence(self.root)
        self.assertTrue(status.startswith("BLOCKED"))
        self.assertIsNone(report["visual"])

    def test_missing_visual_report_blocks(self):
        self.good_timing()
        self.assertIn("visual", _story_intelligence(self.root)[0])

    def test_missing_timing_report_blocks(self):
        self.good_visual()
        self.assertIn("narration coverage", _story_intelligence(self.root)[0])

    def test_bad_visual_status_blocks(self):
        self.write("visual-story-qa-final.json", {"status": "BLOCKED"})
        self.good_timing()
        self.assertIn("BLOCKED", _story_intelligence(self.root)[0])

    def test_final_visual_report_is_accepted(self):
        self.good_visual()
        self.good_timing()
        self.assertTrue(_story_intelligence(self.root)[0].startswith("PASS"))

    def test_bad_timing_status_blocks(self):
        self.good_visual()
        self.write("narration-coverage.json", {
            "status": "STORY_INTELLIGENCE_PASS",
            "narration_coverage": {"timing_status": "MISSING"},
        })
        self.assertIn("BLOCKED", _story_intelligence(self.root)[0])

    def test_caption_gate_uses_real_quality_status(self):
        with patch("production.quality_gates.quality_report", return_value={
            "status": "CAPTION_QA_PASS", "event_count": 19,
        }):
            self.assertEqual(_captions(Path("dummy.json"), "final")[0], "PASS")
        with patch("production.quality_gates.quality_report", return_value={
            "status": "PASS", "event_count": 19,
        }):
            self.assertEqual(_captions(Path("dummy.json"), "final")[0], "BLOCKED")

    def test_actual_voice_schema_is_supported(self):
        (self.root / "audio").mkdir()
        (self.root / "audio/narration.wav").write_bytes(b"not-used-in-this-non-media-test")
        manifest = {
            "voice": {"provider": "gemini_tts", "model_or_voice_type": "gemini-3.8-flash-tts",
                      "voice_name": "Charon", "language_code": "en-US", "style": "restrained"},
            "audio": {"path": "audio/narration.wav"},
        }
        self.assertEqual(_narration(manifest, self.root)[0], "PASS")
        manifest["voice"].pop("voice_name")
        self.assertEqual(_narration(manifest, self.root)[0], "BLOCKED")

    def test_final_must_have_approved_rights(self):
        scene = {"scene_id": "S01", "asset": {
            "source_page_url": "https://example.org/asset", "license": "commercial",
            "sha256": "test", "rights_status": "PREVIEW_ONLY",
            "approved_for_render": False, "drive_file_id": "test",
        }}
        m = {"story_profile": {"truth_mode": "DECLARED_FICTION"},
             "story_creation": {"truth": {"disclosure": "Fiction."}}, "scenes": [scene]}
        self.assertIn("BLOCKED", _provenance(m, "final")[0])
        scene["asset"]["rights_status"] = "APPROVED"
        scene["asset"]["approved_for_render"] = True
        self.assertNotIn("approved_rights", _provenance(m, "final")[0])

    def test_quality_checks_are_read_only(self):
        self.good_visual()
        self.good_timing()
        snapshots = {p.name: p.read_bytes() for p in (self.root / "rendered").iterdir()}
        _story_intelligence(self.root)
        self.assertEqual(snapshots, {p.name: p.read_bytes() for p in (self.root / "rendered").iterdir()})


if __name__ == "__main__":
    unittest.main()
