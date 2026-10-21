# BECAUSE OF THIS — Independent Engine

Independent free-first engine for suspenseful science Shorts. It does not
modify or depend on Capta Pronto, Corte Fino, Publisher, Creator, or any other
protected engine.

## Current architecture

The official path is the generic authorial episode pipeline:

- `narrate.py`: optional Gemini TTS adapter with Charon support and provenance.
- `production/build_authorial_prompt_pack.py`: reusable visual prompt builder.
- `production/render_authorial_episode.py`: deterministic FFmpeg assembler.
- `production/validate_authorial_episode.py`: fail-closed release validator.
- `production/require_preview_approval.py`: final-render approval gate.
- `examples/`: episode manifests, scripts, captions, and asset contracts.
- `tests/`: unit and regression tests.
- `.github/workflows/validate.yml`: compile, tests, and JSON checks.
- `.github/workflows/render-authorial-episode.yml`: preview/final workflow.

The older Mars renderer and validator remain as legacy compatibility paths while
the authorial pipeline is migrated. They are not the official path for new
episodes.

A release episode requires a Charon-compatible 24 kHz mono WAV, external ASS
captions, reviewed 9:16 images, image provenance sidecars, a preview render,
human approval, and a validated final render.

NASA, Cloudflare, and Gemini providers are separate adapters. NASA imagery is
not considered an authorial cartoon asset by itself; a provider must be selected
explicitly and every visual remains subject to human review.

The motion assembler applies only deterministic smooth zoom and short fade
crossfades. It does not use shake, glitch, decorative transition packs, or
image regeneration during assembly.

## Local run

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python production/run_episode.py \
  --manifest production/mars-climate-orbiter-episode.json \
  --render
```

For the new authorial path, validate the contract and render a preview:

```bash
python production/validate_authorial_manifest_contract.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json
python production/render_authorial_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview
python production/validate_authorial_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview
```

Legacy Mars runs are manifest-driven and remain protected by their historical
validator. New authorial releases must use the preview, approval, and release
validation gates described in `production/AUTHORIAL_RENDERING.md`.

`PREVIEW_VALIDATED` is not `APPROVED`. A human mobile-speaker review and an
exact approval hash are required before any final delivery step.

Generated WAV/MP4 media and local run logs are intentionally not versioned;
the repository stores source code, manifests, metadata, tests, and audit
records.
