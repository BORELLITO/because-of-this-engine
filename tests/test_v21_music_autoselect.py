"""Motor, not owner, selects story-fitting legal background music.

These test dossiers are SYNTHETIC fixtures, not real music licenses.
A patched historic catalog gate only isolates ranking/rights decisions.
Real file/Chromaprint checks stay mandatory in the production engine.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from production.music_autoselect_v21 import select_for_story, evaluate_one
from production.audio_mix_receipt_v21 import file_sha256

HAS_FFPROBE=bool(shutil.which("ffprobe"))


@unittest.skipUnless(HAS_FFPROBE,"real ffprobe needed to inspect fixture song durations")
class StoryMusicAutoselectTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root=Path(self.dir.name)
        self.episode="episode-fixture"
        self.story={"tension_arc":"slow_burn",
                    "mood_tags":["psychological_suspense","dark_ambient","low_drone"]}
        self.candidates=[
            self.make_candidate("music-a",277.0,
                                ["psychological_suspense","dark_ambient","low_drone"],
                                "slow_burn"),
            self.make_candidate("music-b",323.0,
                                ["psychological_suspense","cinematic_tension"],
                                "investigation"),
        ]
        self.patcher=patch("production.music_autoselect_v21.check_file",
                           return_value={"status":"PASS","failures":[]})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def make_candidate(self, name, frequency, tags, arc):
        local=self.root/(name+".wav")
        sr=8000
        with wave.open(str(local),"wb") as w:
            w.setframerate(sr);w.setnchannels(1);w.setsampwidth(2)
            w.writeframes(b"".join(struct.pack(
                "<h",int(5000*math.sin(2*math.pi*frequency*i/sr)))
                for i in range(15*sr)))
        source_sha=file_sha256(local)
        item="https://mixkit.co/free-stock-music/ambient/"+name+"/"
        evidence=self.root/(name+"-rights.json")
        rights={
            "provider":"mixkit","item_url":item,
            "source_sha256":source_sha,
            "license_terms_url":"https://mixkit.co/license/modal/musicFree/",
            "rights_reviewer":"MOTOR_V21_SOURCE_REVIEW",
            "commercial_video_use":True,
            "platform_scope":["youtube_shorts","tiktok"],
            "standalone_distribution":False,
            "third_party_rights":"CLEARED_FOR_THIS_EDITORIAL_USAGE",
            "content_id_review":"NO_KNOWN_MATCH",
            "episode_id":self.episode,
            "usage_scope":"BACKGROUND_MUSIC_IN_EPISODE_ONLY",
            "license_checked_on":"2026-11-07",
            "rights_evidence_refs":["fixture-provider-item-snapshot"],
        }
        evidence.write_text(json.dumps(rights))
        return {
            "candidate_id":name,"episode_id":self.episode,
            "provider":"mixkit","title":name,"artist":"fixture-author",
            "kind":"music_bed","local_audio_path":str(local),
            "sha256":source_sha,
            "source_item_url":item,
            "source_duration_seconds":15.0,
            "rights_evidence_path":str(evidence),
            "rights_evidence_sha256":file_sha256(evidence),
            "tags":tags,"arc_fit":arc,
            "content_qa":{
                "method":"MULTI_SEGMENT_SOURCE_LISTENING_AND_SPECTRAL_REVIEW",
                "result":"PASS","siren_or_alarm":False,
                "lead_vocals":False,"start_audible":True,
                "speech_masking_risk":"LOW","abrupt_stinger":False,
            },
            "license_verified":True,
            "acoustic_uniqueness_qa":"VERIFIED",
        }

    def choose(self,candidates=None):
        return select_for_story({
            "episode_id":self.episode,"story":self.story,
            "candidates":candidates if candidates is not None else self.candidates,
        },repo_root=self.root,total_seconds=12.0)

    def test_motor_picks_best_story_fit_without_user_choice(self):
        result=self.choose()
        self.assertEqual(result["status"],"AUTO_SELECTED_EVIDENCE_BOUND_V21",result)
        self.assertEqual(result["selected"]["candidate_id"],"music-a")
        self.assertTrue(result["music_through_end_card"])
        self.assertTrue(result["no_sirens"])
        self.assertFalse(result["publication_authorized"])

    def test_siren_always_blocked_even_with_high_mood_score(self):
        items=copy.deepcopy(self.candidates)
        items[0]["tags"].append("siren")
        result=self.choose(items)
        self.assertEqual(result["selected"]["candidate_id"],"music-b")
        blocked=next(d for d in result["decisions"] if d["candidate_id"]=="music-a")
        self.assertTrue(any("siren" in x for x in blocked["reasons"]))

    def test_forged_license_or_content_id_risk_blocks(self):
        candidate=copy.deepcopy(self.candidates[0])
        path=Path(candidate["rights_evidence_path"])
        e=json.loads(path.read_text())
        e["content_id_review"]="UNRESOLVED"
        path.write_text(json.dumps(e))
        candidate["rights_evidence_sha256"]=file_sha256(path)
        result=self.choose([candidate])
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("third-party" in reason for reason
                            in result["decisions"][0]["reasons"]))

    def test_rights_document_mutation_after_hash_must_block(self):
        candidate=copy.deepcopy(self.candidates[0])
        path=Path(candidate["rights_evidence_path"])
        path.write_text(path.read_text()+"altered")
        verdict=self.choose([candidate])
        self.assertEqual(verdict["status"],"BLOCKED")

    def test_unknown_provider_must_block(self):
        items=copy.deepcopy(self.candidates)
        for item in items:
            item["provider"]="unknown-studio"
        self.assertEqual(self.choose(items)["status"],"BLOCKED")

    def test_song_must_cover_entire_end_card(self):
        result=select_for_story({
            "episode_id":self.episode,"story":self.story,
            "candidates":self.candidates[:1],
        },repo_root=self.root,total_seconds=20.5)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("song too short" in x
                            for x in result["decisions"][0]["reasons"]))

    def test_not_even_a_blank_pool_can_substitute_silence(self):
        self.assertEqual(self.choose([])["status"],"BLOCKED")

    def test_duplicate_music_identifiers_fail_closed(self):
        items=[self.candidates[0],self.candidates[0]]
        self.assertEqual(self.choose(items)["status"],"BLOCKED")

if __name__=="__main__":
    unittest.main()
