# Because of This Engine v2.0 — Visual Contract 2.2

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


## Visual story semantic gate

Every scene is tied to a canonical `narration_excerpt` and a reviewed
`visual_semantics` contract. The contract separates subject, action,
environment, object, mood and composition. Asset evidence is recorded in the
same dimensions, so a clip is judged against the complete narrated beat.

Every scene must also declare visual_semantics.narrative_anchors.direct_required
and minimum_direct. These are concrete events or entities that the reviewed
clip must visibly contain. Symbolic footage may support mood, time or uncertainty,
but it cannot replace a direct narrated event such as demolition, running,
pointing or recording. Missing direct anchors block the scene before rendering.

The research queue generates focused query variants from those dimensions and
keeps rejected candidates visible for audit. A forbidden concept (for example,
a medical vial in a hotel scene) blocks the candidate. A near, symbolic or
atmospheric fallback is allowed only when explicitly declared and never silently
promoted to an exact match. Keyword-only matching is disabled.

The visual story QA gate runs before narration/rendering and emits one result
per scene with coverage, missing anchors and forbidden hits. This makes a
mismatched clip a pipeline error instead of a subjective problem discovered
only after watching the final video. It reports every blocked scene in one pass.
Explicit negations are handled as context: "no person" becomes an empty or
unoccupied search intent, while the forbidden concepts remain hard blockers.
Editorial review notes are never used as visual evidence, preventing a note
such as "not a guard" from creating a false match.

## Story intelligence and evidence

Before asset search, the manifest must contain a story graph with stable
entities, aliases, causal beats, temporal states and a visual motif for every
scene. Each scene's narration excerpt is then matched as an ordered,
non-overlapping subsequence of the canonical script. Missing paragraphs,
duplicated excerpts and out-of-order beats block the job.

After Gemini TTS and Vosk forced alignment, the same gate attaches real
word-time spans to every scene. The renderer uses those spans as its master
clock; it does not proportionally stretch scenes away from the words being
spoken. The alignment report is required before validate-only or render.

A semantic match is not pixel proof. Final release evidence must include the
reviewer, review timestamp and method, at least three sampled timestamps,
observed subjects/actions/environments/objects, and an action window for
motion-sensitive beats. Source URLs, titles and editorial notes can guide
discovery but cannot satisfy a final visual anchor.

## Cinematic suspense and brand scale

Final renders use the locked investigative_noir_suspense preset. The layer applies
a controlled dark grade, cooler shadows, restrained warm highlights and a
moderate noir vignette to the video layers only. Captions, the original logo
and the loop card are composited afterward, so readability and brand colors are
not crushed by the grade. The renderer validates all grade parameters against
safe editorial ranges and blocks final output when the suspense layer is absent.

The canonical logo is rendered at 432px wide, 20% larger than the previous
360px lock, while retaining the same top-right safe-area margins and opacity.
The final contract rejects a smaller logo width.

## Timeline and edit

Narration is the master clock. Scene durations are allocated to the measured
narration while respecting each source video's usable duration, a 2–20-second
visual-beat range and transition overlap. Each scene is trimmed from a real
video stream, stripped of source audio, scaled/cropped to 9:16 and joined with
deterministic transitions. Hard cuts remain effectively instantaneous;
crossfades and dissolves are kept short for continuity, and dip-to-black is
reserved for deliberate beat changes. The contract blocks consecutive
dip-to-black transitions and any non-hard-cut transition longer than 0.30
seconds.
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
