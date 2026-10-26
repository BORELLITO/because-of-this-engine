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

    def test_missing_narrative_anchor_contract_blocks_operational_qa(self) -> None:
        from production.visual_story_qa import _scene_report

        scene = self._scene()
        scene["narration_excerpt"] = "The building was demolished."
        del scene["visual_semantics"]["narrative_anchors"]
        scene["asset"] = candidate(action="demolition")
        qa = _scene_report(scene, "preview")
        self.assertEqual(qa["status"], "BLOCKED")
        self.assertIn("narrative_anchors.direct_required is mandatory", qa["reason"])

    def test_figure_anchor_accepts_silhouette_alias(self) -> None:
        scene = {
            "scene_id": "S01",
            "visual_match": "EXACT",
            "visual_semantics": {
                "role": "literal",
                "required": {"subjects": ["silhouette"]},
                "critical": {"subjects": ["silhouette"]},
                "narrative_anchors": {
                    "direct_required": ["figure"],
                    "minimum_direct": 1,
                },
            },
        }
        direct = candidate(action="standing")
        direct["visual_evidence"]["subjects"] = ["silhouette"]
        direct["visual_evidence"]["observed_subjects"] = ["silhouette"]
        direct["visual_evidence"]["environments"] = ["interior"]
        direct["visual_evidence"]["observed_environments"] = ["interior"]
        report = visual_match_report(scene, direct, require_review=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["narrative_alignment"]["direct_hits"], ["figure"])

    def test_forbidden_concepts_use_observed_pixels_for_approval(self) -> None:
        scene = {
            "scene_id": "S02",
            "visual_match": "EXACT",
            "visual_semantics": {
                "role": "literal",
                "required": {"environments": ["hotel"]},
                "forbidden": ["person"],
                "narrative_anchors": {
                    "direct_required": ["hotel"],
                    "minimum_direct": 1,
                },
            },
        }
        reviewed = candidate(action="standing")
        reviewed["source_description"] = "person in a hotel hallway"
        report = visual_match_report(scene, reviewed, require_review=True)
        self.assertEqual(report["status"], "PASS")

        reviewed["visual_evidence"]["observed_subjects"] = ["person"]
        blocked = visual_match_report(scene, reviewed, require_review=True)
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertIn("person", blocked["forbidden_hits"])

    def test_direct_narrative_anchor_passes(self) -> None:
        scene = self._scene()
        direct = candidate(action="demolition")
        direct["visual_evidence"]["objects"] = ["hourglass"]
        report = visual_match_report(scene, direct, require_review=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["narrative_alignment"]["direct_hits"], ["demolition"])


if __name__ == "__main__":
    unittest.main()
