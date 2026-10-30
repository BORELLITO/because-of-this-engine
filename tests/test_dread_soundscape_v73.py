from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from production.cinematic_dread import PROFILE
from production.generate_suspense_bed import generate


def manifest(episode="e-001"):
    return {"video_id":episode,"atmosphere":{"enabled":True,"profile":PROFILE,
            "director_review":"PENDING"},"scenes":[
            {"scene_id":"S01","story_beat":"hook","duration":5},
            {"scene_id":"S02","story_beat":"reveal","duration":5}]}


class CinematicDreadSoundscapeTests(unittest.TestCase):
    def test_same_episode_is_bitwise_reproducible_and_unrelated_episode_differs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            generate(root/"a.wav",10,1000,manifest())
            generate(root/"b.wav",10,1000,manifest())
            generate(root/"c.wav",10,1000,manifest("e-002"))
            a=(root/"a.wav").read_bytes()
            self.assertEqual(a,(root/"b.wav").read_bytes())
            self.assertNotEqual(a,(root/"c.wav").read_bytes())
            self.assertGreater(len(a),39000)
    def test_disabled_mode_preserves_legacy_exact_waveform(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            generate(root/"original.wav",10,1000)
            m=manifest();m["atmosphere"]={"enabled":False}
            generate(root/"new.wav",10,1000,m)
            self.assertEqual((root/"original.wav").read_bytes(),(root/"new.wav").read_bytes())
    def test_no_media_output_on_invalid_scene_contract(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"invalid.wav"
            m=manifest();m["atmosphere"]["profile"]="unsupported"
            with self.assertRaises(ValueError):generate(target,10,1000,m)
            self.assertFalse(target.exists())

if __name__=="__main__":unittest.main()
