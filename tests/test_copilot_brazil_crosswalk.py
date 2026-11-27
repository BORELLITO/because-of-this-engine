import unittest

from production.brazil_files_canonical_crosswalk_v1 import (
    BRAZIL_FILES_ROLE_CROSSWALK,
    CANONICAL_AGENT_IDS,
    TERMINAL_HANDOFF,
    canonical_agent_for,
    validate_crosswalk,
)


class BrazilFilesCanonicalCrosswalkTests(unittest.TestCase):
    def test_22_checkpoints_map_to_one_sequential_lane(self):
        report = validate_crosswalk()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["source_checkpoint_count"], 22)
        self.assertEqual(report["canonical_agent_count"], 8)
        self.assertEqual(report["execution_mode"], "SEQUENTIAL_REUSE_CANONICAL_AGENT")
        self.assertFalse(report["parallel_allowed"])
        self.assertFalse(report["secondary_engine_allowed"])

    def test_all_canonical_capabilities_are_represented(self):
        mapped = {row["canonical_agent"] for row in BRAZIL_FILES_ROLE_CROSSWALK}
        self.assertEqual(mapped | {TERMINAL_HANDOFF["canonical_agent"]}, set(CANONICAL_AGENT_IDS))
        self.assertNotIn("delivery_agent", mapped)

    def test_terminal_delivery_requires_all_receipts(self):
        self.assertEqual(TERMINAL_HANDOFF["canonical_agent"], "delivery_agent")
        self.assertEqual(TERMINAL_HANDOFF["after_order"], 22)
        self.assertEqual(TERMINAL_HANDOFF["requires"], "ALL_BRAZIL_FILES_CHECKPOINTS_PASS")

    def test_source_roles_resolve_without_new_agents(self):
        self.assertEqual(canonical_agent_for("CASE_RESEARCH"), "research_analyst")
        self.assertEqual(canonical_agent_for("VISUAL_CLIP_DIRECTOR"), "visual_continuity_agent")
        self.assertEqual(canonical_agent_for("RED_TEAM_REVIEW"), "qa_release_reviewer")

    def test_drift_blocks_duplicate_or_invalid_checkpoint(self):
        drifted = list(BRAZIL_FILES_ROLE_CROSSWALK)
        drifted[0] = dict(drifted[0], source_role=drifted[1]["source_role"])
        report = validate_crosswalk(tuple(drifted))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("unique" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
