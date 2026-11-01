from __future__ import annotations

import unittest

from production.editorial_story_gates import audit_editorial_story
from production.story_creation import audit_story_creation


def _manifest(with_contract: bool = True) -> dict:
    scene_ids = [f"S{index:02d}" for index in range(1, 13)]
    manifest = {
        "video_id": "editorial-test",
        "title": "The Room That Remembered",
        "scenes": [{"scene_id": scene_id} for scene_id in scene_ids],
        "story_graph": {
            "beats": [
                {"scene_id": scene_id, "causal_role": "setup" if index < 4 else "escalation"}
                for index, scene_id in enumerate(scene_ids, start=1)
            ]
        },
        "story_creation": {},
    }
    if with_contract:
        manifest["story_creation"]["editorial_contract"] = {
            "protagonist": {
                "name": "Nora",
                "goal": "prove what happened to her brother",
                "wound": "she chose the official explanation because it was easier to survive",
                "flaw": "she treats evidence as safer than grief",
                "agency_action": "she opens the sealed room after being warned to leave",
                "decision_scene_id": "S09",
                "irreversible_choice": "she destroys the only clean copy to keep the room open",
                "cost": "she loses the evidence that could restore her reputation",
                "change": "she accepts that truth requires a personal risk",
            },
            "wound": {
                "wound_scene_ids": ["S03", "S09"],
                "manifestation": "she corrects the record instead of naming her brother",
                "conflict": "the room repeats the version of events she used to protect herself",
                "link_to_choice": "her need to control the record makes her choose the dangerous copy",
            },
            "causal_escalation": [
                {
                    "from_scene": "S02",
                    "to_scene": "S04",
                    "trigger": "the recording contains a room absent from the plan",
                    "protagonist_action": "Nora compares the timestamp instead of stopping the playback",
                    "new_cost": "the archive records her voice before she speaks",
                    "state_change": "evidence becomes an active threat",
                },
                {
                    "from_scene": "S04",
                    "to_scene": "S07",
                    "trigger": "the recording changes when she tries to copy it",
                    "protagonist_action": "Nora follows the new timestamp into the sealed corridor",
                    "new_cost": "the exit disappears from the floor plan",
                    "state_change": "investigation becomes entrapment",
                },
                {
                    "from_scene": "S07",
                    "to_scene": "S09",
                    "trigger": "the room plays her brother's last instruction",
                    "protagonist_action": "Nora opens the final door and refuses the safe explanation",
                    "new_cost": "the clean evidence is overwritten by her presence",
                    "state_change": "solving the mystery requires sacrificing proof",
                },
            ],
            "anomaly_rule": {
                "rule": "the room can only appear when an archivist edits a record of a death",
                "violation": "Nora changes the timestamp after the recording has already closed",
                "cost": "the room replaces one piece of evidence with the viewer's own memory",
                "rule_scene_id": "S04",
                "cost_scene_id": "S09",
            },
            "emotional_turns": [
                {"scene_id": "S02", "from": "confidence", "to": "curiosity", "cause": "the impossible room appears"},
                {"scene_id": "S07", "from": "curiosity", "to": "dread", "cause": "the exit vanishes from the plan"},
                {"scene_id": "S09", "from": "dread", "to": "grief", "cause": "her brother speaks through the recording"},
            ],
            "payoff": {
                "early_clue_scene_ids": ["S02", "S04"],
                "final_scene_id": "S12",
                "payoff_type": "recontextualization",
                "final_consequence": "the archive preserves Nora's choice as the event it was meant to record",
                "emotional_aftertaste": "truth survives, but Nora can no longer stand outside it",
                "recontextualizes_opening": True,
                "central_question_resolved": True,
            },
            "visual_dramatization": [
                {
                    "scene_id": scene_id,
                    "human_action": f"Nora takes a consequential action in {scene_id}",
                    "visual_evidence": f"the frame shows the physical result of that action in {scene_id}",
                    "subjective_stakes": "the evidence changes what she can safely choose next",
                    "not_just_atmosphere": True,
                }
                for scene_id in scene_ids
            ],
            "density": {
                "meaningful_beat_count": 10,
                "visual_shot_count": 18,
                "micro_beat_count": 4,
                "story_seconds": 72,
                "padding_seconds": 0.4,
                "repeated_visual_count": 0,
            },
            "originality": {
                "core_mechanism": "an archive edits the witness who edits it",
                "familiar_trope": "the haunted recording",
                "distinctive_inversion": "the investigator becomes the missing evidence",
                "comparison_set": ["found footage", "archival ghost story", "closed-room mystery"],
                "similarity_score": 0.32,
            },
            "narration": {
                "naturalness_status": "PASS",
                "generic_line_count": 0,
                "orphan_line_count": 0,
                "causal_link_count": 7,
                "action_consequence_ratio": 0.86,
                "reviewed_sentence_count": 18,
                "line_evidence": [
                    "Nora's choice changes the recording",
                    "the changed recording removes her exit",
                    "the missing exit forces the final sacrifice",
                ],
            },
        }
    return manifest


class EditorialStoryGateTests(unittest.TestCase):
    def test_explicit_contract_passes_all_editorial_gates(self):
        report = audit_editorial_story(_manifest(), _manifest()["story_creation"])
        self.assertEqual(report["status"], "EDITORIAL_STORY_PASS")
        self.assertEqual(report["blocked_gates"], [])
        self.assertEqual(len(report["gates"]), 11)

    def test_missing_contract_is_fail_closed(self):
        report = audit_editorial_story(_manifest(False), {})
        self.assertEqual(report["status"], "EDITORIAL_STORY_BLOCKED")
        self.assertIn("E0", report["blocked_gates"])
        self.assertIn("E7", report["blocked_gates"])

    def test_story_creation_audit_exposes_editorial_report(self):
        report = audit_story_creation(_manifest())
        self.assertIn("editorial_story", report)
        self.assertEqual(report["editorial_story"]["status"], "EDITORIAL_STORY_PASS")
        self.assertEqual(report["schema_version"], "1.1")


if __name__ == "__main__":
    unittest.main()
