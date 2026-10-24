import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from production.render_video_episode import ffprobe, mux_audio, prepare_logo


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required for the media smoke test")
class LogoOverlaySmokeTests(unittest.TestCase):
    def _run(self, command):
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)

    def test_original_logo_overlay_produces_valid_vertical_media(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, voice, captions = root / "source.mp4", root / "voice.wav", root / "captions.ass"
            logo, music, output = root / "logo.png", root / "music.wav", root / "output.mp4"
            self._run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#101624:s=1080x1920:r=25", "-t", "1.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)])
            with wave.open(str(voice), "wb") as handle:
                handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(24000)
                handle.writeframes(b"\x00\x00" * int(24000 * 1.2))
            captions.write_text("""[Script Info]
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,50,&H00FFFFFF,&H00FFFFFF,&H00101624,&H80101624,-1,0,0,0,100,100,0,0,1,3,1,2,100,100,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.20,Default,,0,0,300,,Smoke test
""", encoding="utf-8")
            self._run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=110:sample_rate=24000", "-t", "1.2", "-c:a", "pcm_s16le", str(music)])
            self._run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=360x90:r=25", "-vf", "drawbox=x=10:y=10:w=340:h=70:color=0xE3262E@1:t=fill", "-frames:v", "1", str(logo)])
            runtime_logo = root / "runtime-logo.png"
            prepare_logo(logo, runtime_logo, 360)
            mux_audio(source, voice, captions, output, 1.2, music, 0.12, None, runtime_logo,
                      {"logo_enabled": True, "logo_width": 360, "logo_opacity": 0.82, "logo_margin": 54, "logo_top": 72})
            media = ffprobe(output)
            self.assertEqual((media["width"], media["height"]), (1080, 1920))
            self.assertEqual(media["codec"], "h264")
            self.assertEqual(media["audio_codec"], "aac")
            self.assertEqual(media["sample_rate"], 48000)


if __name__ == "__main__":
    unittest.main()
