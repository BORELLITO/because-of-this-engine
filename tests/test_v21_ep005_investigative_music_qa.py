"""Offline tests for private EP005 original-Mixkit music discovery and ranking."""
import unittest
import json
from pathlib import Path

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

    def test_archived_real_qa_report_is_not_forged_as_release(self):
        root=Path(__file__).resolve().parents[1]
        report=json.loads((root/"reports/EP005_MIXKIT_INVESTIGATIVE_HEAD_TO_HEAD_QA_20261108.json").read_text())
        self.assertEqual(report["evidence_workflow"]["conclusion"],"success")
        self.assertEqual(report["evidence_workflow"]["run_id"],42494029735)
        self.assertEqual(report["status"],"PRIVATE_HEAD_TO_HEAD_TECHNICAL_PASS_RELEASE_BLOCKED")
        self.assertEqual(report["total_incremental_spend_usd"],0)
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["production_enablement"])
        self.assertEqual(report["approved_voice"]["new_tts_requests"],0)
        self.assertEqual(report["mix"]["source_ids_compared"],5)
        candidates={x["title"]:x for x in report["candidates"]}
        self.assertEqual(len(candidates),2)
        self.assertEqual(candidates["Selpan"]["source_sha256"],
                         "3d46ec4a1572e00a7da4b3e697067c7cbb07331bc5837758985ff95eda858267")
        self.assertEqual(candidates["Delirium"]["source_sha256"],
                         "c5b38b0191bada42aaaac2330e5de875409d9d9423cb3fd4804b0b69f4cb69e4")
        for candidate in candidates.values():
            self.assertEqual(candidate["technical_verdict"],"PASS")
            self.assertIn("PENDING",candidate["release_verdict"])
            self.assertLess(candidate["true_peak_dbTP"],-1)
            self.assertLess(candidate["near_black_rms"],candidate["early_outro_rms"]*0.2)
        self.assertEqual(report["provisional_director_choice"]["title"],"Selpan")
        self.assertIn("PROVISIONAL",report["provisional_director_choice"]["status"])
        self.assertIn("PLATFORM_CONTENT_ID_UNKNOWN",report["unresolved"])

    def test_selpan_is_active_qa_candidate_and_silent_descent_is_preserved(self):
        root = Path(__file__).resolve().parents[1]
        current=json.loads((root/"episodes/episode-005/music-clearance-v21.json").read_text())
        archived=json.loads((root/"episodes/episode-005/music-clearance-silent-descent-archive-v21.json").read_text())
        report=json.loads((root/"reports/EP005_MIXKIT_INVESTIGATIVE_HEAD_TO_HEAD_QA_20261108.json").read_text())
        self.assertEqual(current["title"],"Selpan")
        self.assertEqual(current["source_sha256"],report["candidates"][0]["source_sha256"])
        self.assertEqual(current["source_evidence"]["qa_workflow_run_id"],42494029735)
        self.assertFalse(current["decision"]["publication_authorized"])
        self.assertEqual(current["decision"]["status"],
                         "HOLD_FOR_QUALIFIED_SOURCE_AUDITION_AND_CONTENT_ID")
        self.assertEqual(current["content_id"]["status"],"UNKNOWN_NOT_CHECKED_ON_DESTINATION_PLATFORM")
        self.assertEqual(archived["title"],"Silent Descent")
        self.assertEqual(archived["source_sha256"],
                         "601955cacab6c38417687b144754c914f392f6508c35c241372695ad3987ec2b")

    def test_strict_zero_spend_remains_enforced(self):
        self.assertEqual(evaluate_cost("existing_charon_audio_reuse")["status"],"PASS")
        self.assertEqual(evaluate_cost("gemini_tts_generate_content")["status"],"BLOCKED")
        self.assertEqual(evaluate_cost("paid_stock_purchase")["status"],"BLOCKED")


if __name__ == "__main__":
    unittest.main()
