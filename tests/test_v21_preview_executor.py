import unittest

from v21_render_preview import PreviewRenderError, build_scene_plan, parse_range


class V21PreviewExecutorTests(unittest.TestCase):
    def test_parse_range(self) -> None:
        self.assertEqual(parse_range("01:06-01:12"), (66.0, 72.0))

    def test_parse_range_rejects_reverse_range(self) -> None:
        with self.assertRaises(PreviewRenderError):
            parse_range("00:10-00:09")

    def test_scene_plan_requires_distinct_assignments(self) -> None:
        scene_manifest = {
            "assets": [
                {"candidate_id": f"asset-{index}", "sha256": "a" * 64}
                for index in range(16)
            ],
            "shot_assignments": [
                {
                    "shot_id": f"S{index + 1:02d}",
                    "assignment": {"candidate_id": f"asset-{index}"},
                }
                for index in range(16)
            ],
        }
        story = {
            "shot_plan": [
                {"shot_id": f"S{index + 1:02d}", "range": f"00:{index:02d}-00:{index + 1:02d}"}
                for index in range(16)
            ]
        }
        plan = build_scene_plan(scene_manifest, story)
        self.assertEqual(len(plan), 16)
        self.assertEqual(len({item["candidate_id"] for item in plan}), 16)


if __name__ == "__main__":
    unittest.main()
