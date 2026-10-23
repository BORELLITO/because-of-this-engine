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
- regression tests for motion selection, invalid easing, repetition and transitions.

## Current Mars contract

The Mars manifest now covers the complete Charon narration instead of six equal
placeholder scenes. It includes a beat, visual intent, image type, emotion and
motion choice for every scene. It still requires real WAV, reviewed images and
provenance sidecars under `examples/assets/`.

## Honest release status

The engine upgrade is implemented and unit-tested. A new episode is **not**
declared final until the asset-complete preview passes the validator, is watched
on a phone, and receives a fresh hash-bound approval file.

See `production/DOCUMENTARY_ENGINE_AUDIT_2026-10-23.md` for the complete audit,
priority matrix, residual risks and operational checklist.
