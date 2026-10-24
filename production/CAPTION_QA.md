# Caption QA contract — BECAUSE OF THIS

This is the caption gate for the independent Because of This engine. It adapts
the useful editorial behavior of the Corte Fino caption pipeline without
changing Corte Fino or copying its brand surface.

## What the gate proves

Before a preview is accepted, production/caption_quality.py verifies:

- exact normalized word identity between the canonical script and the ASS file;
- chronological event order and zero overlap;
- one or two semantic lines per event;
- per-line character limit and maximum reading speed;
- hook anchoring and end-of-narration coverage;
- centered mobile-safe lower-third placement;
- legible font, outline and shadow ranges;
- explicit alignment provenance.

The gate is intentionally fail-closed. A successful MP4 render is not enough.

## Timing honesty

The current Mars WAV was collected manually from AI Studio and does not include
a verifiable word timestamp sidecar. Therefore the current episode remains
phrase_level_manual_reviewed. The engine must not promote that state to
word_level_verified.

Preview mode accepts reviewed phrase-level captions after all readability and
transcript gates pass. Final mode must run with --require-word-level and will
block until a real forced-alignment or hybrid-alignment sidecar is attached and
validated.

## Editorial rules adapted from Corte Fino

- captions follow semantic thought units, not arbitrary equal-duration cards;
- breaks preserve meaning and do not split a name, number, unit or consequence;
- punctuation is retained and reviewed;
- one restrained highlight is allowed per block;
- captions stay in the lower safe zone with symmetric spacing;
- captions remain external until the render stage;
- no duplicated caption layer and no caption text baked into visual assets.

## Current Mars result

The current asset contains 18 reviewed phrase-level events, covering the full
156-word canonical transcript. That is a valid technical preview state, but it
is not a word-level timing proof and still requires human listening/phone review.
