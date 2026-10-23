import unittest

from production.motion_engine import (
    normalize_motion,
    normalize_transition,
    validate_motion_sequence,
)


class MotionEngineTests(unittest.TestCase):
    def test_contextual_motion_is_deterministic(self):
        scene = {"scene_id": "S01", "story_beat": "establish context and scale"}
        first = normalize_motion(scene, 0)
        second = normalize_motion(scene, 0)
        self.assertEqual(first, second)
        self.assertEqual(first["type"], "slow_pull_out")

    def test_repetition_guard_changes_the_next_motion(self):
        scene = {"scene_id": "S02", "story_beat": "consequence reveal"}
        value = normalize_motion(scene, 1, "slow_push_in")
        self.assertNotEqual(value["type"], "slow_push_in")

    def test_invalid_easing_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_motion({"scene_id": "S01", "motion": {"type": "static_hold", "easing": "random"}}, 0)

    def test_transition_default_is_context_safe(self):
        value = normalize_transition({"scene_id": "S02"}, 0.33, 1)
        self.assertEqual(value, {"type": "crossfade", "duration": 0.33})

    def test_three_identical_motions_are_a_gate_failure(self):
        scenes = [{"motion": {"type": "static_hold"}}] * 3
        self.assertTrue(validate_motion_sequence(scenes))


if __name__ == "__main__":
    unittest.main()
