import unittest

from production.brazil_files_orchestrator import (
    AGENT_PIPELINE,
    PRODUCTION_BLOCKS,
    build_preparation_plan,
    validate_case_brief,
    validate_flow_receipts,
)


def valid_brief():
    return {
        "case_id": "noite-oficial-ovnis-1986",
        "working_title": "The Official UFO Night",
        "lane": "DOCUMENTED_UNEXPLAINED",
        "premise": "Brazilian military records describe an unidentified aerial event that remains disputed.",
        "source_urls": ["https://example.gov.br/archive"],
        "unknowns": ["What were the objects?", "Why did the official explanation remain incomplete?"],
        "visual_anchors": ["radar room", "night sky", "military runway"],
        "brazilian_anchor": "The story begins with Brazil's air-defense records and the people who witnessed the event.",
        "cultural_value": "Introduce the Brazilian context with respect and without reducing it to a stereotype.",
    }


class BrazilFilesOrchestratorTests(unittest.TestCase):
    def test_valid_brief_passes(self):
        report = validate_case_brief(valid_brief())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["narration_language"], "en-US")
        self.assertTrue(report["preserve_visual_motor"])

    def test_invalid_lane_blocks(self):
        brief = valid_brief()
        brief["lane"] = "ALIENS_CONFIRMED"
        self.assertEqual(validate_case_brief(brief)["status"], "BLOCKED")

    def test_other_project_reference_blocks(self):
        brief = valid_brief()
        brief["premise"] = "This belongs to Verbo no Chão"
        self.assertEqual(validate_case_brief(brief)["status"], "BLOCKED")

    def test_plan_requires_every_subagent(self):
        plan = build_preparation_plan(valid_brief())
        self.assertEqual(plan["status"], "READY_FOR_AGENT_EXECUTION")
        self.assertEqual(len(plan["agents"]), len(AGENT_PIPELINE))
        self.assertEqual(len(plan["blocks"]), len(PRODUCTION_BLOCKS))
        self.assertTrue(all(block["analyst"] and block["reviewer"] for block in plan["blocks"]))
        self.assertIn("VISUAL_CLIP_DIRECTOR", [agent["name"] for agent in plan["agents"]])
        self.assertEqual(plan["visual_clip_contract"]["generic_filler_clips"], "BLOCK")
        self.assertEqual(plan["runflow_handoff"], "BLOCKED_UNTIL_ALL_BLOCK_REVIEWERS_PASS")

    def test_flow_blocks_when_a_reviewer_is_missing(self):
        receipts = {
            "blocks": {
                block["block_id"]: {
                    "analyst_status": "PASS",
                    "reviewer_status": "PASS",
                }
                for block in PRODUCTION_BLOCKS
            }
        }
        receipts["blocks"][PRODUCTION_BLOCKS[3]["block_id"]]["reviewer_status"] = "BLOCKED"
        report = validate_flow_receipts(receipts)
        self.assertEqual(report["status"], "FLOW_BLOCKED")
        self.assertIn(PRODUCTION_BLOCKS[3]["block_id"], report["failed_blocks"])

    def test_flow_passes_only_when_all_pairs_pass(self):
        receipts = {
            "blocks": {
                block["block_id"]: {
                    "analyst_status": "PASS",
                    "reviewer_status": "PASS",
                }
                for block in PRODUCTION_BLOCKS
            }
        }
        report = validate_flow_receipts(receipts)
        self.assertEqual(report["status"], "FLOW_PASS")
        self.assertEqual(report["runflow_handoff"], "READY_FOR_RUNFLOW_PREPARATION_GATE")


if __name__ == "__main__":
    unittest.main()

