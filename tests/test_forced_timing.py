import unittest

from production.render_video_episode import narration_locked_scenes


class ForcedTimingRenderTests(unittest.TestCase):
    def test_scene_durations_follow_audio_spans_and_transition_overlap(self):
        scenes = [
            {"scene_id": "S01", "duration": 15, "transition": {"type": "hard_cut", "duration": 0}},
            {"scene_id": "S02", "duration": 15, "transition": {"type": "crossfade", "duration": 0.25}},
            {"scene_id": "S03", "duration": 15, "transition": {"type": "crossfade", "duration": 0.25}},
            {"scene_id": "S04", "duration": 15, "transition": {"type": "crossfade", "duration": 0.25}},
        ]
        spans = [
            {"scene_id": "S01", "audio_start": 0.0, "audio_end": 14.0},
            {"scene_id": "S02", "audio_start": 16.0, "audio_end": 29.0},
            {"scene_id": "S03", "audio_start": 31.0, "audio_end": 44.0},
            {"scene_id": "S04", "audio_start": 46.0, "audio_end": 60.0},
        ]
        locked = narration_locked_scenes(scenes, 60.0, narration_spans=spans)
        self.assertAlmostEqual(
            sum(item["duration"] for item in locked) - (0.25 * 3),
            60.0,
            places=5,
        )
        self.assertEqual(locked[0]["narration_span"]["audio_start"], 0.0)
        self.assertEqual(locked[-1]["narration_span"]["audio_end"], 60.0)

    def test_scene_order_mismatch_blocks_forced_timing(self):
        scenes = [
            {"scene_id": "S01", "duration": 30},
            {"scene_id": "S02", "duration": 30},
        ]
        spans = [
            {"scene_id": "S02", "audio_start": 0.0, "audio_end": 30.0},
            {"scene_id": "S01", "audio_start": 30.0, "audio_end": 60.0},
        ]
        with self.assertRaisesRegex(RuntimeError, "scene order mismatch"):
            narration_locked_scenes(scenes, 60.0, narration_spans=spans)


if __name__ == "__main__":
    unittest.main()
