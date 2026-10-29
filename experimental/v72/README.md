# Because Of This — V7.2 Free Integrations (experimental only)

This directory is **not** a new canonical engine. The original V7.1 production
orchestrator, SSML Cloud TTS, Vosk word alignment, FFmpeg renderer, manual
publication rule, audiovisual layout, SHA-256 archive and global no-repeat policy
remain unmodified. The branch is isolated from main.

## Free software evaluated

- [AI Shorts Generator](https://github.com/AbdullahNaveed/ai-shorts-generator)
  — MIT. Its human-reviewable clip candidate concept inspired the independent
  metadata audit in `shot_review.py`. No external code or assets were copied.
  Its clip-reuse behavior must **not** be imported: this channel forbids a reused
  source across episodes.
- [WhisperX](https://github.com/m-bain/whisperX) — BSD-2-Clause. Optional
  **candidate-only** word alignment in `whisperx_optional.py` (separate
  installation and model weights). Never silently replaces Vosk or writes final
  subtitles. Tests run without downloading WhisperX.
- [ClipFactory](https://github.com/feyzilim/clipfactory) —
  Elastic License 2.0, **design reference only**; no code copied.
- [ZeroCost Shorts](https://github.com/igennova/ZeroCost-Shorts) —
  no license identified during review; **no code copied**.

## Experimental commands

```bash
PYTHONPATH=. python -m unittest tests.test_v72_free_integrations -v
PYTHONPATH=. python experimental/v72/shot_review.py \
  --manifest episodes/video-001/preview-manifest.json \
  --report /tmp/v72-shot-review.json
# Optional, runs on local hardware with separate WhisperX installation:
PYTHONPATH=. python experimental/v72/whisperx_optional.py \
  --wav episodes/video-001/audio/narration.wav \
  --script episodes/video-001/script.txt \
  --report /tmp/v72-whisperx-candidate.json
```

The shot audit checks scene-level source duplication and metadata **only**.
Canonical cross-episode asset registry checks, actual scene footage, source
rights, frame approval and the final MP4 require the existing V7 gates.
`METADATA_READY` does not mean video is ready or rights-cleared.

## Preview attempt

The isolated branch workflow tests V7.1 and V7.2, then attempts an editorial
draft preview using the existing V7.1 rendering pipeline and only previously
referenced Drive preview assets. It checks Drive access **before** any TTS
call. If secrets, source media, quota or validation are missing, it stops
without representing a static storyboard as a rendered video.

No publication, merge, deletion, or automatic approval is permitted.
