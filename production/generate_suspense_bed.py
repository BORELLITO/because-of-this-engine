#!/usr/bin/env python3
"""Generate a deterministic, royalty-free suspense bed for draft previews.

The bed is intentionally synthesized from basic oscillators instead of a
third-party recording. It is a voice-first layer: low drone, slow pulse,
subtle high tension and restrained transition impacts. Every render gets the
same bytes for the same duration and sample rate.
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

DEFAULT_SAMPLE_RATE = 48_000
DEFAULT_DURATION = 70.0


def envelope_fade(t: float, duration: float) -> float:
    fade_in = min(1.0, t / 1.75)
    fade_out = min(1.0, max(0.0, (duration - t) / 1.25))
    return fade_in * fade_out


def render_sample(t: float, duration: float, channel: int) -> float:
    """Render a stable low cinematic drone without pulse or pitch-sweep artifacts.

    The bed intentionally avoids periodic beats, siren-like frequency motion and
    transition hits. It is a quiet E-minor harmonic floor designed to sit under
    voice-first narration.
    """
    slow_swell = 0.82 + 0.18 * (0.5 + 0.5 * math.sin(2.0 * math.pi * 0.025 * t + 0.4))

    # Stable E-minor harmonics: dark and cinematic, with no moving pitch.
    drone = (
        0.22 * math.sin(2.0 * math.pi * 41.20 * t)
        + 0.085 * math.sin(2.0 * math.pi * 49.00 * t + channel * 0.10)
        + 0.040 * math.sin(2.0 * math.pi * 61.74 * t)
        + 0.018 * math.sin(2.0 * math.pi * 82.41 * t + channel * 0.16)
    ) * slow_swell

    # Barely audible upper air preserves atmosphere without introducing a tone sweep.
    air = 0.010 * math.sin(2.0 * math.pi * 123.47 * t + channel * 0.21)
    stereo = 1.0 + (0.025 if channel == 0 else -0.025) * math.sin(2.0 * math.pi * 0.07 * t)
    sample = (drone + air) * stereo
    return max(-0.52, min(0.52, sample * envelope_fade(t, duration)))


def generate(output: Path, duration: float, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    if duration < 10:
        raise ValueError("Suspense bed duration must be at least 10 seconds.")
    output.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(round(duration * sample_rate))
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        block: list[bytes] = []
        for frame in range(total_frames):
            t = frame / sample_rate
            left = int(round(render_sample(t, duration, 0) * 32767))
            right = int(round(render_sample(t, duration, 1) * 32767))
            block.append(struct.pack("<hh", left, right))
            if len(block) >= 4096:
                handle.writeframes(b"".join(block))
                block.clear()
        if block:
            handle.writeframes(b"".join(block))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    args = parser.parse_args()
    generate(args.output, args.duration, args.sample_rate)
    print(f"SUSPENSE_BED_GENERATED path={args.output} duration={args.duration:.3f}s sample_rate={args.sample_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
