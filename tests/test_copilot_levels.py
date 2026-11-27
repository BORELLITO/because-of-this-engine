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
        contract["brazil_files_crosswalk"] = {
            "module": "production/brazil_files_canonical_crosswalk_v1.py",
            "source_checkpoint_count": 22,
            "canonical_agent_count": 8,
            "execution_mode": "SEQUENTIAL_REUSE_CANONICAL_AGENT",
            "parallel": False,
            "secondary_engine": False,
            "terminal_agent": "delivery_agent",
        }
        contract["runflow_handoff"] = {
            "module": "production/copilot_runflow_handoff_v1.py",
            "requires": [
                "queue_engine_queue",
                "eight_analysis_receipts_pass",
                "brazil_files_crosswalk_pass",
                "current_memory_and_policy",
            ],
            "dispatch": "MANUAL_OR_SEPARATE_AUTHORIZED_WORKFLOW",
            "parallel": False,
            "can_start_engine": False,
            "production_enabled": False,
        }
        contract["provider_readiness"] = {
            "module": "production/copilot_provider_readiness_v1.py",
            "metadata": "EXPLICIT_REGISTERED_PROVIDER",
            "preflight_before_dispatch": True,
            "network_allowed": False,
            "can_start_engine": False,
            "parallel": False,
            "estimated_cost_cents": 0,
            "missing_provider": "BLOCKED",
            "unsafe_manifest": "FAIL_CLOSED",
        }
        self.assertEqual(contract_failures(contract), [])

    def test_level_one_declares_all_eight_executable_roles(self):
        contract = json.loads((ROOT / ".." / "production" / "copilot_contract_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(len(contract["levels"]["analysis"]["agents"]), 8)
        self.assertEqual(contract["levels"]["analysis"]["agents"], [
            "research_analyst",
            "factual_reviewer",
            "story_editorial_agent",
            "rights_provenance_agent",
            "visual_continuity_agent",
            "timeline_caption_agent",
            "qa_release_reviewer",
            "delivery_agent",
        ])
        self.assertFalse(contract["levels"]["analysis"]["parallel"])
        self.assertFalse(contract["levels"]["analysis"]["can_start_engine"])


if __name__ == "__main__":
    unittest.main()

