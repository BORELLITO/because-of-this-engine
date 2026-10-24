# BECAUSE OF THIS — Engine v2

The definitive production engine for the Because of This channel. It is
independent from Corte Fino, Rajada 011, CaptaPronto, Publisher and every
other project.

## Official architecture

The v2 pipeline is video-only:

1. Story and narration define the master clock.
2. Cloud Browser research creates a review queue from Mixkit, Pixabay and
   Pexels.
3. A human approves the exact clip and its licence.
4. The approved file is staged in Google Drive.
5. GitHub Actions hydrates the asset, verifies its MIME type and SHA-256, and
   renders with FFmpeg.
6. Captions, visual truth, reuse and final media gates run before delivery.
7. Validated media is uploaded to Drive and ephemeral runner media is removed.

Narrative still images are not supported. A scene must contain a real video
asset. If the exact visual is unavailable, the manifest must explicitly
declare a semantic fallback: NEAR, EXPLANATORY, SYMBOLIC or ATMOSPHERE.
Random filler and image fallback are forbidden.

## Quality gates

- 60–75 second episode duration.
- 9:16 output: 1080×1920 preview or 2160×3840 final.
- H.264/AAC, 25 fps, faststart and no stretched footage.
- Narration-locked scene timing.
- External ASS captions generated from the final narration.
- Two-line mobile-safe captions with CPS limits.
- Licensed suspense music below the voice, with sidechain ducking and
  loudness/true-peak control.
- No repeated narrative asset in an episode.
- No repeated clip across episodes when its registry status is
  PERMANENTLY_RETIRED.
- Source URL, licence, Drive ID, SHA-256 and approval status are required.

## Useful files

- narrate.py: isolated Gemini TTS adapter.
- production/video_asset_research.py: review queue and semantic fallback
  ladder.
- production/google_drive_assets.py: Drive-to-runner asset bridge.
- production/video_asset_contract.py: fail-closed v2 contract.
- production/render_video_episode.py: deterministic FFmpeg renderer.
- production/validate_video_release.py: post-render release gate with independent media/caption verification.
- production/pipeline_state.py: stable job identity and explicit state machine.
- production/finalize_manifest.py: reproducible final manifest and cleanup completion record.
- production/caption_quality.py: caption synchronization and readability.
- production/google_drive_delivery.py: verified Drive delivery.
- examples/video-only-episode-manifest-v2.template.json: episode template.
- production/VIDEO_ENGINE_V2.md: detailed production contract.

## Local checks

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v
    python -m py_compile production/*.py

## GitHub Actions

- Video engine v2 CI runs compile, regression and contract tests.
- Render video-only episode v2 is manually dispatched with a populated v2
  manifest and supports preview or final.

The template contains placeholders intentionally. A real episode must first
receive its narration, word-level captions, licensed music, verified research,
approved Drive video IDs/checksums and human editorial QA before final release.
Final mode is fail-closed until those gates are present.

Preview is validation-only: its reproducibility receipt ends in `PREVIEW_COMPLETE` and is never a production publication. Only a `final` run with human editorial approval may reach `PRODUCTION_COMPLETE`.


