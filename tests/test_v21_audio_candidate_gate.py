"""Deterministic bytes-first future music non-reuse regression.
Fixtures do not grant licenses or claim acoustic novelty in production.
"""
from __future__ import annotations
import hashlib
import json
import io
import math
import shutil
import struct
import wave
import tempfile
import unittest
from pathlib import Path
from production.audio_candidate_gate_v21 import check_file, historical_identities, _read

ROOT=Path(__file__).resolve().parents[1]

class AudioCandidateGateTests(unittest.TestCase):
    def setUp(self):
        self.ctx=tempfile.TemporaryDirectory();self.addCleanup(self.ctx.cleanup)
        self.root=Path(self.ctx.name)
        (self.root/"episodes").mkdir()
        def wav_bytes(freq:float)->bytes:
            output=io.BytesIO()
            with wave.open(output,"wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(8000)
                frames=bytearray()
                for i in range(8000*11):
                    value=int(17000*math.sin(2*math.pi*(freq+3*i/8000)*i/8000))
                    frames.extend(struct.pack("<h",value))
                w.writeframes(bytes(frames))
            return output.getvalue()
        self.old=wav_bytes(331.0)
        self.new=wav_bytes(223.0)
        self.old_sha=hashlib.sha256(self.old).hexdigest()
        self.master={"rendered_masters":[{
            "episode_id":"fixture-final","music_asset":{"sha256":self.old_sha,"drive_file_id":"historical-id"}
        }],"verified_full_track_collisions":[]}
        self.legacy={"tracks":[{"episode_id":"legacy-001","sha256":self.old_sha,
                               "drive_file_id":"historical-id","track_id":"existing-song"}]}
        (self.root/"episodes"/"audio-rendered-master-registry.json").write_text(json.dumps(self.master))
        (self.root/"episodes"/"audio-memory-registry.json").write_text(json.dumps(self.legacy))
        shutil.copyfile(ROOT/"episodes"/"audio-acoustic-fingerprints-v21.json",
                        self.root/"episodes"/"audio-acoustic-fingerprints-v21.json")
        self.audio=self.root/"candidate.wav"
        self.audio.write_bytes(self.new)
        self.candidate={"sha256":hashlib.sha256(self.new).hexdigest(),
                        "kind":"music_bed","license_verified":True,
                        "acoustic_uniqueness_qa":"VERIFIED","drive_file_id":"new-source"}

    @unittest.skipUnless(shutil.which("ffprobe"), "real ffprobe required for positive source validation")
    def test_distinct_audio_bytes_can_pass_identity_gate_without_publication_approval(self):
        report=check_file(self.audio,self.candidate,root=self.root)
        self.assertEqual(report["status"],"PASS",report)
        self.assertTrue(report["identity_check_pass"])
        self.assertFalse(report["ready_for_render"])
        self.assertEqual(report["scope"],"IDENTITY_AND_DECODING_ONLY_NEXT_STAGE_REQUIRED")
        self.assertFalse(report["publication_authorized"])

    def test_same_music_exact_source_detects_reuse(self):
        self.audio.write_bytes(self.old)
        c=dict(self.candidate,sha256=self.old_sha)
        report=check_file(self.audio,c,root=self.root)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertTrue(any("historical audio identity reused:sha256" in s for s in report["failures"]))

    def test_same_drive_id_even_if_bytes_reencoded_blocks(self):
        c=dict(self.candidate,drive_file_id="historical-id")
        self.assertTrue(any("historical audio identity reused:drive_file_id" in x
                             for x in check_file(self.audio,c,root=self.root)["failures"]))

    def test_cannot_claim_sha_while_supplying_different_bytes(self):
        c=dict(self.candidate,sha256=self.old_sha)
        report=check_file(self.audio,c,root=self.root)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertTrue(any("does not match actual" in x for x in report["failures"]))

    def test_license_or_acoustic_qa_absent_blocks(self):
        c=dict(self.candidate,license_verified=False,acoustic_uniqueness_qa="UNKNOWN")
        result=check_file(self.audio,c,root=self.root)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertGreaterEqual(len(result["failures"]),2)

    def test_sfx_no_proven_three_video_cooldown_blocks(self):
        c=dict(self.candidate,kind="sfx")
        self.assertTrue(any("SFX cooldown" in x
                            for x in check_file(self.audio,c,root=self.root)["failures"]))

    def test_real_master_and_legacy_registries_protect_identical_002_004_track(self):
        master=_read(ROOT/"episodes/audio-rendered-master-registry.json")
        legacy=_read(ROOT/"episodes/audio-memory-registry.json")
        ids=historical_identities(master,legacy)
        repeated="4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24"
        self.assertIn(repeated,ids["sha256"])
        duplicates=[x for x in master["rendered_masters"] if x["music_asset"]["sha256"]==repeated]
        self.assertEqual(len(duplicates),2)
        self.assertEqual(len(master["verified_full_track_collisions"]),1)

if __name__=="__main__":unittest.main()
