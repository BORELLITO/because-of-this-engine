import unittest

from production.stock_video_research import (
    SceneQuery,
    ResearchError,
    _scene_query,
    research,
    score_candidate,
)


class StockVideoResearchTests(unittest.TestCase):
    def test_scene_query_is_derived_from_story_beat(self):
        scene = {
            "scene_id": "S04",
            "duration": 9.4,
            "story_beat": "a conversion error sends the spacecraft toward the wrong trajectory",
            "visual_intent": "turn the unit error into a point of no return",
            "visual_function": "reveal",
        }
        query = _scene_query(scene)
        self.assertIn("conversion", query.query)
        self.assertIn("trajectory", query.query)
        self.assertNotIn("the", query.query)

    def test_score_prefers_matching_vertical_candidate(self):
        scene = SceneQuery(
            scene_id="S01",
            query="spacecraft journey mars",
            duration=8.0,
            visual_function="establishing",
            visual_intent="show the long journey to Mars",
        )
        matching = {
            "provider": "nasa",
            "title": "Mars spacecraft journey",
            "description": "spacecraft travels toward Mars",
            "tags": "mars spacecraft journey",
            "duration_seconds": 12,
            "width": 1080,
            "height": 1920,
        }
        weak = {
            "provider": "pixabay",
            "title": "city traffic",
            "description": "",
            "tags": "street cars",
            "duration_seconds": 2,
            "width": 1920,
            "height": 1080,
        }
        self.assertGreater(score_candidate(matching, scene), score_candidate(weak, scene))

    def test_research_never_auto_approves(self):
        manifest = {
            "video_id": "test-001",
            "scenes": [{
                "scene_id": "S01",
                "duration": 6,
                "story_beat": "spacecraft journey",
                "visual_intent": "establish scale",
            }],
        }
        result = research(
            manifest,
            provider="nasa",
            searchers={"nasa": lambda query, limit: [{
                "provider": "nasa",
                "candidate_id": "N1",
                "title": "Spacecraft journey",
                "description": "",
                "tags": "spacecraft journey",
                "source_page_url": "https://images.nasa.gov/details/N1",
                "download_url": "https://example.invalid/N1.mp4",
                "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
                "license": "NASA_MEDIA_GUIDELINES_REVIEW",
                "rights_status": "REVIEW_REQUIRED",
                "approved_for_render": False,
                "duration_seconds": 8,
                "width": 1080,
                "height": 1920,
            }]},
        )
        candidate = result["scenes"][0]["candidates"][0]
        self.assertEqual(result["scenes"][0]["approval_status"], "REVIEW_REQUIRED")
        self.assertFalse(candidate["approved_for_render"])

    def test_missing_story_language_is_blocked(self):
        with self.assertRaises(ResearchError):
            _scene_query({"scene_id": "S01", "duration": 4})


if __name__ == "__main__":
    unittest.main()
