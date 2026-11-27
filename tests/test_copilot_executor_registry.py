import hashlib
import json
import unittest

from production.copilot_analysis_agents_v1 import AGENT_ORDER
from production.copilot_executor_registry_v1 import (
    SPECIALIZED_ROLE_PROMPTS,
    build_specialized_tasks,
    dispatch_registered,
    registry_status,
)


def artifact_hash(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def result_for(task):
    output = {"agent": task["agent_id"], "executor_role": task["executor_role"]}
    return {
        "agent_id": task["agent_id"],
        "input_revision": task["input_revision"],
        "source_artifacts": task["source_artifacts"],
        "evidence": task["evidence"],
        "status": "PASS",
        "blocking_reasons": [],
        "output_artifact": output,
        "output_sha256": artifact_hash(output),
        "next_gate": "technical_gate",
        "token_budget_used": 1,
        "approval_domain": task["approval_domain"],
        "can_start_engine": False,
    }


class CopilotExecutorRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tasks = build_specialized_tasks(
            input_revision="state-v96",
            source_artifacts=["research.json"],
            evidence=["source-1"],
        )

    def test_tasks_include_distinct_specialized_roles(self):
        self.assertEqual([task["agent_id"] for task in self.tasks], list(AGENT_ORDER))
        self.assertEqual(set(SPECIALIZED_ROLE_PROMPTS), set(AGENT_ORDER))
        self.assertTrue(all(task["network_allowed"] is False for task in self.tasks))
        self.assertTrue(all(task["context_policy"] == "MINIMAL_REFERENCES_ONLY" for task in self.tasks))

    def test_missing_executor_fails_closed_without_calling_provider(self):
        calls = []
        results = dispatch_registered(self.tasks, {})
        self.assertEqual(calls, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "BLOCKED")
        self.assertIn("not configured", results[0]["blocking_reasons"][0])

    def test_registered_executors_run_once_in_canonical_order(self):
        calls = []

        def provider(task):
            calls.append(task["agent_id"])
            return result_for(task)

        executors = {agent_id: provider for agent_id in AGENT_ORDER}
        self.assertEqual(registry_status(executors)["status"], "READY")
        results = dispatch_registered(self.tasks, executors)
        self.assertEqual(calls, list(AGENT_ORDER))
        self.assertEqual(len(results), len(AGENT_ORDER))
        self.assertTrue(all(result["status"] == "PASS" for result in results))

    def test_partial_registry_stops_at_first_unconfigured_role(self):
        calls = []

        def provider(task):
            calls.append(task["agent_id"])
            return result_for(task)

        executors = {AGENT_ORDER[0]: provider, AGENT_ORDER[2]: provider}
        results = dispatch_registered(self.tasks, executors)
        self.assertEqual(calls, [AGENT_ORDER[0]])
        self.assertEqual([result["status"] for result in results], ["PASS", "BLOCKED"])


if __name__ == "__main__":
    unittest.main()
