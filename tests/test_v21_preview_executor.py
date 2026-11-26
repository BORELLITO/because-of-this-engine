import unittest

from production.render_v21_preview import PreviewRenderError, build_scene_plan, parse_range


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

    def test_scene_plan_hydrates_missing_asset_continuity_from_assignment(self) -> None:
        scene_manifest = {
            "assets": [
                {"candidate_id": f"asset-{index}", "sha256": "a" * 64}
                for index in range(16)
            ],
            "shot_assignments": [
                {
                    "shot_id": f"S{index + 1:02d}",
                    "assignment": {
                        "candidate_id": f"asset-{index}",
                        "continuity_tags": {"era": ["1983"]},
                    },
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
        self.assertEqual(plan[3]["asset"]["continuity_tags"], {"era": ["1983"]})

    def test_scene_plan_preserves_existing_asset_continuity(self) -> None:
        asset_tags = {"era": ["asset_declared"]}
        scene_manifest = {
            "assets": [
                {
                    "candidate_id": f"asset-{index}",
                    "sha256": "a" * 64,
                    **({"continuity_tags": asset_tags} if index == 0 else {}),
                }
                for index in range(16)
            ],
            "shot_assignments": [
                {
                    "shot_id": f"S{index + 1:02d}",
                    "assignment": {
                        "candidate_id": f"asset-{index}",
                        "continuity_tags": {"era": ["assignment_declared"]},
                    },
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
        self.assertEqual(plan[0]["asset"]["continuity_tags"], asset_tags)


if __name__ == "__main__":
    unittest.main()
