# Because Of This V7.2 — Reuse First / Zero Waste (experimental, Piper)

**Base pinned:** `abd54f1f2d935f8d8c95810cc7900c646721079e` (main V7.1 Piper, first video preview delivered).
**This branch is not canonical.** Do not merge it or activate workflows in main before human approval.
No file in the previously delivered 9-file preview package is modified.

### Completed in this branch

1. `production/asset_reuse_brain.py`: historical/archived videos still block whole-source reuse in new episodes. Legacy pilot collisions stay separately reported and release-blocked.
2. `production/audio_reuse_brain.py`: track/Drive/hash provenance compared against active, archived and registry tracks; requires a present ledger when explicitly requested. Acoustic similarity and SFX cooldown are still separately required and **not** automatically cleared.
3. `production/narration_cache.py`: Piper support, cache key tied to actual ONNX model + config SHA-256, full voice settings, narration beats, pronunciation script, duration and verified WAV. No silently accepting a cache with missing model.
4. `experimental/v72/reuse_first.py` with `verified_preview_001.json`: locates already-successful video 001 Drive MP4, WAV, reports, and draft manifest; checks Git blob bytes to flag stale media instead of rebuilding it. **Read-only**: Drive-byte SHA/MD5 must still be checked on actual restoration.
5. `experimental/v72/shot_review.py`, `whisperx_optional.py` and `audio_boundary.py`: free optional review/word-QA candidates only. No generated voices or automatic captions.
6. New CI runs without TTS/FFmpeg media generation; regression tests verify no-repeat rules, stale cache rejection, Piper identity and previously delivered preview provenance.

### Existing finished preview — reuse, do not rerender

GitHub Actions: https://github.com/BORELLITO/because-of-this-engine/actions/runs/40986385249
Drive: https://drive.google.com/drive/folders/1HkjYfLf4vXJuJ1XjE-pQWVdjPGho6NDh
MP4: https://drive.google.com/file/d/1C3mkxkKy1uZh8pBKlDOmaaRr4Gk_DDVR/view
WAV: https://drive.google.com/file/d/1fFI8b5RzDq3qu_T44lEh-BHCqIHl4ttH/view
No production approval/publication or release clearance is implied by the draft preview.

### Still to integrate before promotion

- Commit/transfer durable Piper narration cache into the actual runner: **do not** regenerate the existing WAV as a side effect of promoting this branch.
- Add persistent cache hydration for caption alignment/ASS and scene renders. They were NOT uploaded in the prior preview bundle.
- Shared per-episode lock across preview/production, verified Drive restore, and cost-aware resumable workflow.
- Visual pixel-level comparisons to approved frames; actual rights evidence and Piper voice-model commercial-use license assessment.
- Atomic source reservations across concurrent episodes and robust SFX cooldown history.
- Repo branch protection via GitHub settings (App integration cannot change it).
- Never merge an older experimental branch wholesale; select changes to the approved Piper commit.

### Quick dry run (no media, no paid tools)

```bash
PYTHONPATH=. python -m unittest -v tests.test_reuse_first_v72 tests.test_v72_free_integrations tests.test_asset_reuse_brain tests.test_audio_reuse_v72 tests.test_narration_cache
PYTHONPATH=. python experimental/v72/reuse_first.py \
  --manifest episodes/video-001/preview-manifest.json \
  --script episodes/video-001/script.txt \
  --catalog experimental/v72/verified_preview_001.json \
  --report /tmp/v72-reuse-plan.json
```
