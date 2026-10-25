import unittest

from production.visual_semantics import visual_match_report


def candidate(*, action: str) -> dict:
    return {
        "visual_evidence": {
            "reviewed": True,
            "basis": "pixel review",
            "subjects": ["building"],
            "actions": [action],
            "environments": ["hotel"],
            "objects": [],
            "moods": ["eerie"],
            "sample_timestamps": [0.5, 2.5, 4.5],
            "reviewer": "test",
            "reviewed_at": "2026-10-25T00:00:00Z",
            "review_method": "test frames",
            "observed_subjects": ["building"],
            "observed_actions": [action],
            "observed_environments": ["hotel"],
            "observed_objects": [],
        }
    }


class NarrativeAnchorGateTests(unittest.TestCase):
    def _scene(self) -> dict:
        return {
            "scene_id": "S11",
            "visual_match": "SYMBOLIC",
            "visual_semantics": {
                "role": "symbolic",
                "required": {"objects": ["hourglass"]},
                "preferred": {"moods": ["eerie"]},
                "narrative_anchors": {
                    "direct_required": ["demolition"],
                    "minimum_direct": 1,
                },
            },
        }

    def test_symbolic_metaphor_cannot_replace_concrete_narrated_event(self) -> None:
        scene = self._scene()
        metaphor = candidate(action="falling")
        metaphor["visual_evidence"]["objects"] = ["hourglass"]
        report = visual_match_report(scene, metaphor, require_review=True)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("demolition", report["narrative_alignment"]["direct_missing"])

    def test_direct_narrative_anchor_passes(self) -> None:
        scene = self._scene()
        direct = candidate(action="demolition")
        direct["visual_evidence"]["objects"] = ["hourglass"]
        report = visual_match_report(scene, direct, require_review=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["narrative_alignment"]["direct_hits"], ["demolition"])


if __name__ == "__main__":
    unittest.main()
