"""Tests for the numbered episode display naming contract."""
import unittest

from production.episode_naming_v21 import validate_episode_naming


class EpisodeNamingTests(unittest.TestCase):
    def test_numbered_display_name_matches_video_title(self):
        result = validate_episode_naming(
            {
                "episode_id": "episode-005",
                "video_title": "THE SIGNAL THAT COULD HAVE STARTED WORLD WAR III",
                "display_name": "05 - THE SIGNAL THAT COULD HAVE STARTED WORLD WAR III",
            }
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "NUMBERED_VIDEO_TITLE")

    def test_wrong_number_is_blocking(self):
        result = validate_episode_naming(
            {
                "episode_id": "episode-005",
                "video_title": "THE SIGNAL THAT COULD HAVE STARTED WORLD WAR III",
                "episode_name": "01 - THE SIGNAL THAT COULD HAVE STARTED WORLD WAR III",
            }
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("display name number does not match episode_id", result["failures"])

    def test_legacy_record_without_fields_is_not_rewritten(self):
        result = validate_episode_naming({"episode_id": "episode-001"})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "NOT_APPLICABLE_LEGACY_OR_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
