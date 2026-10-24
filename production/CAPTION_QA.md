# Caption QA contract — BECAUSE OF THIS Engine v2

This is the caption gate for the definitive video-only engine. It verifies
that the captions remain faithful to the final narration and readable on a
mobile screen.

## What the gate proves

The caption checker verifies:

- exact normalized word identity between the canonical script and ASS;
- chronological event order and zero overlap;
- one or two semantic lines per event;
- character limits and maximum reading speed;
- hook anchoring and end-of-narration coverage;
- centered lower-third mobile-safe placement;
- legible font, outline and shadow ranges;
- explicit alignment provenance.

The gate is fail-closed. A successful MP4 render alone is not enough.

## Timing policy

Preview may use phrase-level timing only when it is explicitly declared and
reviewed. Final mode requires real word-level or hybrid forced alignment.
Captions are generated from the same narration used as the master clock and
are never maintained as an independent transcript.

## Editorial rules

- captions follow semantic thought units;
- breaks preserve meaning and do not split names, numbers or consequences;
- punctuation is retained and reviewed;
- captions stay in the lower safe zone with symmetric spacing;
- captions remain external until final mux;
- no duplicated caption layer and no text baked into narrative videos.


