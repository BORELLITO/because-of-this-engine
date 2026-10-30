# BECAUSE OF THIS — V7.1 Piper Canonical Engine + Active V7.2 Reuse-First Add-ons

This repository contains the single canonical production engine for the
Because Of This channel. The approved V7.2 Reuse-First optimization layer is
ACTIVE on top of the locked Piper V7.1 core, without changing the canonical
voice model, profile fingerprint or human-controlled publication policy.
The active feature bundle is declared in `production/active_engine_policy.json`.
V7.1 is driven by the pinned master prompt
`docs/PROMPT_MESTRE_BECAUSE_OF_THIS_V7_1_PIPER_TTS_LOCAL.txt` and schema
`because-of-this://schemas/production-record/3.0.0`.

## Active engine contract

- Video-only vertical output: 1080×1920, 60 fps, 60–75 seconds.
- Narration provider: local Piper neural TTS only, `en_US-ryan-high`,
  LINEAR16 at 24 kHz, with no API key, billing account, network synthesis or silent fallback.
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
- `production/piper_tts.py` — Piper local model preflight, chunk synthesis,
  provenance, hashes and real-duration metadata; Edge and Google Cloud adapters are archived.
- `production/v7_post_publication.py` — manual-only G11 verifier.
- `.github/workflows/because-of-this-v7.yml` — manually dispatched production
  workflow; it stops on missing evidence and never publishes automatically.

## Lifecycle

Use `--mode contract` for structural validation before external work, `--mode
dry-run` for local Piper TTS prosody and orchestration checks, `--mode preflight` after
approved assets/music and narration coverage are hydrated, `--mode preview`
for a render candidate, and `--mode production` only after final artifacts,
preview approval and human approval are registered. A blocked gate is an intentional stop, not an implicit fallback.

The Episode 001 draft preview completed successfully with Piper narration,
Vosk-aligned captions, FFmpeg render and Drive delivery:
https://github.com/BORELLITO/because-of-this-engine/actions/runs/40986385249

**The already completed MP4 must be reused rather than rendered again when the
verified source script, manifest and code fingerprints match.** Its original
Drive folder is https://drive.google.com/drive/folders/1HkjYfLf4vXJuJ1XjE-pQWVdjPGho6NDh.
This file is DRAFT_PREVIEW_ONLY: do not confuse technical success with commercial
rights review, editorial approval or permission to publish.

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

## Active V7.2 Reuse First

- `production/narration_cache.py`: Piper model/config SHA-256, all voice settings, beat list and pronunciation-aware cache keys; Drive checksum-verified reuse.
- `production/asset_reuse_brain.py`: archived footage stays retired and cannot be silently recycled across episodes.
- `production/audio_reuse_brain.py`: track IDs, audio hashes, Drive IDs and historical music records checked.
- `production/release_integrity_v72.py`: read-only registry-backed release integrity checks in place of unconditional PASS metadata.
- `experimental/v72/reuse_first.py`: exact original media code and input fingerprints, original nine Drive delivery receipts and zero-media rerun planning.
- `experimental/v72/verify_drive_receipt.py`: read-only Drive receipt size/hash metadata verification.
- Two manual production/preview workflows share a media lock and preserve newly generated audio/caption artifacts on Drive. No automatic channel publishing.
- The ordinary main-branch CI now runs both the V7.1 canonical and extended V7.2 guard/regression suites. Full audiovisual second-run validation remains outstanding by design; do not waste production resources to recreate the approved preview.

