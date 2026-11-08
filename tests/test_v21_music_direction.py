import unittest
from production.music_direction_v21 import select_soundtrack

def candidate(track_id, tags):
    return {
        "track_id":track_id,"tags":tags,"contains_siren_or_alarm":False,
        "license_verified":True,"commercial_video_use":True,
        "modification_allowed":True,"item_license_evidence":"VERIFIED",
        "license_url":"https://example.org/terms","source_url":"https://example.org/track",
        "content_id_risk_review":"VERIFIED",
        "local_file_verified":True,"acoustic_uniqueness_qa":"VERIFIED",
        "source_duration_seconds":90,"sparse_arrangement":True,
        "low_dynamic_range":True,
    }

class MusicDirectorTests(unittest.TestCase):
    def test_story_selects_suspense_not_siren(self):
        alarm=candidate("siren",["investigative","siren"])
        quiet=candidate("quiet",["investigative","minimal_tension"])
        dark=candidate("dark",["dark_ambient"])
        r=select_soundtrack({"genre":"historical_mystery","picture_duration_seconds":70},
                            [alarm,dark,quiet])
        self.assertEqual(r["selected_track_id"],"quiet")
        self.assertFalse(r["publication_authorized"])
        self.assertIn("siren/alarm",r["rejected"][0]["reasons"][0])

    def test_rights_not_inferred_from_royalty_free_label(self):
        c=candidate("fake",["psychological_suspense"])
        c["item_license_evidence"]="PENDING"
        r=select_soundtrack({"genre":"psychological_horror","picture_duration_seconds":72},[c])
        self.assertEqual(r["status"],"BLOCKED")

    def test_content_id_and_reuse_fail_closed(self):
        c=candidate("claimed",["dark_ambient"])
        c["content_id_risk_review"]="PENDING"
        self.assertEqual(select_soundtrack(
            {"genre":"supernatural","picture_duration_seconds":72},[c])["status"],"BLOCKED")
        c["content_id_risk_review"]="VERIFIED"
        c["acoustic_uniqueness_qa"]="PENDING"
        self.assertEqual(select_soundtrack(
            {"genre":"supernatural","picture_duration_seconds":72},[c])["status"],"BLOCKED")

    def test_missing_genre_or_runtime_blocks(self):
        self.assertEqual(select_soundtrack(
            {"genre":"unknown","picture_duration_seconds":70},[])["status"],"BLOCKED")
        self.assertEqual(select_soundtrack(
            {"genre":"true_story","picture_duration_seconds":90},[])["status"],"BLOCKED")

if __name__=="__main__":
    unittest.main()
