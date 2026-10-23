# Authorial pipeline upgrade status

## Implemented in the independent engine

- canonical authorial manifest schema `1.1`;
- narration-first timeline gate with a 0.75 s tolerance;
- external captions, duplicate scene and schema checks;
- provenance-safe image ingestion and release validation;
- deterministic contextual motion engine with smoothstep/ease-in-out;
- subpixel-stable Pillow frame rendering with no shake or random jitter;
- controlled motion variety gate and per-scene visual-plan fields;
- contextual transition contract with conservative crossfade default;
- optional music/license and AI-disclosure gates;
- preview approval bound to manifest, inputs and preview output;
- atomic render promotion and fail-closed workflow behavior;
- regression tests for motion selection, invalid easing, repetition and transitions;
- narration-locked master contract on a 24 kHz audio sample clock and 25 fps rational timebase;
- source fingerprinting for manifest, narration, captions and scene assets;
- post-render media gate for zero start offsets, CFR, duration, sample rate and mux consistency;
- explicit visual-story gate requiring a function and match grade per scene;
- honest phrase-level caption alignment when word-level forced alignment is unavailable (no invented word precision);
- best-effort artifact delivery separated from content-quality gates so GitHub storage quota cannot rewrite a valid render as a sync failure.

## Current Mars contract

The Mars manifest now covers the complete Charon narration instead of six equal
placeholder scenes. It includes a beat, visual intent, image type, emotion,
visual function, visual match and motion choice for every scene. It still
requires real WAV, reviewed images and provenance sidecars under
`examples/assets/`.

The master timeline is derived from the narration duration (58.36 s), using
integer frame/sample conversions at the declared timebase. The current episode
uses `phrase_level_manual_reviewed` because no word-level aligner is installed;
the validator reports that limitation instead of claiming false precision.

## Honest release status

The hard-lock implementation is committed and the integrated GitHub Actions
preview run completed successfully through all content gates:

- run: https://github.com/BORELLITO/because-of-this-engine/actions/runs/40002494516
- result: `MASTER_TIMELINE_VALIDATED`
- post-render sync: `PASS`
- stale-artifact check: `PASS`
- caption events: 18
- narration duration: 58.36 s

The run's artifact upload was best-effort and was externally blocked by GitHub
Actions storage quota; this does not invalidate the render or its gates. A fresh
artifact can be uploaded automatically after quota recalculation.

A new episode is **not** declared final until the asset-complete preview passes
the validator, is watched on a phone, and receives a fresh hash-bound approval
file. The current run is a validated preview, not a final publish approval.

See `production/DOCUMENTARY_ENGINE_AUDIT_2026-10-23.md` for the complete audit,
priority matrix, residual risks and operational checklist.
