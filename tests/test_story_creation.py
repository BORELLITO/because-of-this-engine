import copy
import unittest

from production.story_creation import CREATION_GATES, audit_story_creation


def valid_manifest():
    scene_ids = ["S01", "S02", "S03", "S04"]
    beats = [
        {"scene_id": "S01", "causal_role": "hook", "emotion": "curiosity", "state_before": "unknown", "state_after": "question"},
        {"scene_id": "S02", "causal_role": "escalation", "emotion": "unease", "state_before": "question", "state_after": "threat"},
        {"scene_id": "S03", "causal_role": "consequence", "emotion": "fear", "state_before": "threat", "state_after": "flight"},
        {"scene_id": "S04", "causal_role": "recurrence", "emotion": "chill", "state_before": "flight", "state_after": "doubt"},
    ]
    return {
        "video_id": "test-episode",
        "title": "The Door That Opened Twice",
        "story_profile": {"truth_mode": "DECLARED_FICTION"},
        "scenes": [{"scene_id": scene_id, "duration": 15} for scene_id in scene_ids],
        "story_graph": {"beats": beats},
        "story_creation": {
            "idea": {
                "title": "The Door That Opened Twice",
                "premise": "A sealed door opens twice after the building is empty.",
                "audience_promise": "Watch the contradiction tighten until the final recurrence.",
                "central_question": "Who opened the door?",
                "hook_type": "impossible_evidence",
            },
            "truth": {
                "mode": "DECLARED_FICTION",
                "disclosure": "This is an original fictional story.",
            },
            "causal_chain": {
                "cause": "The camera records a door that should not move.",
                "escalation": ["The lock remains intact.", "The witness sees the hallway empty."],
                "consequence": "The recording contradicts the physical scene.",
                "why_it_mattered": "The final recurrence makes the contradiction personal.",
            },
            "emotional_arc": {
                "primary": "tension",
                "secondary": "curiosity",
                "target_sensations": ["curiosity", "unease", "dread"],
            },
            "promise_payoff": {
                "promise": "The viewer will understand what the impossible recording reveals.",
                "payoff": "The same trigger returns after the evidence is gone.",
                "payoff_type": "recurrence",
                "promise_paid": True,
            },
            "visual_feasibility": {
                "checked_before_script": True,
                "scene_ids": scene_ids,
                "approved_scene_ids": scene_ids,
                "coverage_ratio": 1.0,
            },
            "channel_diversity": {
                "comparison_window": "last_20_episodes",
                "recent_episode_count": 3,
                "similarity_score": 0.2,
                "similarity_status": "PASS",
                "unique_signature": "sealed-door-double-recurrence",
            },
            "original_authorship": {
                "original_script": True,
                "original_narration": True,
                "editorial_transform": True,
                "asset_provenance_complete": True,
                "mass_production_risk": "LOW",
            },
            "monetization_safety": {
                "youtube_ad_safety": "LOW_RISK",
                "tiktok_originality": "ORIGINAL",
                "claims_reviewed": True,
                "disclosure_present": True,
                "risk_flags": {
                    "graphic_content": "NONE",
                    "harmful_claims": "NONE",
                    "shocking_content": "LOW",
                },
            },
            "duration": {
                "target_seconds": 60,
                "planned_seconds": 60,
                "estimated_narration_seconds": 59.7,
                "padding_seconds": 0,
                "padding_status": "PASS",
            },
            "red_team": {
                "status": "PASS",
                "editorial": {"status": "PASS", "blocking_issues": []},
                "factual": {"status": "PASS", "blocking_issues": []},
                "monetization": {"status": "PASS", "blocking_issues": []},
            },
        },
    }


class StoryCreationTests(unittest.TestCase):
    def gate(self, report, code):
        return next(gate for gate in report["gates"] if gate["code"] == code)

    def test_complete_creation_contract_passes(self):
        report = audit_story_creation(valid_manifest())
        self.assertEqual(report["status"], "STORY_CREATION_PASS")
        self.assertEqual(report["blocked_gates"], [])
        self.assertEqual(len(report["gates"]), len(CREATION_GATES))

    def test_missing_creation_contract_blocks(self):
        manifest = valid_manifest()
        manifest.pop("story_creation")
        report = audit_story_creation(manifest)
        self.assertEqual(report["status"], "STORY_CREATION_BLOCKED")
        self.assertIn("C0", report["blocked_gates"])
        self.assertIn("C11", report["blocked_gates"])

    def test_promise_must_be_paid(self):
        manifest = valid_manifest()
        manifest["story_creation"]["promise_payoff"]["promise_paid"] = False
        self.assertEqual(self.gate(audit_story_creation(manifest), "C4")["status"], "BLOCKED")

    def test_every_beat_needs_state_change(self):
        manifest = valid_manifest()
        manifest["story_graph"]["beats"][1]["state_after"] = "question"
        self.assertEqual(self.gate(audit_story_creation(manifest), "C5")["status"], "BLOCKED")

    def test_similarity_blocks_repetitive_channel(self):
        manifest = valid_manifest()
        manifest["story_creation"]["channel_diversity"]["similarity_score"] = 0.8
        self.assertEqual(self.gate(audit_story_creation(manifest), "C7")["status"], "BLOCKED")

    def test_graphic_content_blocks_monetization_gate(self):
        manifest = valid_manifest()
        manifest["story_creation"]["monetization_safety"]["risk_flags"]["graphic_content"] = "GRAPHIC"
        self.assertEqual(self.gate(audit_story_creation(manifest), "C9")["status"], "BLOCKED")

    def test_padding_is_not_accepted(self):
        manifest = valid_manifest()
        manifest["story_creation"]["duration"]["padding_seconds"] = 3
        self.assertEqual(self.gate(audit_story_creation(manifest), "C10")["status"], "BLOCKED")

    def test_red_team_is_required(self):
        manifest = valid_manifest()
        manifest["story_creation"]["red_team"]["factual"]["status"] = "BLOCKED"
        self.assertEqual(self.gate(audit_story_creation(manifest), "C11")["status"], "BLOCKED")

    def test_fiction_needs_disclosure(self):
        manifest = valid_manifest()
        manifest["story_creation"]["truth"]["disclosure"] = ""
        self.assertEqual(self.gate(audit_story_creation(manifest), "C1")["status"], "BLOCKED")

    def test_visual_feasibility_must_precede_script_for_new_story(self):
        manifest = valid_manifest()
        manifest["story_creation"]["visual_feasibility"]["checked_before_script"] = False
        self.assertEqual(self.gate(audit_story_creation(manifest), "C6")["status"], "BLOCKED")

    def test_legacy_backfill_is_explicit(self):
        manifest = valid_manifest()
        feasibility = manifest["story_creation"]["visual_feasibility"]
        feasibility["checked_before_script"] = False
        manifest["story_creation"]["legacy_backfill"] = True
        manifest["story_creation"]["backfill_reason"] = "Existing approved episode migrated into the new contract."
        report = audit_story_creation(manifest)
        self.assertEqual(self.gate(report, "C6")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
