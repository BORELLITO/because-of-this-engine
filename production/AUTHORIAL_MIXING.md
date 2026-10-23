# Authorial audio mix and release gate

The renderer keeps narration as the timing master. A licensed music bed is optional for previews and required for final release when the episode manifest sets `require_music: true`.

## Manifest contract

Add the track only after checking its actual terms and storing its provenance:

```json
{
  "require_music": true,
  "music": {
    "path": "assets/music/suspense-bed.wav",
    "license": "youtube_audio_library",
    "commercial_use": true,
    "attribution": "",
    "volume": 0.08
  }
}
```

The file must exist inside the episode directory. The license field and explicit commercial-use permission are required. Creative Commons tracks also require attribution text. Keep source URL, title, attribution requirement, verification date and Content ID risk in the music license register. The engine does not decide whether a license applies to a particular upload.

## Mix behavior

- Music loops or trims to the narration duration.
- The default music gain is 0.08; the manifest can set a value from 0 to 0.25.
- Sidechain compression ducks music while narration is present.
- Narration and music are mixed with a peak limiter.
- The existing no-music preview path remains available.
- Final preflight blocks before approval when required music or its license contract is missing.

The presence of licensed music does not establish monetization eligibility. Review YouTube's current Audio Library terms and track-specific attribution before use. YouTube says Audio Library music can be monetized in YPP and identifies its own library as the only music it knows to be copyright-safe: https://support.google.com/youtube/answer/3376882

## Verification

Run the local unit suite with `python -m unittest discover -s tests -v`. A 1-second FFmpeg integration smoke test also verifies that the sidechain mix produces H.264/AAC output at the expected audio sample rate. Keep a preview and human listening review before final approval.
