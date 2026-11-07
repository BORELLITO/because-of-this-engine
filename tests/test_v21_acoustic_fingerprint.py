"""Source-derived fingerprints must detect re-encoding/volume/excerpts, fail closed."""
from __future__ import annotations
import copy
import hashlib
import io
import json
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from production.audio_acoustic_fingerprint_v21 import (
    ALGORITHM, CATALOG_PATH, FingerprintError, compare, fingerprint,
    pack, review_file, unpack, catalog_coverage,
)

ROOT=Path(__file__).resolve().parents[1]
FFMPEG=bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _wav(path:Path, hz:float=157.0, duration:float=22.0)->None:
    sample_rate=8000
    frames=bytearray()
    for i in range(int(sample_rate*duration)):
        t=i/sample_rate
        envelope=0.5+0.32*math.sin(2*math.pi*0.17*t)
        value=int(14000*envelope*(
            0.60*math.sin(2*math.pi*(hz+2.0*math.sin(t*0.22))*t)
            +0.24*math.sin(2*math.pi*(hz*1.5)*t)
            +0.16*math.sin(2*math.pi*(hz*2.5)*t)))
        frames+=struct.pack("<h",max(-32767,min(32767,value)))
    with wave.open(str(path),"wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(bytes(frames))


class AudioAcousticFingerprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/CATALOG_PATH).read_text(encoding="utf-8"))

    def test_historical_fingerprint_entries_validate_checksums(self):
        self.assertEqual(self.catalog["algorithm"],ALGORITHM)
        self.assertEqual(len(self.catalog["sources"]),5)
        self.assertEqual(self.catalog["source_count"],5)
        self.assertEqual(catalog_coverage(ROOT)["status"],"PASS")
        sources={x["source_sha256"] for x in self.catalog["sources"]}
        self.assertIn("4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24",sources)
        for x in self.catalog["sources"]:
            f=unpack(x["fingerprint"])
            self.assertGreaterEqual(len(f),64)
            self.assertEqual(pack(f)["raw_sha256"],x["fingerprint"]["raw_sha256"])

    def test_all_three_original_mp3_sources_are_covered(self):
        expected={
            "49842074dc06f05a40690c2b3af42bd32be76a5f6505a65cfe952b2fe1ccb5de",
            "144384cf2bcda8070a0d11c8aa98c3ae547de861a553275788669b7cf6a57bcd",
            "dd57de53251011da1cc72f22c81595e80c03151c46d4a43e71aa6baaf2bc98cc",
        }
        present={x["source_sha256"] for x in self.catalog["sources"]}
        self.assertTrue(expected.issubset(present))
        result=catalog_coverage(ROOT)
        self.assertEqual(result["known_source_count"],5)
        self.assertEqual(result["covered_count"],5)
        self.assertEqual(result["missing_source_sha256"],[])

    def test_all_five_full_signatures_decode_and_do_not_cross_match_as_copies(self):
        frames=[unpack(x["fingerprint"]) for x in self.catalog["sources"]]
        self.assertEqual([len(f) for f in frames],[544,544,1806,797,1077])
        for i in range(len(frames)):
            for j in range(i+1,len(frames)):
                verdict=compare(frames[i],frames[j])
                self.assertNotEqual(verdict["classification"],"LIKELY_REUSE",
                                   (i,j,verdict))
        for f in frames:
            self.assertEqual(compare(f,f)["classification"],"LIKELY_REUSE")

    def test_missing_acoustic_source_cannot_be_considered_complete(self):
        with tempfile.TemporaryDirectory() as dirname:
            from shutil import copyfile
            import json
            root=Path(dirname)
            (root/"episodes").mkdir()
            for name in ("audio-memory-registry.json","audio-rendered-master-registry.json"):
                copyfile(ROOT/"episodes"/name,root/"episodes"/name)
            catalog=copy.deepcopy(self.catalog)
            catalog["sources"]=[s for s in catalog["sources"]
                                  if s["source_id"]!="legacy-003-echoes"]
            catalog["source_count"]=len(catalog["sources"])
            (root/CATALOG_PATH).write_text(json.dumps(catalog))
            outcome=catalog_coverage(root)
            self.assertEqual(outcome["status"],"BLOCKED")
            self.assertIn("49842074dc06f05a40690c2b3af42bd32be76a5f6505a65cfe952b2fe1ccb5de",
                          outcome["missing_source_sha256"])

    def test_corrupted_fingerprint_is_blocked(self):
        entry=copy.deepcopy(self.catalog["sources"][0]["fingerprint"])
        entry["raw_sha256"]="a"*64
        with self.assertRaises(FingerprintError):
            unpack(entry)

    def test_embedded_source_002_and_004_same_acoustic_signature(self):
        used=next(x for x in self.catalog["sources"] if x["source_id"]=="v7-002-004-reused-procedural")
        self.assertEqual(compare(unpack(used["fingerprint"]),unpack(used["fingerprint"]))["classification"],"LIKELY_REUSE")
        self.assertEqual(used["historical_episode_ids"],["episode-002-archive-tape","because-of-this-episode-004"])

    @unittest.skipUnless(FFMPEG,"Chromaprint/FFmpeg unavailable in lightweight CI")
    def test_actual_reencoded_gain_changed_excerpt_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"original.wav"
            altered=root/"altered.m4a"
            _wav(source,157.0,28.0)
            subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
                            "-y","-ss","7","-i",str(source),"-t","15",
                            "-af","volume=0.36","-c:a","aac","-b:a","96k",
                            str(altered)],check=True,capture_output=True,timeout=30)
            original_fp=fingerprint(source)
            changed_fp=fingerprint(altered)
            result=compare(changed_fp,original_fp)
            self.assertEqual(result["classification"],"LIKELY_REUSE",result)
            self.assertGreaterEqual(result["similarity"],0.88)
            self.assertNotEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                                hashlib.sha256(altered.read_bytes()).hexdigest())
            cat=root/"catalog.json"
            cat.write_text(json.dumps({"algorithm":ALGORITHM,"sources":[{
                "source_id":"fixture","source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                "fingerprint":pack(original_fp)}]}))
            inspection=review_file(altered,cat)
            self.assertEqual(inspection["status"],"BLOCKED")
            self.assertFalse(inspection["ready_for_render"])

    @unittest.skipUnless(FFMPEG,"Chromaprint/FFmpeg unavailable in lightweight CI")
    def test_unrelated_sources_not_claimed_as_definite_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"a.wav"
            b=Path(tmp)/"b.wav"
            _wav(a,137.0,20)
            _wav(b,583.0,20)
            result=compare(fingerprint(a),fingerprint(b))
            self.assertLess(result["similarity"],0.88,result)

    def test_missing_catalog_blocks_instead_of_succeeding(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=review_file(Path(tmp)/"no.wav",Path(tmp)/"missing.json")
            self.assertEqual(result["status"],"BLOCKED")


if __name__=="__main__":
    unittest.main()
