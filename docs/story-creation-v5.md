# Story creation intelligence v5

The engine now treats story creation as a release boundary before visual search and rendering.

## Contract

Every episode manifest must contain a `story_creation` object with:

- an explicit idea promise and central question;
- a declared truth mode: `REAL_FACTUAL`, `DOCUMENTED_RECONSTRUCTION`, or `DECLARED_FICTION`;
- a causal chain: cause → escalation → consequence → why it mattered;
- a calibrated emotional arc;
- an explicit promise and payoff;
- state transitions for every story beat;
- visual feasibility evidence before script lock;
- channel-diversity evidence;
- original authorship and provenance evidence;
- YouTube/TikTok safety classifications;
- a 60–75 second density plan without padding;
- editorial, factual, and monetization red-team sign-off.

The block is audited by `production/story_creation.py` and reported as `C0–C11`. The canonical `quality_gates.py` report includes those results alongside the existing `G0–G12` and `S0–S2` gates.

## Review behavior

A gate is blocked when the evidence is missing or contradictory. The system does not infer that a stock clip proves a narrated claim. Symbolic or explanatory footage must be declared as such in the existing visual contract.

Existing episodes can be migrated with `legacy_backfill: true`, but the reason must be recorded. New episodes must prove that visual feasibility was checked before script lock.

## Local command

```bash
python production/story_creation.py \
  --manifest episodes/episode-001/manifest.json \
  --report episodes/episode-001/rendered/story-creation-preview.json
```

A non-zero exit means the story is not ready to enter the render pipeline.
