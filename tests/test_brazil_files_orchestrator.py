import unittest

from production.brazil_files_orchestrator import (
    AGENT_PIPELINE,
    PRODUCTION_BLOCKS,
    build_preparation_plan,
    validate_case_brief,
    validate_clip_selection_dossier,
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


def valid_clip_dossier():
    representation_types = (
        ["EVIDENCE_OR_ARCHIVE"] * 5
        + ["BRAZILIAN_REAL_WORLD"] * 5
        + ["FACELESS_REENACTMENT"] * 5
        + ["CTA"]
    )
    beats = []
    for index, representation_type in enumerate(representation_types, start=1):
        candidate_count = 1 if representation_type == "CTA" else 3
        candidates = []
        for candidate_index in range(candidate_count):
            selected = candidate_index == 0
            candidates.append({
                "candidate_id": f"candidate-{index:02d}-{candidate_index + 1}",
                "source_url": f"https://example.com/{index}/{candidate_index + 1}",
                "license": "verified editorial license",
                "fingerprint": f"sha256-{index:02d}-{candidate_index + 1}",
                "rights_status": "VERIFIED",
                "decision": "SELECTED" if selected else "REJECTED",
                "rejection_reason": None if selected else "weaker semantic match",
            })
        beat = {
            "beat_id": f"S{index:02d}",
            "script_excerpt": f"Narration beat {index}",
            "narrative_function": "escalation",
            "representation_type": representation_type,
            "visual_anchor": f"direct visual anchor {index}",
            "location": "Varginha, Minas Gerais",
            "era": "1996",
            "camera": {"language": "CONTROLLED_REALISTIC", "movement": "slow push-in"},
            "continuity": {
                "previous_link": "same location and light",
                "next_link": "same location and light",
                "light": "overcast dusk",
                "mood": "investigative dread",
            },
            "candidates": candidates,
            "selected_candidate": candidates[0],
            "rejection_log": [
                {"candidate_id": item["candidate_id"], "reason": item["rejection_reason"]}
                for item in candidates[1:]
            ],
        }
        if representation_type == "FACELESS_REENACTMENT":
            beat["disclosure_label"] = "DRAMATIZED REENACTMENT"
        beats.append(beat)
    return {
        "semantic_match": "DIRECT",
        "source_asset_reuse": "BLOCK_GLOBAL",
        "approval_mode": "AUTOMATIC_FAIL_CLOSED",
        "beats": beats,
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

    def test_clip_dossier_passes_with_approved_contract(self):
        report = validate_clip_selection_dossier(valid_clip_dossier())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["beat_count"], 16)
        self.assertEqual(report["selected_asset_count"], 16)

    def test_clip_dossier_blocks_unverified_selected_candidate(self):
        dossier = valid_clip_dossier()
        dossier["beats"][0]["candidates"][0]["rights_status"] = "UNKNOWN"
        report = validate_clip_selection_dossier(dossier)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("verified rights" in error for error in report["errors"]))

    def test_clip_dossier_blocks_reused_asset_and_missing_disclosure(self):
        dossier = valid_clip_dossier()
        dossier["beats"][1]["selected_candidate"]["fingerprint"] = dossier["beats"][0]["selected_candidate"]["fingerprint"]
        dossier["beats"][10].pop("disclosure_label")
        report = validate_clip_selection_dossier(dossier)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("reused" in error for error in report["errors"]))
        self.assertTrue(any("disclosure" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()

