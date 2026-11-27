import tempfile
import unittest
from pathlib import Path

from production.copilot_queue_v1 import QueueContractError, claim_next, complete, enqueue, fail_closed, initial_state, read_state, write_state


class CopilotQueueTests(unittest.TestCase):
    def setUp(self):
        self.memory = "state-v90"
        self.policy = "policy-sha"
        self.state = initial_state(memory_revision=self.memory, engine_policy_sha256=self.policy)

    def test_only_one_request_can_be_claimed(self):
        enqueue(self.state, "req-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        enqueue(self.state, "req-2", memory_revision=self.memory, engine_policy_sha256=self.policy)
        claim_next(self.state, "run-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        with self.assertRaisesRegex(QueueContractError, "already active"):
            claim_next(self.state, "run-2", memory_revision=self.memory, engine_policy_sha256=self.policy)
        self.assertEqual(self.state["active_request_id"], "req-1")
        self.assertEqual(self.state["queued_request_ids"], ["req-2"])

    def test_stale_memory_or_policy_fails_closed(self):
        enqueue(self.state, "req-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        with self.assertRaisesRegex(QueueContractError, "memory revision is stale"):
            claim_next(self.state, "run-1", memory_revision="state-old", engine_policy_sha256=self.policy)
        with self.assertRaisesRegex(QueueContractError, "policy hash is stale"):
            claim_next(self.state, "run-1", memory_revision=self.memory, engine_policy_sha256="policy-old")

    def test_duplicate_enqueue_is_idempotent(self):
        enqueue(self.state, "req-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        version = self.state["state_version"]
        enqueue(self.state, "req-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        self.assertEqual(self.state["state_version"], version)
        self.assertEqual(self.state["queued_request_ids"], ["req-1"])

    def test_failed_run_blocks_future_claims_without_deleting_queue(self):
        enqueue(self.state, "req-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        enqueue(self.state, "req-2", memory_revision=self.memory, engine_policy_sha256=self.policy)
        claim_next(self.state, "run-1", memory_revision=self.memory, engine_policy_sha256=self.policy)
        complete(self.state, "run-1", memory_revision=self.memory, engine_policy_sha256=self.policy, success=False)
        self.assertEqual(self.state["status"], "FAIL_CLOSED")
        self.assertEqual(self.state["queued_request_ids"], ["req-2"])
        with self.assertRaisesRegex(QueueContractError, "fail-closed"):
            claim_next(self.state, "run-2", memory_revision=self.memory, engine_policy_sha256=self.policy)

    def test_state_write_is_atomic_and_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            write_state(path, self.state)
            self.assertEqual(read_state(path), self.state)


if __name__ == "__main__":
    unittest.main()

