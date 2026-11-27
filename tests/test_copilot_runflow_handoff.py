import unittest

from production.copilot_analysis_agents_v1 import AGENT_ORDER
from production.copilot_queue_v1 import enqueue, initial_state
from production.copilot_runflow_handoff_v1 import (
    HANDOFF_STATUS,
    validate_runflow_handoff,
)


class CopilotRunflowHandoffTests(unittest.TestCase):
    def setUp(self):
        self.memory = "state-v91"
        self.policy = "policy-sha"
        self.state = initial_state(memory_revision=self.memory, engine_policy_sha256=self.policy)
        enqueue(self.state, "req-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        self.results = [
            {
                "agent_id": agent_id,
                "status": "PASS",
                "output_sha256": f"sha-{index}",
                "can_start_engine": False,
            }
            for index, agent_id in enumerate(AGENT_ORDER, start=1)
        ]

    def test_valid_queue_and_receipts_prepare_read_only_handoff(self):
        report = validate_runflow_handoff(
            self.state,
            self.results,
            memory_revision=self.memory,
            engine_policy_sha256=self.policy,
        )
        self.assertEqual(report["status"], HANDOFF_STATUS)
        self.assertEqual(report["receipt_count"], 8)
        self.assertFalse(report["production_started"])
        self.assertFalse(report["can_start_engine"])
        self.assertFalse(report["parallel"])
        self.assertEqual(self.state["status"], "ENGINE_QUEUE")

    def test_active_run_is_blocked_before_dispatch(self):
        self.state["status"] = "ENGINE_RUNNING"
        self.state["active_run_id"] = "run-1"
        self.state["active_request_id"] = "req-1"
        self.state["queued_request_ids"] = []
        report = validate_runflow_handoff(
            self.state,
            self.results,
            memory_revision=self.memory,
            engine_policy_sha256=self.policy,
        )
        self.assertEqual(report["status"], "RUNFLOW_HANDOFF_BLOCKED")
        self.assertTrue(any("active run" in error for error in report["errors"]))

    def test_missing_or_reordered_receipt_blocks(self):
        report = validate_runflow_handoff(
            self.state,
            self.results[:-1],
            memory_revision=self.memory,
            engine_policy_sha256=self.policy,
        )
        self.assertEqual(report["status"], "RUNFLOW_HANDOFF_BLOCKED")
        self.assertTrue(any("exactly 8" in error for error in report["errors"]))

        reordered = list(reversed(self.results))
        report = validate_runflow_handoff(
            self.state,
            reordered,
            memory_revision=self.memory,
            engine_policy_sha256=self.policy,
        )
        self.assertTrue(any("eight-agent order" in error for error in report["errors"]))

    def test_stale_context_and_unsafe_receipt_block(self):
        unsafe = list(self.results)
        unsafe[0] = dict(unsafe[0], can_start_engine=True)
        report = validate_runflow_handoff(
            self.state,
            unsafe,
            memory_revision="state-old",
            engine_policy_sha256=self.policy,
        )
        self.assertEqual(report["status"], "RUNFLOW_HANDOFF_BLOCKED")
        self.assertTrue(any("stale" in error for error in report["errors"]))
        self.assertTrue(any("may not start" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
