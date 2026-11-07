# Because Of This — V2.1 Senior Editorial Quality Runbook

**Purpose:** operational quality guidance for human/Work review, not an
executable approval or a replacement for `active_engine_policy.json`.
Do not interpret this document as permission to synthesize, fetch, render,
upload or publish.

## Source of truth and negative constraints

- All released stories in the active mode are `factual_documentary`.
- Human editorial authority remains independent of structural schema scores.
- External publication is manual; `production_enablement=false` is not
  a defect to bypass.
- Preserve Gemini TTS + Charon; never silently retry via a new voice.
- Protect approved audio/visual identity, provenance, hashes and receipts.
- A workflow marked SUCCESS proves only the specific steps it executed.

## Preproduction: 7 senior editorial questions

1. What fact-based danger or consequence is uniquely compelling?
2. Who bears the human consequence, and what was actually documented?
3. Which choice/technical hinge changed the result?
4. Is the causal chain distinguishable from speculation or embellishment?
5. Can the story fit 60–75 seconds without misleading compression?
6. Does the opening promise pay off with credible, meaningful resolution?
7. Can every beat be represented with responsibly licensed footage and
   truth-class labels (archive vs stock representation vs reconstruction)?

Reject by editorial review if any essential answer is generic, unverifiable,
contradictory or visually unworkable; an automated 10/10 structural score is
never sufficient.

## Claims and historical accuracy

Map each material claim to `claim_id`, source URLs, source type and
corroboration. Prefer primary evidence and independent corroboration.
Quote attribution, uncertainty, chronology and disputed interpretations
accurately. Audit referents such as "one", "the other", "it", "that device"
to prevent switching identities mid-story. Avoid recreations masquerading
as archival images and unverifiable character thoughts.

## Shot design and footage review

For each beat record: narration excerpt, depicted action, setting, era,
weather, lighting, source identity, license and truth class. Evaluate both
semantic correctness and adjacency continuity. Sample beginning, 25%,
midpoint, 75% and end before selection; inspect any additional risky
motion/overlay frames. Check crop in 9:16 and content at 1080x1920.
Flag modern UI in historical stories, legible unrelated signs, embedded
branding, daytime/nighttime contradictions, face/rights risks, looping,
derivative reuse or text that implies false documentary proof.

Metadata tags alone are NOT footage evidence; score threshold alone is
NOT a human visual inspection.

## Sound design / Charon

Lock script hash, audio hash, voice/provider/model and duration. Avoid
silent provider fallback. Never shift captions from a pre-final narration.
Measure levels and pauses after final mix. Human listening is required to
assess emotional restraint, pronunciation, musical masking, clicks, clipping
and awkward pacing; numerical WAV and LUFS gates cannot prove aesthetics.

## Captions

Use final WAV timestamps. Verify normalized canonical transcript exactly
matches frozen script, source WAV hash, monotonic timestamps, no mismatched
captions events and no out-of-bounds words. After render, inspect:
- first/last phonemes, word timing, pauses and actual ASR substitutions
- spelling of names, dates, numerals and acronyms
- red karaoke highlight, two-line readability and vertical safe zone
- off-screen text, collision with HUD/logo and burned-in stock text

Structural pass is not perceptual pass. Report unknowns; never declare
"perfect" without human QA against the rendered MP4.

## Thumbnail and packaging

Creative cover aligns to real opening/payout and has human approval
separate from pixel size, safe-zone checks and the recorded file hash.
Ensure visual truth class and disclosures are accurate. Evaluate at
mobile size. Add title, description, sources/credits and platform-specific
truth disclosures; licensed stock does not automatically satisfy platform
originality or monetization rules.

## Release gates and learning

Distinct statuses: CONTRACT / FACT / RIGHTS / VISUAL / AUDIO / CAPTIONS /
PREVIEW / HUMAN EDITORIAL / THUMBNAIL / TECHNICAL / MANUAL PUBLICATION.
No status is inferred from another. A blocked scene is not repaired by
changing a status string. Preserve previews and production files before
cleanup. Never auto-merge or auto-post. After release, use retention and
audience metrics over a suitable sample to propose experiments; do not
rewrite locked creative or video profiles after a single low-performing clip.

## Low-cost operational policy

Inspect and reuse matching assets/checkpoints *within their authorized
episode* before new requests. Record expected request cost/quotas before
Gemini or other external calls; cap retry loops and fail closed on quota
or provider mismatch. Avoid rerenders of approved media solely to test a
metadata change. Prefer read-only CI and static/deterministic tests first.

## Current 2026-11-07 holds

- Episode 005 acquisition-plan S09 `pexels-12213087` human approval
  and perceptual manifest fingerprint are not reconciled: must remain blocked.
- Episode 006 factual phrasing concerning the buried versus
  parachute-retarded bombs requires editorial correction review.
- The audio-memory registry is empty, so historical no-reuse coverage
  is not demonstrated.
- A live complete V2.1 final release pipeline has not been proven on
  this audit branch; no production enablement or publication is authorized.
