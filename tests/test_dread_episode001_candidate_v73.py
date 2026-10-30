from __future__ import annotations
import json, unittest
from pathlib import Path
from production.cinematic_dread import plan
ROOT=Path(__file__).resolve().parents[1]
class DreadEpisode001CandidateTests(unittest.TestCase):
    def test_candidate_is_separate_and_unapproved(self):
        parent=ROOT/"episodes/video-001"
        candidate=json.loads((parent/"atmosphere-candidate-v73.json").read_text())
        manifest=json.loads((parent/"preview-manifest.json").read_text())
        self.assertNotIn("atmosphere",manifest)
        self.assertTrue(candidate["not_a_manifest_replacement"])
        self.assertEqual(candidate["atmosphere"]["director_review"],"PENDING")
        self.assertFalse(candidate.get("not_authorized_for_production") is False)
        self.assertEqual(candidate["episode_id"],manifest["video_id"])
        enriched=dict(manifest,atmosphere=candidate["atmosphere"])
        directions=plan(enriched)
        self.assertEqual([s["intensity"] for s in directions["scenes"]],
                         [1,2,3,2,3,4,4,3])
        self.assertTrue(directions["human_final_approval_required"])
if __name__=="__main__":unittest.main()
