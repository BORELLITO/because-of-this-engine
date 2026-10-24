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
static narrative image fields and any repeated source/checksum/animation
fingerprint inside the episode. A clip shorter than its assigned beat is
blocked; clips are never looped to fill time.

## Clip quantity and visual storytelling

New episodes use an adaptive clip policy: 10 unique clips is the hard
minimum, 12–16 is the target range, and 18 is the hard maximum for a
60–75-second story. The story is divided into narrative beats, and each beat
receives its own fresh video asset. The policy rejects under-edited episodes
unless the manifest explicitly marks an already approved pilot baseline.

Candidate discovery ranks exact semantic matches first, then near,
explanatory, symbolic and atmospheric fallbacks. A fallback is never allowed
to replace a scene silently: the manifest records its match class and score.
The final contract also rejects repeated source pages and duplicate animation
fingerprints, even when filenames or checksums differ.

## Timeline and edit

Narration is the master clock. Scene durations are allocated to the measured
narration while respecting each source video's usable duration, a 2–20-second
visual-beat range and transition overlap. Each scene is trimmed from a real
video stream, stripped of source audio, scaled/cropped to 9:16 and joined with
deterministic transitions. Hard cuts remain effectively instantaneous;
crossfades and dissolves are used only when the edit calls for continuity.
Preview is 1080×1920 and final is 2160×3840, both at 25 fps.

Captions are generated from the same narration and remain external ASS
captions until the final mux. The brand HUD uses the original full wordmark in the upper-right safe area,
with a fixed symmetric right margin and chroma-key removal of its embedded
black plate. The legacy `|B` text mark remains only as a fallback when the
canonical logo asset is unavailable.

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
rendered media, captions and black/freeze/silence anomalies. The canonical
G0–G12 report is emitted before render, after release QA and after verified
delivery/cleanup; a blocked gate cannot be silently skipped. After the first verified delivery, the engine
writes a reproducibility manifest, performs scoped cleanup, marks cleanup
complete, and re-delivers the completed manifest.

A final job may declare `PRODUCTION_COMPLETE` only after all of these are true:
validated media, verified Drive delivery, reproducibility manifest, scoped
cleanup, and final-manifest re-delivery.
