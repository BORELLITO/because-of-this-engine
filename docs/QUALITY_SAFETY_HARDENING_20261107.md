# Because Of This — Safety and Quality Hardening (2026-11-07)

**Scope:** isolated audit branch. This document is not permission to synthesize,
render, publish, mutate the global media catalog, or enable production.

## Authority and operating invariants

- Canonical identity: `production/active_engine_policy.json`, active V2.1.
- Canonical entrypoint: `production/canonical_entrypoint.py` validates contracts;
  it DOES NOT synthesize audio, render footage, write Drive or publish.
- Voice: direct Gemini/Charon; no implicit Edge, Piper or Cloud TTS fallback.
- Documentary mode: factual, verified sources; re-creations are not archival evidence.
- Publication stays manual, `production_enablement=false`, old engines rollback-only.
- Original audio is the timing master. Forced word timestamps do not alone
  establish perceptually perfect subtitles; review the rendered video.
- Claims of complete technical or editorial readiness require distinct evidence.

## P0: preserve deliverables

The former scheduled housekeeping deleted unprotected Actions artifacts older than
three days and old workflow-run evidence. It has been replaced IN THIS BRANCH with a
**read-only storage report**. It cannot call deleteArtifact, deleteWorkflowRun or
delete cache endpoints. Nothing is permanently removed by this patch.

Three recent checkpoints were independently copied to Google Drive on 2026-11-07,
in folder `A BECAUSE OF THIS — PRODUÇÕES`:
- Episode 006 Charon narration: `1AdO-cWZuuB5xLfRZXT3LxPXv2zZzqy8-`, 2,641,420 bytes.
- Episode 006 Charon narration+captions: `12M70EUiodrvBYzVJ3ahrwt6p58O5-MPT`, 2,654,033 bytes.
- Episode 005 V2.1 creative preview: `1BhV8WR_0oEQZOb03kchMCCAK-LFUj2ek`, 24,667,284 bytes.

These files were uploaded and Drive metadata sizes checked. Full byte-for-byte
restore/checksum verification and inventory of all older assets remain pending.

**Warning:** the main branch still has the former housekeeping until this PR
has been reviewed and merged. Do not mistake a branch-level fix for production.

## P0: visual manifest — no fabricated approvals

The active Episode 005 plan lists `pexels-12213087` as
`CANDIDATE_DOWNLOADED_AWAITING_HUMAN_QA`, with `qa.human_approval=PENDING`.
The scene manifest instead says `APPROVED_FOR_MANIFEST_ONLY` and contains
`perceptual_hash=PENDING_MANIFEST_ONLY` while an intake perceptual hash exists.

The verifier now enforces matching SHA-256 and perceptual identity, independently
of the human approval state. Current real data remains BLOCKED. A synthetic
in-memory test reconciles both discrepancies to prove the positive path; it
DOES NOT alter the actual manifest, grant rights, or authorize render.

CI explicitly asserts the two KNOWN blocked reasons while failing on unexpected
new discrepancies. CI green for an expected blocked case means the fail-closed
policy works; it does not mean the Episode 005 visual release is approved.

## P0: singleton engine

The former Edge TTS Episode 005 workflow was copied under
`archive/v21/workflows/` and removed from `.github/workflows/` IN THIS BRANCH.
The singleton guard rejects workflows invoking retired runtime providers/entrypoints
and workflow names indicating retired Edge/Piper routes. Gemini/Charon remains valid.

Legacy modules in `production/` are retained for traceability. Actual run
permissions and provider identity should still be audited for every dispatch.

## QA policy: separate proof levels

1. **Structural contract PASS:** fields and identities are consistent.
2. **Source verification PASS:** critical claims are checked against actual sources.
3. **Asset licensing PASS:** provider, author, terms, commercial use, restrictions
   and license evidence independently checked.
4. **Visual-semantic PASS:** inspected frames show the described action without
   period, setting, day/night, cropping or timeline contradictions.
5. **Audio/caption PASS:** WAV hashes, source transcript, alignment sidecar and
   rendered text/safe-zones verified together, with perceptual spot-check.
6. **Human editorial PASS:** actual story strength, emotion, ethical framing,
   factual causality, ambiguity, hooks and payoff reviewed.
7. **Production/release PASS:** technical render, thumbnail, package and manual
   release authorization independently recorded.

A field saying `VERIFIED`, `APPROVED` or a score 10/10 is not, on its own,
proof that the underlying real-world claim or creative quality was inspected.
Do not auto-promote from metadata to artistic/factual/publication approval.

## P1/P2 backlog — avoid unsafe premature activation

- Implement reproducible evidence-linked claim reviews and historical ambiguity
  checks before final factual approval. Episode 006: review which Goldsboro bomb
  was buried versus which descended by parachute.
- Review semantic clip continuity from frame samples across the FULL duration,
  not solely hand-entered tags. Require adequate proof coverage.
- Compare spoken Charon WAV against captions perceptually and validate mobile
  overlay after encoding; timestamps alone do not establish zero audible error.
- Treat original, licensed and transformed footage as separate checks. Confirm
  platform disclosure rules and originality/monetization requirements.
- Restore and reconcile complete track/SFX history before declaring no-reuse;
  the present `episodes/audio-memory-registry.json` contains an empty track list.
- Require video-specific thumbnail review: safe zones, title truthfulness,
  mobile legibility and evidence status; dimension PASS is not artistic PASS.
- Generalize Episode 005-only render assertions only after a new episode's
  contract and regression baselines exist, without touching the approved preview.
- Track quotas and retries before external TTS or media generation.
- Use analytics in a controlled review loop; never silently rewrite approved
  creative or visual settings.

## Verification and rollback

Run in CI on the branch:
```
PYTHONPATH=. python -m unittest discover -s tests -p 'test_v21*.py' -v
PYTHONPATH=. python production/v21_singleton_guard.py --repo-root .
```
Use PR checks and inspect both the *contract* CI and the *main* CI.
No production switch, Drive publication, or TTS synthesis is included.
Rollback by closing the PR or reverting its commits. Do not erase history.
