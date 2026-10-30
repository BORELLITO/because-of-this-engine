from __future__ import annotations
import shutil
import subprocess
import unittest
from production.cinematic_dread import music_filter
from production.render_video_episode import scene_filter


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg needed for atmosphere filter integration")
class DreadFFmpegSmokeTests(unittest.TestCase):
    def test_actual_cold_grade_grain_vignette_pipeline(self):
        grade={"enabled":True,"brightness":-0.043,"contrast":1.16,"saturation":0.78,
             "gamma":0.98,"vignette":True,"cinematic_suspense":{"enabled":True,
             "motion_strength":0.021,"push_in":0.034,"cool_shadows":0.059,
             "warm_highlights":0.004},"_dread_grain_strength":4,
             "_dread_vignette_angle":"PI/4.8"}
        flt=scene_filter(180,320,0.50,0.50,grade,duration=0.7)
        x=subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi",
            "-i","testsrc2=s=180x320:r=30","-t","0.6","-vf",flt,
            "-frames:v","20","-f","null","-"],
            capture_output=True,text=True,timeout=45)
        self.assertEqual(x.returncode,0,x.stderr[-1400:])
    def test_dynamic_music_gain_is_a_real_ffmpeg_filter(self):
        time=[{"end":0.2,"music_gain":0.84},{"end":0.6,"music_gain":1.12}]
        flt=music_filter(time)
        x=subprocess.run(["ffmpeg","-v","error","-f","lavfi",
            "-i","sine=frequency=110:sample_rate=48000","-t","0.6",
            "-af",flt,"-f","null","-"],capture_output=True,text=True,timeout=30)
        self.assertEqual(x.returncode,0,flt+"\n"+x.stderr[-1400:])

if __name__ == "__main__":unittest.main()
