# Because Of This — E4 real-media integrity audit | 2026-11-04

**Scope: read-only technical validation of archived Episode 004, NOT new episode production.** Work performed against existing Drive assets with no update to original MP4 files, manifests, One Extra Minute, `main`, TTS or publishing systems.

## Independently executed checks

Directly streamed **12 actual MP4 files** referenced by `episodes/video-004/preview-manifest.json` from the connected Google Drive; verified them in an isolated runtime.

| Technical check | Actual result |
|---|---|
| SHA-256 calculated from downloaded bytes vs GitHub manifesto | **12 / 12 exact matches** |
| File size in bytes vs manifest | **12 / 12 exact matches** |
| FFprobe video metadata readable | **12 / 12** |
| FFmpeg independent samples at 25%, 50%, 75% | **36 / 36 readable frames** |
| Media files, archive or `episodes/` changed | **zero** |

This closes the **E4 technical identity check for this exact historical reference episode only**. SHA-256 agreement proves the downloaded object is byte-identical to the **manifest-declared object**, not that the original licensing source page served identical bytes.

## Review exceptions detected from the actual image pixels

1. **S01 vs S05 — same base USGS photograph in two edits**, with arrows embedded in S05 from the Commons reference. Normalized grayscale central-frame correlation **0.9720**. They are different files and URLs: source IDs and SHA-256 checks alone would miss the underlying-image repetition. Do **not** alter Episode 004. Future episodes require review/avoidance, not automatic approval.
2. **S02 vs S10 — dHash distance 7** suggested similarity but manual inspection shows different landscapes; normalized frame correlation **0.8769**, so a single coarse fingerprint should **not** automatically label them duplicates.
3. **S04 — semantic claim needs review**: the exact Pexels source-page description says *calm ripples* on water; extracted frames show water movement, not conclusive visual evidence of a rock hitting the water. Never rely on a stock filename or title as proof of the narrated action.

### New reusable E4 auditor

- `audits/e4_media_integrity_v11.py` accepts a manifest and already downloaded media root, checks actual byte hashes and sizes, probes duration/codecs/dimensions, decodes three frames per clip, and flags possible visual repetitions.
- Strict and bounded to 25 scenes; read-only, rejects traversal, never grants rights or production approval.
- **Fail closed**: visually similar/inconclusive material yields `E4_TECHNICAL_PASS_WITH_REVIEW` and CLI exit code **2**, requiring review. Corrupt/missing media yields `BLOCKED` and exit **1**. Only pure technical success exits **0**, and even that does not authorize commercial use.
- Tests synthesize disposable clips locally with FFmpeg, use no Drive/Gemini API and write no historical content.

## Current source-page rights evidence (E3 only)

12 source pages examined: 5 Mixkit clips explicitly with Stock Video **Free** commercial license; 3 individually named Pexels clips with **Free** license; 1 Pixabay clip displayed as free stock under the Pixabay Content License; 3 source works from USGS/Wikimedia Commons declared US public domain.

Primary pages:
- S01: https://www.usgs.gov/media/images/lituya-bay-1958
- S02: https://mixkit.co/free-stock-video/bay-landscape-aerial-shot-1940/
- S03: https://www.pexels.com/video/landslide-in-a-mountain-9354609/
- S04: https://www.pexels.com/video/stone-falling-into-lake-13723991/
- S05: https://commons.wikimedia.org/wiki/File:Lituya-Bay-overview-with-arrows.png
- S06: https://www.pexels.com/video/a-boat-traveling-on-the-water-with-a-cloudy-sky-20066901/
- S07: https://pixabay.com/videos/rain-trees-boat-fishing-boats-107910/
- S08: https://mixkit.co/free-stock-video/aerial-shot-of-a-huge-forest-full-of-trees-51103/
- S09: https://mixkit.co/free-stock-video/speedboat-returning-to-a-beautiful-bay-seen-from-the-sky-5007/
- S10: https://mixkit.co/free-stock-video/air-tour-around-a-huge-mountain-44613/
- S11: https://commons.wikimedia.org/wiki/File:Lituya_Bay_spit.jpg
- S12: https://mixkit.co/free-stock-video/aerial-view-of-a-mountain-top-43129/

**Not E5 / NOT READY**: this checks no future-story media; third-party releases, downstream derivative authorization, full-source-to-derivative authenticity, soundtrack use, mobile safe zones, final narration/captions and final human preview approval remain required. Existing historical material is never provisioned for reuse in new episodes.

**Status:** archived Episode 004 E4 bytes **PASS**, visual near-repetition **HUMAN REVIEW FLAG**, new production **BLOCKED**. Original Gemini TTS Charon unchanged.
