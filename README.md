# BECAUSE OF THIS — Independent Engine

Independent free-first engine for suspenseful science Shorts. It does not
modify or depend on Capta Pronto, Corte Fino, Publisher, Creator, or any other
protected engine.

## Current architecture

- `narrate.py`: optional Gemini TTS adapter with Charon support and provenance.
- `examples/`: canonical episode transcript.
- `production/`: manifest-driven render, validation, reports, and audit docs.
- `production/nasa_image_provider.py`: free, no-key NASA imagery adapter with
  vertical crop and provenance sidecars.
- `tests/`: unit and regression tests.
- `.github/workflows/validate.yml`: compile, tests, and JSON checks.

The current episode uses a local Charon WAV collected from Google AI Studio;
the API adapter remains available but does not store a key in the repository.
The current visual draft is v4 and maps the story beats explicitly: journey and
signal loss, unit mismatch, path divergence, dangerous approach, unresolved
warnings, and consequence.

The default visual provider is `nasa`, which uses the public NASA Image and
Video Library without an API key. Cloudflare and Gemini remain opt-in
providers; neither is an automatic fallback. Every downloaded asset keeps a
source URL and a license-review note in its sidecar, and human review remains
required before monetization.

## Local run

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python production/run_episode.py \
  --manifest production/mars-climate-orbiter-episode.json \
  --render
```

The run is manifest-driven, derives duration from the WAV, binds the canonical
transcript to captions by hash, measures technical mix, uses a lock, writes
temporary outputs before atomic promotion, and records a local JSONL run log.

`TECH_VALIDATED` is not `APPROVED`. A human mobile-speaker review and an exact
approval hash are required before any future delivery or publication step.

Generated WAV/MP4 media and local run logs are intentionally not versioned;
the repository stores source code, manifests, metadata, tests, and audit
records.
