# Authorial visual layer

This layer is independent from the other engines and is designed for many videos, not only the Mars pilot.

## Contract

Each video supplies a manifest with:
- a stable `video_id`
- a topic
- one or more scene beats
- a subject, action, setting, mood, and optional camera direction per scene

The builder turns that manifest into a reusable prompt pack using the canonical style:

`because-of-this-cinematic-cartoon-v1`

The result is still marked `human_review_required: true`. Prompt generation is not approval and does not silently publish assets.

## Pipeline

`script -> beats -> scene manifest -> authorial prompt pack -> image provider -> visual QC -> smooth zoom/transitions -> external captions -> final video`

NASA, Wikimedia, or other factual sources may inform research and verification. They are not the final visual layer for this authorial style.

## Style guardrails

- premium adult editorial cartoon
- realistic proportions and readable silhouettes
- suspense through lighting, composition, and atmosphere
- charcoal/midnight/slate base with rust/burnt-orange accents and muted cyan
- vertical 9:16
- one primary subject or relationship per frame
- clean negative space for captions
- no text, labels, logos, watermarks, UI, collage, or childish proportions

## Safe rollout

1. Build the prompt pack without spending image quota.
2. Review one scene (S01) in the target generator.
3. Approve or revise the style lock.
4. Generate the remaining scenes.
5. Run visual QC before video assembly.

The Mars manifest is only a pilot example. New videos use the same contract and style lock.
