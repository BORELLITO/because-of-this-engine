# BECAUSE OF THIS — Engine V7.1

This repository contains the single canonical production engine for the
Because Of This channel. V7.1 is driven by the pinned master prompt
`docs/PROMPT_MESTRE_BECAUSE_OF_THIS_V7_1_CLOUD_TTS_INTEGRADO.txt` and schema
`because-of-this://schemas/production-record/3.0.0`.

## Active engine contract

- Video-only vertical output: 1080×1920, 60 fps, 60–75 seconds.
- Narration provider: Google Cloud Text-to-Speech only, `en-US-Standard-B`,
  SSML, LINEAR16 at 24 kHz, with ADC/OAuth and no silent fallback.
- Audio is the master clock. Captions are generated from final audio using
  forced alignment; estimated timings are not accepted.
- Every visual beat requires direct semantic anchors, rights evidence,
  SHA-256/perceptual identity and a reservation/consumption history that
  prevents reuse or derivation reuse.
- Publication is always manual. The engine produces a handoff and G11 closes
  only from a matching manual publication receipt.

## Canonical entrypoints

- `production/v7_contract.py` — prompt, schema, manifest and gate contract.
- `production/v7_singleton_guard.py` — proves the active profile and workflow
  are V7.1 and rejects retired execution markers.
- `production/v7_orchestrator.py` — G0–G11 evaluation, idempotency and
  production-record generation.
- `production/cloud_tts.py` — Cloud TTS voice preflight, SSML synthesis,
  chunk provenance, hashes and real-duration metadata.
- `production/v7_post_publication.py` — manual-only G11 verifier.
- `.github/workflows/because-of-this-v7.yml` — manually dispatched production
  workflow; it stops on missing evidence and never publishes automatically.

## Lifecycle

Use `--mode contract` for structural validation, `--mode dry-run` for local
SSML and orchestration checks, `--mode preflight` before expensive media work,
and `--mode production` only after final artifacts and human approval are
registered. A blocked gate is an intentional stop, not an implicit fallback.

The current first episode is a V7 story/scene package but remains blocked at
visual asset approval until unique licensed or original clips are registered.

## Rollback

The previous V6/Gemini engine is not executable from the active tree. Its
entrypoints and exact stable commit are preserved under `archive/v6/` for
auditing and an explicit reviewed rollback only.

## Local checks

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python -m unittest discover -s tests -p 'test_v7*.py' -v
PYTHONPATH=. python production/v7_singleton_guard.py --repo-root .
PYTHONPATH=. python production/v7_orchestrator.py --repo-root . \
  --manifest episodes/video-001/manifest.json --mode dry-run
```
