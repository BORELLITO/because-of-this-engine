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


def pulse(t: float, period: float, offset: float = 0.0) -> float:
    phase = (t - offset) % period
    return math.exp(-4.8 * phase) if phase < 1.15 else 0.0


def render_sample(t: float, duration: float, channel: int) -> float:
    # Slow dark floor: intentionally stable enough to sit under narration.
    drift = 0.5 + 0.5 * math.sin(2.0 * math.pi * 0.065 * t)
    drone = (
        0.23 * math.sin(2.0 * math.pi * 47.0 * t)
        + 0.105 * math.sin(2.0 * math.pi * 70.5 * t + channel * 0.13)
        + 0.045 * math.sin(2.0 * math.pi * 94.0 * t)
    ) * (0.72 + 0.28 * drift)

    # A restrained heartbeat-like pulse gives the story an audible suspense
    # rhythm without turning the bed into a beat-driven music track.
    pulse_env = pulse(t, 2.35, 0.35)
    heartbeat = pulse_env * (
        0.20 * math.sin(2.0 * math.pi * 58.0 * t)
        + 0.065 * math.sin(2.0 * math.pi * 116.0 * t)
    )

    # Mid-band tension slowly moves in and out, preserving speech clarity.
    tension = (
        0.055
        * math.sin(2.0 * math.pi * (172.0 + 18.0 * math.sin(2.0 * math.pi * 0.08 * t)) * t)
        * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(2.0 * math.pi * 0.12 * t + 0.8)))
    )

    # Soft impacts at beat boundaries. They are short and low enough to remain
    # cinematic rather than sounding like a trailer hit.
    impact_env = max(
        pulse(t, 8.0, 0.10),
        0.72 * pulse(t, 8.0, 4.25),
    )
    impact = impact_env * (
        0.085 * math.sin(2.0 * math.pi * 82.0 * t)
        + 0.028 * math.sin(2.0 * math.pi * 164.0 * t)
    )

    # Very quiet stereo movement prevents the track from feeling flat.
    stereo = 1.0 + (0.035 if channel == 0 else -0.035) * math.sin(2.0 * math.pi * 0.11 * t)
    sample = (drone + heartbeat + tension + impact) * stereo
    return max(-0.78, min(0.78, sample * envelope_fade(t, duration)))


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
