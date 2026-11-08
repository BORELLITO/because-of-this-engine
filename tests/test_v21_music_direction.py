"""Strict SINGLE V2.1 soundtrack chooser — no legal rights inferred from labels."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from production.music_direction_v21 import select_soundtrack
from production.audio_mix_receipt_v21 import file_sha256


class MusicDirectorTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root=Path(self.work.name)
        self.ep="episode-test"
        self.story={"episode_id":self.ep,"genre":"historical_mystery",
                    "picture_duration_seconds":70}

    def candidate(self, track_id, tags):
        audio=self.root/(track_id+".wav")
        audio.write_bytes((track_id+"--test-media-").encode()*300)
        digest=file_sha256(audio)
        source_url="https://mixkit.co/free-stock-music/"+track_id+"/"
        license_url="https://mixkit.co/license/modal/musicFree/"
        evidence=self.root/(track_id+"-rights.json")
        evidence.write_text(json.dumps({
            "episode_id":self.ep,
            "provider":"mixkit",
            "source_url":source_url,
            "source_sha256":digest,
            "license_url":license_url,
            "reviewer":"MOTOR_V21_MEDIA_REVIEW",
            "license_review_status":"CLEARED_FOR_THIS_EPISODE",
            "commercial_video_use":True,
            "standalone_distribution":False,
            "platforms":["youtube_shorts","tiktok"],
            "third_party_rights":"CLEARED_FOR_THIS_EDITORIAL_USE",
            "content_id_status":"REVIEWED_NO_KNOWN_UNRESOLVED_CLAIM",
            "source_license_citation":"fixture-archived-license-snapshot",
            "reviewed_on":"2026-11-07",
        }))
        return {
            "track_id":track_id,"tags":tags,
            "provider":"mixkit","contains_siren_or_alarm":False,
            "license_verified":True,"commercial_video_use":True,
            "source_url":source_url,"source_license_url":license_url,
            "license_url":license_url,"local_audio_path":str(audio),
            "rights_evidence_path":str(evidence),
            "rights_evidence_sha256":file_sha256(evidence),
            "sha256":digest,"source_sha256":digest,
            "local_file_verified":True,"acoustic_uniqueness_qa":"VERIFIED",
            "source_duration_seconds":90,
            "lead_vocals":False,"speech_masking_qa":"LOW",
            "music_content_qa_method":"MULTI_SEGMENT_LISTENING_AND_SPECTRAL_REVIEW",
            "music_content_qa_status":"PASS",
            "sparse_arrangement":True,"low_dynamic_range":True,
        }

    def test_story_selects_suspense_not_siren(self):
        alarm=self.candidate("siren",["investigative","siren"])
        quiet=self.candidate("quiet",["investigative","minimal_tension"])
        dark=self.candidate("dark",["dark_ambient"])
        r=select_soundtrack(self.story,[alarm,dark,quiet])
        self.assertEqual(r["selected_track_id"],"quiet",r)
        self.assertEqual(r["selected_audio_sha256"],quiet["sha256"])
        self.assertEqual(r["selected_rights_evidence_sha256"],quiet["rights_evidence_sha256"])
        self.assertIn("siren/alarm",r["rejected"][0]["reasons"][0])
        self.assertFalse(r["publication_authorized"])

    def test_fake_license_domain_is_not_accepted(self):
        track=self.candidate("fake",["investigative"])
        track["license_url"]="https://example.org/free-music-terms"
        self.assertEqual(select_soundtrack(self.story,[track])["status"],"BLOCKED")

    def test_rights_dossier_must_match_exact_source_and_episode(self):
        track=self.candidate("source",["investigative"])
        evidence=Path(track["rights_evidence_path"])
        proof=json.loads(evidence.read_text())
        proof["episode_id"]="unrelated"
        evidence.write_text(json.dumps(proof))
        track["rights_evidence_sha256"]=file_sha256(evidence)
        outcome=select_soundtrack(self.story,[track])
        self.assertEqual(outcome["status"],"BLOCKED")
        self.assertTrue(any("dossier" in e for e in outcome["rejected"][0]["reasons"]))

    def test_content_id_risk_and_modified_evidence_cannot_be_ignored(self):
        track=self.candidate("claimed",["investigative"])
        e=Path(track["rights_evidence_path"])
        proof=json.loads(e.read_text())
        proof["content_id_status"]="UNRESOLVED"
        e.write_text(json.dumps(proof))
        track["rights_evidence_sha256"]=file_sha256(e)
        self.assertEqual(select_soundtrack(self.story,[track])["status"],"BLOCKED")
        track=self.candidate("tampered",["investigative"])
        Path(track["rights_evidence_path"]).write_text("{}")
        self.assertEqual(select_soundtrack(self.story,[track])["status"],"BLOCKED")

    def test_original_audio_bytes_and_runtime_are_enforced(self):
        candidate=self.candidate("short",["investigative"])
        candidate["source_duration_seconds"]=20
        self.assertEqual(select_soundtrack(self.story,[candidate])["status"],"BLOCKED")
        candidate=self.candidate("wrong-sha",["investigative"])
        candidate["sha256"]="0"*64
        self.assertEqual(select_soundtrack(self.story,[candidate])["status"],"BLOCKED")

    def test_requires_real_story_genre_or_track_inventory(self):
        self.assertEqual(select_soundtrack(
            {"episode_id":self.ep,"genre":"unknown","picture_duration_seconds":70},[])["status"],"BLOCKED")
        self.assertEqual(select_soundtrack(self.story,[])["status"],"BLOCKED")

    def test_vocal_or_missing_qa_is_blocked(self):
        candidate=self.candidate("words",["investigative"])
        candidate["lead_vocals"]=True
        self.assertEqual(select_soundtrack(self.story,[candidate])["status"],"BLOCKED")
        candidate=self.candidate("unreviewed",["investigative"])
        candidate["music_content_qa_status"]="PENDING"
        self.assertEqual(select_soundtrack(self.story,[candidate])["status"],"BLOCKED")

if __name__ == "__main__":
    unittest.main()
