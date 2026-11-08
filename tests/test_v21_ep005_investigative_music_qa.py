"""Offline tests for private EP005 original-Mixkit music discovery and ranking."""
import unittest

from production.ep005_investigative_music_qa import (
    TARGETS, LISTING, LICENSE, VOICE_SHA,
    editorial_score, official_cdn_from_listing,
)
from production.zero_cost_v21 import evaluate_cost

HTML = """
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@id":"Selpan","@type":"MusicRecording","name":"Selpan","genre":"Drone Music",
 "byArtist":"Eugenio Mininni","duration":"PT3M14S",
 "url":"https://assets.mixkit.co/music/612/612.mp3",
 "copyrightNotice":"Mixkit Stock Music Free License"},
{"@id":"Delirium","@type":"MusicRecording","name":"Delirium","genre":"Drone Music",
 "byArtist":"Eugenio Mininni","duration":"PT4M50S",
 "url":"https://assets.mixkit.co/music/605/605.mp3",
 "copyrightNotice":"Mixkit Stock Music Free License"}]}
</script>
"""


class EP005MixkitPrivateAudioTests(unittest.TestCase):
    def test_actual_html_track_binding_not_guessed_url(self):
        for title in TARGETS:
            self.assertEqual(official_cdn_from_listing(HTML,title),TARGETS[title]["url"])
            self.assertTrue(TARGETS[title]["url"].startswith("https://assets.mixkit.co/music/"))

    def test_lawful_listing_but_renamed_track_fails_closed(self):
        wrong=HTML.replace('"name":"Selpan"', '"name":"Unrelated"')
        with self.assertRaises(ValueError):
            official_cdn_from_listing(wrong,"Selpan")
        changed=HTML.replace("612/612.mp3","99/99.mp3")
        with self.assertRaises(ValueError):
            official_cdn_from_listing(changed,"Selpan")

    def test_forged_domain_or_inaccurate_artist_is_rejected(self):
        forged=HTML.replace("assets.mixkit.co/music/612","assets.mixkit.co.evil.test/music/612")
        with self.assertRaises(ValueError):
            official_cdn_from_listing(forged,"Selpan")
        changed=HTML.replace('"name":"Delirium","genre":"Drone Music",\n "byArtist":"Eugenio Mininni"',
                              '"name":"Delirium","genre":"Drone Music",\n "byArtist":"Imposter"')
        with self.assertRaises(ValueError):
            official_cdn_from_listing(changed,"Delirium")

    def test_story_editorial_ranking_is_reproducible_not_global_license(self):
        self.assertGreater(editorial_score("Selpan"),editorial_score("Delirium"))
        with self.assertRaises(ValueError):
            editorial_score("Silent Descent")
        self.assertEqual(LICENSE,"https://mixkit.co/license/modal/musicFree/")

    def test_both_tracks_cover_full_episode_without_loops(self):
        self.assertGreater(TARGETS["Selpan"]["duration_listed_seconds"],79.34)
        self.assertGreater(TARGETS["Delirium"]["duration_listed_seconds"],79.34)
        self.assertEqual(len(VOICE_SHA),64)

    def test_strict_zero_spend_remains_enforced(self):
        self.assertEqual(evaluate_cost("existing_charon_audio_reuse")["status"],"PASS")
        self.assertEqual(evaluate_cost("gemini_tts_generate_content")["status"],"BLOCKED")
        self.assertEqual(evaluate_cost("paid_stock_purchase")["status"],"BLOCKED")


if __name__ == "__main__":
    unittest.main()
