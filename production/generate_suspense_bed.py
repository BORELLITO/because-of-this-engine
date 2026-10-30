#!/usr/bin/env python3
"""Generate a deterministic, royalty-free suspense bed for draft previews.

The bed is intentionally synthesized from basic oscillators instead of a
third-party recording. It is a voice-first layer: low drone, slow pulse,
subtle high tension and restrained transition impacts. Every render gets the
same bytes for the same duration and sample rate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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


def _episode_variant(episode_id: str) -> tuple[float, float]:
    digest = hashlib.sha256(episode_id.encode("utf-8")).digest()
    # Two bounded sub-bass parameters derived from the exact episode ID:
    # deterministic across retries, different across unrelated stories.
    frequency_shift = digest[0] / 255.0 * 1.5
    phase = digest[1] / 255.0 * math.pi
    return frequency_shift, phase


def generate(output: Path, duration: float, sample_rate: int = DEFAULT_SAMPLE_RATE,
             atmosphere_manifest: dict | None = None) -> None:
    if duration < 10:
        raise ValueError("Suspense bed duration must be at least 10 seconds.")
    # The original deterministic soundtrack bytes remain unchanged when the
    # atmosphere module is absent. This is a reversible, opt-in sound design.
    schedule = []
    variant = (0.0, 0.0)
    if atmosphere_manifest is not None:
        from production.cinematic_dread import plan as dread_plan, timeline as dread_timeline
        direction = dread_plan(atmosphere_manifest)
        if direction.get("enabled"):
            episode_id = str(atmosphere_manifest.get("video_id") or "").strip()
            if not episode_id:
                raise ValueError("Atmospheric music needs a stable episode ID")
            schedule = dread_timeline(direction, atmosphere_manifest["scenes"], duration)
            variant = _episode_variant(episode_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(round(duration * sample_rate))
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        block: list[bytes] = []
        active_index = 0
        for frame in range(total_frames):
            t = frame / sample_rate
            if schedule:
                while active_index < len(schedule) - 1 and t >= schedule[active_index]["end"]:
                    active_index += 1
                intensity = schedule[active_index]["intensity"]
                # Slow, dissonant pressure is an ORIGINAL oscillator layer, not
                # a stock sound effect or repeated soundtrack between videos.
                # Keep it weak enough for the existing voice-first ducking.
                pressure = (
                    (0.008 + (intensity - 1) * 0.005)
                    * math.sin(2 * math.pi * (39.0 + variant[0]) * t + variant[1])
                    + (0.003 * intensity)
                    * math.sin(2 * math.pi * 80.5 * t + variant[1] * 0.42)
                ) * envelope_fade(t, duration)
                mix_scale = 0.935 + 0.038 * intensity
                left_f = max(-0.78, min(0.78, render_sample(t, duration, 0) * mix_scale + pressure))
                right_f = max(-0.78, min(0.78, render_sample(t, duration, 1) * mix_scale - pressure * 0.85))
            else:
                left_f = render_sample(t, duration, 0)
                right_f = render_sample(t, duration, 1)
            left = int(round(left_f * 32767))
            right = int(round(right_f * 32767))
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
    parser.add_argument("--atmosphere-manifest", type=Path,
                        help="Optional approved manifest; absent or disabled reproduces the legacy bed")
    args = parser.parse_args()
    atmosphere_manifest = None
    if args.atmosphere_manifest:
        atmosphere_manifest = json.loads(args.atmosphere_manifest.read_text(encoding="utf-8"))
    generate(args.output, args.duration, args.sample_rate, atmosphere_manifest)
    print(f"SUSPENSE_BED_GENERATED path={args.output} duration={args.duration:.3f}s sample_rate={args.sample_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
