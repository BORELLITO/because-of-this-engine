from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from experimental.v72.shot_review import review, ReviewError
from experimental.v72.whisperx_optional import validate_candidate, CandidateAlignmentError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "episodes/video-001/preview-manifest.json"

class ExperimentalFreeIntegrationTests(unittest.TestCase):
    def sample(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_preview_metadata_report_is_not_asset_approval(self):
        result = review(self.sample())
        self.assertEqual(result["experimental_version"], "7.2")
        self.assertEqual(result["scene_count"], 12)
        self.assertFalse(result["media_files_verified"])
        self.assertFalse(result["visual_content_verified"])
        self.assertFalse(result["rights_verified_for_publication"])
        self.assertTrue(result["manual_approval_required"])

    def test_repeated_source_is_blocked(self):
        m = self.sample()
        m["scenes"][1]["asset"] = deepcopy(m["scenes"][0]["asset"])
        r = review(m)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertTrue(any("REPEATED_SOURCE" in x for x in r["scenes"][1]["issues"]))

    def test_absent_direct_anchor_is_blocked(self):
        m = self.sample()
        m["scenes"][0]["visual_semantics"]["narrative_anchors"]["direct_required"] = []
        self.assertEqual(review(m)["status"], "BLOCKED")

    def test_duplicate_scene_id_is_blocked(self):
        m = self.sample()
        m["scenes"][1]["scene_id"] = m["scenes"][0]["scene_id"]
        with self.assertRaises(ReviewError):
            review(m)

    def test_preview_only_must_never_clear_release(self):
        m = self.sample()
        m["lifecycle_status"] = "APPROVED"
        result = review(m)
        self.assertEqual(result["status"], "BLOCKED")

    def test_whisperx_words_must_be_real_and_exact(self):
        c = validate_candidate("The door opened.", [
            {"word":"The","start":0.0,"end":0.18},
            {"word":"door","start":0.2,"end":0.49},
            {"word":"opened.","start":0.5,"end":0.95}],1.0)
        self.assertEqual(c["status"], "CANDIDATE_ONLY")
        self.assertFalse(c["canonical_captions_modified"])

    def test_whisperx_missing_timestamps_rejected(self):
        with self.assertRaises(CandidateAlignmentError):
            validate_candidate("The door.", [{"word":"The","start":0.0,"end":0.1},{"word":"door"}], 1.0)

    def test_whisperx_word_mismatch_rejected(self):
        with self.assertRaises(CandidateAlignmentError):
            validate_candidate("The door.", [{"word":"A","start":0.0,"end":0.1},{"word":"door","start":0.2,"end":0.3}],1.0)

    def test_whisperx_overlap_rejected(self):
        with self.assertRaises(CandidateAlignmentError):
            validate_candidate("The door.", [{"word":"The","start":0.0,"end":0.3},{"word":"door","start":0.2,"end":0.5}],1.0)

if __name__ == "__main__":
    unittest.main()
