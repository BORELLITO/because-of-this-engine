import unittest

from production.copilot_analysis_agents_v1 import AGENT_ORDER, AnalysisContractError
from production.copilot_provider_readiness_v1 import (
    ProviderDescriptor,
    RegisteredProvider,
    validate_provider_manifest,
)


def provider(agent_id, fn=None, **overrides):
    descriptor = ProviderDescriptor(
        agent_id=agent_id,
        provider_id=f"test-{agent_id}",
        **overrides,
    )
    return RegisteredProvider(descriptor, fn or (lambda task: {}))


class ProviderReadinessTests(unittest.TestCase):
    def test_complete_manifest_is_ready_without_side_effect_flags(self):
        manifest = {
            agent_id: provider(agent_id)
            for agent_id in AGENT_ORDER
        }
        report = validate_provider_manifest(manifest)
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["configured"], list(AGENT_ORDER))
        self.assertEqual(report["estimated_cost_cents"], 0)

    def test_missing_provider_is_blocked_before_dispatch(self):
        manifest = {AGENT_ORDER[0]: provider(AGENT_ORDER[0])}
        report = validate_provider_manifest(manifest)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["missing"], list(AGENT_ORDER[1:]))

    def test_network_engine_parallel_or_cost_flags_are_rejected(self):
        unsafe_cases = (
            {"network_allowed": True},
            {"can_start_engine": True},
            {"parallel": True},
            {"estimated_cost_cents": 1},
        )
        for overrides in unsafe_cases:
            with self.subTest(overrides=overrides):
                manifest = {
                    AGENT_ORDER[0]: provider(AGENT_ORDER[0], **overrides)
                }
                with self.assertRaises(AnalysisContractError):
                    validate_provider_manifest(manifest)

    def test_unknown_id_and_unwrapped_callable_are_rejected(self):
        with self.assertRaises(AnalysisContractError):
            validate_provider_manifest({"unknown": provider("unknown")})
        with self.assertRaises(AnalysisContractError):
            validate_provider_manifest({AGENT_ORDER[0]: lambda task: {}})


if __name__ == "__main__":
    unittest.main()
