import json
import unittest
from pathlib import Path

from production.copilot_technical_gate_v1 import contract_failures, scope_failures


ROOT = Path(__file__).resolve().parent


class CopilotLevelTests(unittest.TestCase):
    def test_scope_allowlist_blocks_unrelated_changes(self):
        self.assertEqual(scope_failures(["production/copilot_queue_v1.py"]), [])
        self.assertEqual(scope_failures(["production/render_v21_final.py"]), ["production/render_v21_final.py"])

    def test_contract_requires_two_levels_and_disabled_production(self):
        contract = {
            "serialization": {
                "mode": "GLOBAL_SINGLE_CANONICAL_ENGINE",
                "workflow_concurrency_group": "because-of-this-canonical-engine",
                "parallel_production_runs": False,
                "cancel_in_progress": False,
                "memory_sync_before_and_after": True,
                "max_mutating_subagents": 1,
                "subagent_dispatch": "SEQUENTIAL_ISOLATED_ARTIFACT",
            },
            "production_activation": {"enabled": False, "fallbacks_allowed": False},
            "executor_layer": {
                "module": "production/copilot_executor_registry_v1.py",
                "mode": "INJECTED_PROVIDER_REGISTRY",
                "provider_resolution": "EXPLICIT_MAPPING_BY_AGENT_ID",
                "missing_provider": "BLOCKED",
                "parallel": False,
                "network_allowed": False,
                "can_start_engine": False,
                "production_activation": "DISABLED",
            },
            "subagents": [{"can_start_engine": False}] * 8,
            "levels": {"analysis": {}, "technical_gate": {}},
        }
        self.assertEqual(contract_failures(contract), [])


if __name__ == "__main__":
    unittest.main()

