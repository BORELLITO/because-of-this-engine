"""Real isolated FFmpeg execution + mix receipts; no TTS, master or publishing."""
from __future__ import annotations
import json
import math
import subprocess
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from production.audio_mix_receipt_v21 import (
    MixReceiptError, execute_with_receipt, file_sha256, verify_receipt, verify_master_binding,
)

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def make_tone(path: Path, frequency: float, seconds: float = 4.0) -> None:
    sr = 16000
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sr)
        stream.writeframes(b"".join(
            struct.pack("<h", int(8000*math.sin(2*math.pi*frequency*i/sr)))
            for i in range(int(seconds*sr))
        ))


@unittest.skipUnless(HAS_FFMPEG, "actual FFmpeg required; lightweight CI runs static tests")
class RealAudioMixReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.voice = self.root/"voice.wav"
        self.music = self.root/"music.wav"
        self.fx = self.root/"effect.wav"
        make_tone(self.voice, 166, 4.0)
        make_tone(self.music, 93, 4.0)
        make_tone(self.fx, 341, 4.0)
        self.output = self.root/"mixed.wav"
        self.receipt = self.root/"receipt.json"

    def command(self, *, with_effect: bool = False, omit_effect_from_filter: bool = False):
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
                   "-i", str(self.voice), "-i", str(self.music)]
        if with_effect:
            command += ["-i", str(self.fx)]
        if with_effect and not omit_effect_from_filter:
            graph = "[0:a]volume=0.9[v];[1:a]volume=0.18[m];[2:a]volume=0.08[s];[v][m][s]amix=inputs=3:duration=first[out]"
        else:
            graph = "[0:a]volume=0.9[v];[1:a]volume=0.18[m];[v][m]amix=inputs=2:duration=first[out]"
        return command+["-filter_complex", graph, "-map", "[out]",
                        "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
                        "-y", str(self.output)]

    def issue(self, *, with_effect=False, omit_effect_from_filter=False):
        stems = {"narration":self.voice, "music":self.music}
        if with_effect:
            stems["sfx:bell"] = self.fx
        command = self.command(with_effect=with_effect,
                               omit_effect_from_filter=omit_effect_from_filter)
        return execute_with_receipt("ep-test", command, stems, self.output, self.receipt)

    def test_actual_two_stem_mix_and_independent_replay(self):
        record=self.issue()
        self.assertEqual(record["state"],"MIX_EXECUTED_VERIFIED_LOCAL_SOURCE_BYTES")
        self.assertEqual(len(record["sources"]),2)
        result=verify_receipt(self.receipt)
        self.assertEqual(result["status"],"PASS",result)
        self.assertCountEqual(result["source_contributions_confirmed"],
                              ["narration","music"])
        self.assertFalse(result["master_video_verified"])
        self.assertFalse(result["publication_authorized"])

    def test_actual_three_stem_mix_confirms_effect_participation(self):
        self.issue(with_effect=True)
        result=verify_receipt(self.receipt)
        self.assertEqual(result["status"],"PASS",result)
        self.assertCountEqual(result["source_contributions_confirmed"],
                              ["narration","music","sfx:bell"])

    def test_declared_but_unused_effect_fails_post_mix_attestation(self):
        self.issue(with_effect=True, omit_effect_from_filter=True)
        result=verify_receipt(self.receipt)
        self.assertEqual(result["status"],"BLOCKED",result)
        self.assertTrue(any("no measured contribution" in item
                            for item in result.get("errors",[])))

    def test_master_aac_audio_binds_to_replayed_mix_without_publication(self):
        # Generate a real 14-second test master, not a production episode.
        make_tone(self.voice,166,14.0)
        make_tone(self.music,93,14.0)
        self.issue()
        video=self.root/"synthetic-master.mp4"
        subprocess.run([
            "ffmpeg","-nostdin","-hide_banner","-v","error",
            "-f","lavfi","-i","color=c=black:s=160x288:r=8",
            "-i",str(self.output),"-c:v","mpeg4","-c:a","aac",
            "-shortest","-y",str(video)],check=True,capture_output=True,timeout=60)
        result=verify_master_binding(self.receipt,video)
        self.assertEqual(result["status"],"PASS",result)
        self.assertTrue(result["master_audio_bound"])
        self.assertCountEqual(result["source_contributions_confirmed"],["narration","music"])
        self.assertFalse(result["publication_authorized"])

    def test_source_edit_after_render_is_detected(self):
        self.issue()
        make_tone(self.music, 139, 4.0)
        self.assertEqual(verify_receipt(self.receipt)["status"],"BLOCKED")

    def test_receipt_digest_forgery_is_detected(self):
        self.issue()
        data=json.loads(self.receipt.read_text())
        data["output"]["sha256"]="f"*64
        self.receipt.write_text(json.dumps(data))
        self.assertEqual(verify_receipt(self.receipt)["status"],"BLOCKED")

    def test_fresh_output_must_not_overwrite_previous_artifact(self):
        self.issue()
        before=file_sha256(self.output)
        with self.assertRaises(MixReceiptError):
            self.issue()
        self.assertEqual(before,file_sha256(self.output))

    def test_no_replay_cannot_be_mistaken_for_proof(self):
        self.issue()
        report=verify_receipt(self.receipt,replay=False)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertFalse(report["replay_verified"])

    def test_misdeclared_source_file_blocked(self):
        other=self.root/"other.wav"
        make_tone(other,444,4)
        with self.assertRaises(MixReceiptError):
            execute_with_receipt("ep-test",self.command(),
                                 {"narration":self.voice,"music":other},
                                 self.output,self.receipt)


if __name__=="__main__":
    unittest.main()
