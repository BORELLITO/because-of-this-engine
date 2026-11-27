import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "production" / "copilot_contract_v1.json"


class CopilotContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_serialization_is_global_and_fail_closed(self):
        serialization = self.contract["serialization"]
        self.assertEqual(serialization["mode"], "GLOBAL_SINGLE_CANONICAL_ENGINE")
        self.assertEqual(serialization["workflow_concurrency_group"], "because-of-this-canonical-engine")
        self.assertFalse(serialization["parallel_production_runs"])
        self.assertFalse(serialization["cancel_in_progress"])
        self.assertTrue(serialization["memory_sync_before_and_after"])
        self.assertEqual(serialization["max_mutating_subagents"], 1)
        self.assertFalse(self.contract["production_activation"]["enabled"])
        self.assertFalse(self.contract["production_activation"]["fallbacks_allowed"])

    def test_subagents_are_ordered_and_cannot_start_engine(self):
        agents = self.contract["subagents"]
        self.assertEqual([agent["order"] for agent in agents], list(range(1, 9)))
        self.assertEqual(len({agent["id"] for agent in agents}), 8)
        self.assertTrue(all(agent["can_start_engine"] is False for agent in agents))

    def test_executor_layer_is_explicit_and_fail_closed(self):
        executor = self.contract["executor_layer"]
        self.assertEqual(executor["mode"], "INJECTED_PROVIDER_REGISTRY")
        self.assertEqual(executor["provider_resolution"], "EXPLICIT_MAPPING_BY_AGENT_ID")
        self.assertEqual(executor["missing_provider"], "BLOCKED")
        self.assertFalse(executor["parallel"])
        self.assertFalse(executor["network_allowed"])
        self.assertFalse(executor["can_start_engine"])
\n    def test_two_execution_levels_are_explicit_and_ordered(self):
        levels = self.contract["levels"]
        self.assertEqual(self.contract["level_order"], ["specialized_analysis", "copilot_technical_gate"])
        self.assertEqual(levels["analysis"]["level"], 1)
        self.assertFalse(levels["analysis"]["parallel"])
        self.assertEqual(levels["technical_gate"]["level"], 2)
        self.assertEqual(levels["technical_gate"]["workflow"], ".github/workflows/copilot-technical-gate.yml")
        self.assertIn("privacy", levels["technical_gate"]["consolidates"])
        self.assertFalse(levels["technical_gate"]["can_start_engine"])

    def test_output_contract_is_explicit(self):
        required = set(self.contract["required_output_fields"])
        self.assertTrue({"agent_id", "status", "evidence", "output_sha256", "next_gate"} <= required)
        self.assertEqual(self.contract["allowed_statuses"], ["PASS", "EDIT", "BLOCKED", "FAIL"])


if __name__ == "__main__":
    unittest.main()
