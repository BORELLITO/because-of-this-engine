# Because of This Engine v2.0

The production path is **video-only**. Narrative scenes cannot contain still
images. The only supported flow is:

`Cloud Browser discovery/review → Google Drive approved-assets staging → GitHub asset hydration → FFmpeg render → release QA → Google Drive validated delivery`

## Asset approval contract

Every scene records:

- provider (`mixkit`, `pixabay`, `pexels`, `drive` or an approved original video source);
- source page URL and explicit licence;
- Drive file ID when the asset is staged outside Git;
- SHA-256 and optional perceptual hash;
- `rights_status: APPROVED` and `approved_for_render: true`;
- semantic `visual_match`, `match_score` and `visual_truth`.

The renderer blocks missing provenance, stale checksums, unapproved assets,
static narrative image fields and any repeated asset/checksum/perceptual hash
inside the episode. A clip shorter than its assigned beat is blocked; clips
are never looped to fill time.

## Timeline and edit

Narration is the master clock. Scene durations must total the narration within
350 ms. Each scene is trimmed from a real video stream, stripped of source
audio, scaled/cropped to 9:16 and joined with deterministic transitions.
Preview is 1080×1920 and final is 2160×3840, both at 25 fps.

Captions are generated from the same narration and remain external ASS
captions until the final mux. The brand HUD uses the `|B` watermark during
the story; the full wordmark belongs on title/opening/closing cards when a
clean transparent master is available.

## Audio

Narration is always primary. Optional suspense music is licensed, mixed with
sidechain ducking and normalized to a voice-first target around -15 LUFS with
true peak limited near -1 dBTP. Final mode requires the music contract.

## Commands

```bash
python production/google_drive_assets.py --manifest <episode>/manifest.json
python production/render_video_episode.py --manifest <episode>/manifest.json --mode preview
python production/validate_video_release.py --manifest <episode>/manifest.json --mode preview
```

The GitHub workflow is `.github/workflows/render-video-episode.yml`. This v2 contract is the authoritative production path. Image-based manifests
are rejected by the video-only contract.

## Job identity, state and final receipt

Every episode has a stable `job_id`. The state machine records the accepted
stage transitions and refuses to reuse a state file after the manifest
fingerprint changes. A rerun of the same job uses the same Drive delivery
folder and refuses to overwrite a file owned by another job.

The final release requires verified research references, complete asset
provenance, word-level caption evidence, and an explicit human
`editorial_qa.status=PASS`. The release validator independently rechecks the
rendered media and captions. After the first verified delivery, the engine
writes a reproducibility manifest, performs scoped cleanup, marks cleanup
complete, and re-delivers the completed manifest.

A final job may declare `PRODUCTION_COMPLETE` only after all of these are true:
validated media, verified Drive delivery, reproducibility manifest, scoped
cleanup, and final-manifest re-delivery.
