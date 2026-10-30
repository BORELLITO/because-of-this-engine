from __future__ import annotations

import copy
import math
import unittest
from production.cinematic_dread import (
    AtmosphereError, PROFILE, LEVELS, grade_for_scene, music_filter,
    plan, scene_level, timeline,
)
from production.canonical_config import CANONICAL_PROFILE


def make():
    return {"atmosphere":{"enabled":True, "profile":PROFILE, "director_review":"PENDING",
            "scene_overrides":{"S02":{"intensity":4,"reason":"Impossible floor is revealed"}}},
            "scenes":[
                {"scene_id":"S01", "story_beat":"hook", "duration":6},
                {"scene_id":"S02", "story_beat":"reveal", "duration":7},
                {"scene_id":"S03", "story_beat":"aftermath", "duration":6},
            ]}


class CinematicDreadV73Tests(unittest.TestCase):
    def test_opt_in_never_changes_canonical_profile(self):
        manifest = make()
        canonical = copy.deepcopy(CANONICAL_PROFILE)
        result=plan(manifest)
        self.assertEqual(result["profile"], PROFILE)
        self.assertEqual([x["intensity"] for x in result["scenes"]], [1,4,2])
        self.assertEqual(CANONICAL_PROFILE, canonical)
        self.assertTrue(result["human_final_approval_required"])
    def test_old_manifests_render_identically(self):
        self.assertEqual(plan({"scenes":[]})["enabled"], False)
        base = CANONICAL_PROFILE["color_grade"]
        self.assertIs(grade_for_scene(base, {"scene_id":"S01"}, {"enabled":False}), base)
    def test_grade_is_contextual_not_uniform(self):
        manifest=make()
        direction=plan(manifest)
        base=copy.deepcopy(CANONICAL_PROFILE["color_grade"])
        a=grade_for_scene(base,manifest["scenes"][0],direction)
        b=grade_for_scene(base,manifest["scenes"][1],direction)
        self.assertLess(b["brightness"], a["brightness"])
        self.assertLess(b["saturation"], a["saturation"])
        self.assertLessEqual(b["_dread_grain_strength"], 4)
        self.assertEqual(base, CANONICAL_PROFILE["color_grade"])
        self.assertEqual(a["cinematic_suspense"]["push_in"],0.034)
    def test_malformed_inputs_fail_closed(self):
        m=make();m["atmosphere"]["profile"]="random_filter"
        with self.assertRaises(AtmosphereError):plan(m)
        m=make();m["atmosphere"]["scene_overrides"]["S02"]["intensity"]=True
        with self.assertRaises(AtmosphereError):plan(m)
        m=make();m["atmosphere"]["scene_overrides"]["X99"]={"intensity":4,"reason":"bad"}
        with self.assertRaises(AtmosphereError):plan(m)
        m=make();m["atmosphere"]["director_review"]="PASS"
        with self.assertRaises(AtmosphereError):plan(m)
        m=make();m["atmosphere"]["unknown"]="text"
        with self.assertRaises(AtmosphereError):plan(m)
        m=make();m["atmosphere"]["scene_overrides"]["S02"]["reason"]=""
        with self.assertRaises(AtmosphereError):plan(m)
    def test_timeline_respects_original_audio_clock_and_gain_limit(self):
        m=make();d=plan(m)
        result=timeline(d,m["scenes"],66.0)
        self.assertAlmostEqual(result[-1]["end"],66.0)
        self.assertTrue(all(0.8<=x["music_gain"]<=1.12 for x in result))
        self.assertIn("if(lt(t",music_filter(result))
        self.assertIn("eval=frame",music_filter(result))
        with self.assertRaises(AtmosphereError): timeline(d,m["scenes"],float("nan"))
    def test_plan_does_not_approve_pixel_evidence_or_publishing(self):
        d=plan(make())
        self.assertEqual(d["director_review"],"PENDING")
        self.assertIn("no synthetic objects",d["source_clip_mutation"])
        self.assertFalse("publication_approved" in d)
    def test_preexisting_score_and_voice_untouched(self):
        m=make();m["voice"]={"provider":"gemini_tts","voice_name":"Charon"}
        before=copy.deepcopy(m)
        plan(m)
        self.assertEqual(m,before)

if __name__ == "__main__":unittest.main()
