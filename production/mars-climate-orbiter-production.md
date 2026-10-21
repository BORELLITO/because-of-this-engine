# BECAUSE OF THIS — Mars Climate Orbiter

## Current production state

- Voice: Charon
- Narration generated in Google AI Studio: 58 seconds
- Visual draft: 9:16, 1080×1920, 30 fps, controlled motion
- Visual direction: dark navy space, Mars orange, restrained technical graphics
- Narration WAV: collected locally, 58.36s, PCM 24 kHz mono
- Captions: rendered as a separate ASS layer
- Final audio mix: rendered with original restrained ambient bed
- Final video: `mars-climate-orbiter-final.mp4`, 58.37s, H.264 + AAC
- Episode manifest: `mars-climate-orbiter-episode.json`
- Claims/source register: `mars-climate-orbiter-claims.json`
- Technical validation: `mars-climate-orbiter-validation.json`, status `TECH_VALIDATED`
- Canonical transcript: `../examples/mars_climate_orbiter.txt`, hash-bound to the captions and audio provenance
- Mix measurement: approximately -18.3 LUFS integrated, -1.0 dBFS true peak
- Human state: `REVIEW_REQUIRED`; no publication is authorized yet

The detailed editorial specification, beat map, storyboard, asset manifest,
motion plan, quality gates, and red-team review are in
`mars-climate-orbiter-edit-spec.md`.

## Shot plan

| Time | Scene | Visual purpose |
| --- | --- | --- |
| 0–8s | Trajectory | Establish the spacecraft and the long journey to Mars. |
| 8–17s | Units | Show the split between pound-seconds and newton-seconds. |
| 17–28s | Navigation | Show the calculated trajectory diverging from the real path. |
| 28–39s | Approach | Build tension as the spacecraft reaches Mars too low. |
| 39–49s | Signal loss | Show the communication line fading and disappearing. |
| 49–58s | Consequence | Close on Mars and the system-level lesson. |

## Finalization gate

The WAV generated in AI Studio was collected from the existing AI Studio
player and used for synchronization. The workflow executed was:

1. inspect duration and sample format;
2. align caption blocks to the approved script and measured audio duration;
3. burn English captions in the lower safe zone;
4. mix narration above an original restrained ambient bed;
5. validate the full stream duration, codec, dimensions, and peak level;
6. export the final 1080×1920 MP4.

The visual draft v4 deliberately contains no invented NASA interface or archival
claims. Its unit labels and path labels are illustrative information graphics,
not NASA telemetry. It now maps each major narration beat to a concrete visual:
Earth-to-Mars journey and signal loss, unit mismatch, path divergence, dangerous
approach, unresolved warnings, and mission consequence. It remains a timing/
structure draft for the narrated facts, not the
final cinematic asset pass.

## Upgrade status

The independent engine now uses an episode manifest as its operational source
of truth, derives render duration from the narration WAV, binds the canonical
transcript to captions and provenance, records manual AI Studio audio
provenance, uses deterministic temporary renders, and runs a fail-closed
technical validator. Human mobile review is still required before `APPROVED`
or publishing.

