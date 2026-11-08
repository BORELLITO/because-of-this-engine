"""V2.1 final renderer E2E: real synthetic mux, no production, TTS or publishing."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from production.render_v21_final import (
    PROFILE_PATH, FinalRenderError, _time_signature,
    _verify_preview_binding, _verify_sfx_evidence,
    assemble_verified_picture_with_audio, build_audio_mix_command, run_final,
)
from production.audio_mix_receipt_v21 import file_sha256

ROOT=Path(__file__).resolve().parents[1]
FFMPEG=bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def tone(path: Path, frequency: float, seconds: float = 14.0) -> None:
    with wave.open(str(path), "wb") as file:
        file.setframerate(16000)
        file.setnchannels(1)
        file.setsampwidth(2)
        file.writeframes(b"".join(
            struct.pack("<h", int(7000*math.sin(2*math.pi*frequency*t/16000)))
            for t in range(round(seconds*16000))))


class FinalV21RenderTests(unittest.TestCase):
    def setUp(self):
        ctx=tempfile.TemporaryDirectory()
        self.addCleanup(ctx.cleanup)
        self.root=Path(ctx.name)
        self.picture=self.root/"v21-preview.mp4"
        self.narration=self.root/"charon-fixture.wav"
        self.music=self.root/"new-music-fixture.wav"
        self.sfx=self.root/"pre-timed-sfx.wav"
        self.mix=self.root/"mix.wav"
        self.receipt=self.root/"mix-receipt.json"
        self.output=self.root/"final-master.mp4"
        self.profile=json.loads(PROFILE_PATH.read_text())

    def test_real_episode_cannot_render_when_canonical_preflight_is_blocked(self):
        # Check this before any of the supplied media inputs is read.
        with self.assertRaisesRegex(FinalRenderError, "canonical final render preflight blocked"):
            run_final(
                record_path=ROOT/"episodes/episode-005/production-record.json",
                repo_root=ROOT,
                preview=self.picture,preview_report=self.root/"nonexistent-preview.json",
                narration=self.narration,voice_profile=self.root/"voice-profile.json",
                music=self.music,music_candidate=self.root/"music-candidate.json",
                effects_manifest=self.root/"effects.json",
                sfx={"sfx:footsteps":self.sfx},
                output=self.output,mix_output=self.mix,receipt=self.receipt,
                report=self.root/"final-report.json",
            )
        self.assertFalse(self.output.exists())
        self.assertFalse(self.mix.exists())
        self.assertFalse(self.receipt.exists())

    def test_frozen_profile_rejects_unknown_sound_settings(self):
        p=dict(self.profile)
        self.assertAlmostEqual(_time_signature(p,65.0),70.5)
        p["voice_name"]="unapproved-voice"
        with self.assertRaises(FinalRenderError):
            _time_signature(p,65.0)
        p=dict(self.profile)
        p["music_gain"]=1.4
        with self.assertRaises(FinalRenderError):
            _time_signature(p,65.0)
        with self.assertRaises(FinalRenderError):
            _time_signature(self.profile,76.0)

    def test_mix_command_preserves_narration_target_and_pretimed_sfx(self):
        command=build_audio_mix_command(
            self.narration,self.music,{"sfx:footsteps":self.sfx},
            self.mix,voice_seconds=65.0,profile=self.profile)
        joined=" ".join(command)
        self.assertIn("loudnorm=I=-16:TP=-1:LRA=7",joined)
        self.assertIn("volume=0.1200",joined)
        self.assertIn("volume=0.0800",joined)
        self.assertIn("amix=inputs=3",joined)
        self.assertIn("sidechaincompress=",joined)
        self.assertIn("afade=t=out:st=67.000:d=3.500",joined)
        self.assertIn("atrim=duration=70.500",joined)
        self.assertIn("duration=longest",joined)
        self.assertNotIn("-stream_loop",command)
        self.assertIn("apad=pad_dur=5.500",joined)
        self.assertIn(str(self.output),str(self.output))
        self.assertIn(str(self.mix.resolve()),command[-1])

    def test_siren_sound_effect_is_rejected_without_forcing_unwanted_sfx(self):
        with self.assertRaisesRegex(FinalRenderError,"siren/alarm"):
            build_audio_mix_command(
                self.narration,self.music,{"sfx:siren":self.sfx},
                self.mix,voice_seconds=65.0,profile=self.profile)
        path=self.root/"effects-decision.json"
        path.write_text(json.dumps({
            "episode_id":"episode-test",
            "status":"QA_VERIFIED_NO_SFX_REQUIRED",
            "story_sound_design":"AMBIENT_MUSIC_ONLY","stems":[]}))
        _verify_sfx_evidence("episode-test",{},path)
        path.write_text(json.dumps({"episode_id":"episode-test",
             "status":"QA_VERIFIED_NO_SFX_REQUIRED","stems":[]}))
        with self.assertRaises(FinalRenderError):
            _verify_sfx_evidence("episode-test",{},path)

    def test_tampered_preview_report_blocks_before_assembly(self):
        self.picture.write_bytes(b"verified simulated preview bytes")
        voice={"audio_sha256":"a"*64}
        data={
            "status":"V21_CREATIVE_PREVIEW_RENDER_PASS",
            "creative_profile":"cinematic_dread_v73",
            "scene_count":16,
            "music":{"status":"NOT_MIXED"},
            "voice":{"audio_sha256":"a"*64},
            "branding":{"logo_overlay":True,"caption_margin_v":650,
                        "active_word_color":"#F04444","outro_audio":"silence"},
            "visual_continuity_gate":{"status":"PASS"},
            "output_sha256":file_sha256(self.picture),
        }
        report=self.root/"preview-report.json"
        report.write_text(json.dumps(data))
        _verify_preview_binding(self.picture,report,voice)
        data["branding"]["caption_margin_v"]=430
        report.write_text(json.dumps(data))
        with self.assertRaisesRegex(FinalRenderError,"preview.*changed"):
            _verify_preview_binding(self.picture,report,voice)
        data["branding"]["caption_margin_v"]=650
        data["output_sha256"]="0"*64
        report.write_text(json.dumps(data))
        with self.assertRaisesRegex(FinalRenderError,"bytes disagree"):
            _verify_preview_binding(self.picture,report,voice)

    def test_episode_specific_sfx_provenance_is_not_optional(self):
        self.sfx.write_bytes(b"test pretimed source audio")
        data={"episode_id":"episode-test","status":"QA_VERIFIED","stems":[{
            "role":"sfx:footsteps","source_sha256":file_sha256(self.sfx),
            "license_status":"APPROVED","timing_review":"VERIFIED"}]}
        path=self.root/"effects.json"
        path.write_text(json.dumps(data))
        _verify_sfx_evidence("episode-test",{"sfx:footsteps":self.sfx},path)
        with self.assertRaises(FinalRenderError):
            _verify_sfx_evidence("episode-test",{},path)
        data["stems"][0]["source_sha256"]="f"*64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(FinalRenderError,"SFX rights"):
            _verify_sfx_evidence("episode-test",{"sfx:footsteps":self.sfx},path)

    @unittest.skipUnless(FFMPEG,"real FFmpeg/ffprobe is required for E2E")
    def test_real_synthetic_picture_audio_mix_and_master_binding(self):
        # 14s synthetic fixture and 5.5s outro, not a production episode.
        # Only the isolated timing helper is patched; real FFmpeg mix,
        # receipt, counterfactual SFX checks, AAC master binding and bitstream
        # identity run unchanged.
        tone(self.narration,173)
        tone(self.music,91,20.0)
        tone(self.sfx,341)
        subprocess.run([
            "ffmpeg","-nostdin","-hide_banner","-loglevel","error",
            "-f","lavfi","-i","color=c=black:s=160x288:r=8",
            "-f","lavfi","-i","anullsrc=r=48000:cl=mono",
            "-t","19.5","-c:v","libx264","-preset","ultrafast",
            "-pix_fmt","yuv420p","-c:a","aac","-ar","48000",
            "-shortest","-y",str(self.picture)
        ],check=True,capture_output=True,timeout=70)
        with patch("production.render_v21_final._time_signature",return_value=19.5):
            result=assemble_verified_picture_with_audio(
                picture=self.picture,narration=self.narration,music=self.music,
                sfx={"sfx:footsteps":self.sfx},
                output=self.output,mix_output=self.mix,audio_receipt=self.receipt,
                voice_seconds=14.0,profile=self.profile,episode_id="synthetic-test"
            )
        self.assertEqual(result["status"],"V21_FINAL_AUDIO_AND_PICTURE_TECHNICAL_PASS",result)
        self.assertTrue(result["master_audio_bound"])
        self.assertCountEqual(result["stem_contributions"],["narration","music","sfx:footsteps"])
        self.assertNotEqual(result["picture_sha256"],result["final_master_sha256"])
        self.assertEqual(result["picture_video_stream_sha256"],
                         __import__("production.render_v21_final",fromlist=["_video_payload_sha256"])._video_payload_sha256(self.output))
        self.assertEqual(result["publication"],"MANUAL_ONLY_NOT_RUN")
        self.assertEqual(result["drive_write"],"NOT_RUN")
        import array
        with wave.open(str(self.mix),"rb") as f:
            rate=f.getframerate()
            audio=array.array("h")
            audio.frombytes(f.readframes(f.getnframes()))
        def rms(start,end):
            part=audio[int(start*rate):int(end*rate)]
            return math.sqrt(sum(x*x for x in part)/max(1,len(part)))
        self.assertGreater(rms(15.0,15.6),40.0,
                           "music must remain under the branded outro")
        self.assertLess(rms(19.3,19.48),rms(15.0,15.6)*0.5,
                        "soundtrack must fade to black instead of cutting")
        with patch("production.render_v21_final._time_signature",return_value=19.5):
            with self.assertRaisesRegex(FinalRenderError,"overwrite"):
                assemble_verified_picture_with_audio(
                    picture=self.picture,narration=self.narration,music=self.music,
                    sfx={"sfx:footsteps":self.sfx},output=self.output,mix_output=self.mix,
                    audio_receipt=self.receipt,voice_seconds=14,
                    profile=self.profile,episode_id="synthetic-test"
                )

if __name__=="__main__":
    unittest.main()
