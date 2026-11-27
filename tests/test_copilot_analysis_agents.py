import hashlib
import json
import unittest

from production.copilot_analysis_agents_v1 import (
    AGENT_ORDER,
    AnalysisContractError,
    build_task,
    dispatch_sequential,
    validate_result,
)


def artifact_hash(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def result_for(task, status="PASS"):
    output = {"agent": task["agent_id"], "status": status}
    return {
        "agent_id": task["agent_id"],
        "input_revision": task["input_revision"],
        "source_artifacts": task["source_artifacts"],
        "evidence": task["evidence"],
        "status": status,
        "blocking_reasons": [],
        "output_artifact": output,
        "output_sha256": artifact_hash(output),
        "next_gate": "technical_gate" if status == "PASS" else "review",
        "token_budget_used": 1,
        "approval_domain": task["approval_domain"],
        "can_start_engine": False,
    }


class CopilotAnalysisAgentTests(unittest.TestCase):
    def test_tasks_are_declared_in_canonical_order(self):
        tasks = [build_task(agent_id, input_revision="r1", source_artifacts=[], evidence=[]) for agent_id in AGENT_ORDER]
        self.assertEqual([task["agent_id"] for task in tasks], list(AGENT_ORDER))
        self.assertTrue(all(task["parallel"] is False and task["can_start_engine"] is False for task in tasks))

    def test_dispatch_is_sequential_and_stops_on_block(self):
        calls = []
        tasks = [build_task(agent_id, input_revision="r1", source_artifacts=[], evidence=[]) for agent_id in AGENT_ORDER]

        def executor(task):
            calls.append(task["agent_id"])
            return result_for(task, "BLOCKED" if len(calls) == 2 else "PASS")

        results = dispatch_sequential(tasks, executor)
        self.assertEqual(calls, list(AGENT_ORDER[:2]))
        self.assertEqual([result["status"] for result in results], ["PASS", "BLOCKED"])

    def test_invalid_hash_and_engine_control_are_rejected(self):
        task = build_task(AGENT_ORDER[0], input_revision="r1", source_artifacts=[], evidence=[])
        result = result_for(task)
        result["output_sha256"] = "bad"
        with self.assertRaises(AnalysisContractError):
            validate_result(result, expected_agent_id=AGENT_ORDER[0])
        result = result_for(task)
        result["can_start_engine"] = True
        with self.assertRaises(AnalysisContractError):
            validate_result(result, expected_agent_id=AGENT_ORDER[0])

    def test_wrong_task_order_is_rejected(self):
        tasks = [build_task(agent_id, input_revision="r1", source_artifacts=[], evidence=[]) for agent_id in AGENT_ORDER[::-1]]
        with self.assertRaises(AnalysisContractError):
            dispatch_sequential(tasks, lambda task: result_for(task))


if __name__ == "__main__":
    unittest.main()
