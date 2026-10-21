# Authorial pipeline upgrade status

## Implemented

- canonical authorial manifest schema `1.1`;
- external captions required for release;
- duplicate scene and schema checks;
- release validator for images, provenance, captions, duration, codecs, and streams;
- preview approval gate bound to manifest, episode inputs, and preview output;
- provenance-safe image ingestion;
- preview/final workflow with fail-closed validation;
- contract-only CI validation;
- regression tests for approval and caption gates.

## Still requires episode assets

The Mars example remains a contract template until these files are supplied under
`examples/assets/`:

- `mars-climate-orbiter-charon.wav`;
- `S01.png` through `S06.png`;
- one JSON provenance sidecar for each image.

Do not create an approval file before reviewing the preview on a phone.

## Current honest status

The code path is upgraded and guarded, but no new authorial MP4 is claimed as
validated until a real asset-complete preview is rendered and passes the release
validator.
