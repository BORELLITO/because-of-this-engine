import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SingleEnginePolicyTests(unittest.TestCase):
    def test_policy_requires_global_single_engine_lane_and_memory_sync(self):
        policy = json.loads((ROOT / "production" / "active_engine_policy.json").read_text(encoding="utf-8"))
        serialization = policy["execution_serialization"]
        self.assertEqual(serialization["mode"], "GLOBAL_SINGLE_CANONICAL_ENGINE")
        self.assertEqual(serialization["concurrency_group"], "because-of-this-canonical-engine")
        self.assertFalse(serialization["cancel_in_progress"])
        self.assertFalse(serialization["parallel_engine_runs"])
        self.assertTrue(serialization["memory_sync_required_before_and_after"])
        self.assertEqual(serialization["canonical_state_file"], "ESTADO_ATUAL.md")

    def test_runflow_uses_global_lock_without_cancellation(self):
        text = (ROOT / ".github" / "workflows" / "because-of-this-runflow.yml").read_text(encoding="utf-8")
        self.assertIn("group: because-of-this-canonical-engine", text)
        self.assertIn("cancel-in-progress: false", text)


if __name__ == "__main__":
    unittest.main()
