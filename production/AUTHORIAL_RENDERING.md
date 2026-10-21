# Authorial rendering

This is the independent rendering layer for Because of This. It does not connect to or modify Capta Pronto, Corte Fino, Publisher, or Creator.

## Official pipeline

1. build the episode manifest with schema `1.1`;
2. provide the narration, captions, and reviewed image assets;
3. run a low-cost `preview`;
4. inspect the preview on a mobile screen;
5. create an approval file bound to the exact manifest hash;
6. run `final`;
7. run the release validator;
8. deliver the validated package.

A final render without a matching preview approval is blocked.

## Modes

- `preview`: 1080x1920, fast review render
- `final`: 2160x3840, delivery render

The renderer applies only:

- slow deterministic zoom;
- short fade crossfades;
- external ASS captions;
- narration muxing;
- vertical H.264/AAC export.

There is no shake effect and no image regeneration during assembly.

## Manifest contract

The release manifest must provide:

- `schema_version: "1.1"`;
- `video_id`;
- `script.path`;
- `audio.path` pointing to mono 24 kHz 16-bit WAV;
- one or more scenes with unique `scene_id`, `image`, `duration`, and optional `zoom_end`;
- `captions.path`;
- `approval.path`;
- `output.path` containing `{mode}`;
- `require_captions: true`;
- `require_provenance: true`.

Each image must have a sidecar JSON containing provider/model/prompt/style and generation provenance.

All referenced files must remain inside the episode directory. Missing files, invalid audio, missing captions, unsafe zoom values, path escapes, duplicate scene IDs, or invalid durations stop the render before FFmpeg starts.

## Asset ingestion

For images generated outside GitHub, use the provenance-safe ingest command:

```bash
python production/ingest_authorial_asset.py \
  --source /path/to/generated.png \
  --output examples/assets/S01.png \
  --scene-id S01 \
  --provider manual-approved-imagegen \
  --model unknown \
  --prompt-pack examples/mars-climate-orbiter-authorial-prompt-pack-v1.json
```

The command copies the existing image and creates the required JSON sidecar. It
does not generate, improve, or silently replace visual content.

## Validation

The renderer checks the input contract. After FFmpeg completes, run:

```bash
python production/validate_authorial_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview
```

The release validator checks:

- image readability and minimum size;
- image provenance sidecars;
- caption timing and overlap;
- caption/script word identity when a script is provided;
- output dimensions;
- H.264/AAC streams;
- output duration against narration;
- presence of both video and audio.

`PREVIEW_VALIDATED` is not `APPROVED`. A human mobile review and an exact approval hash are required before final delivery.

## Creating approval

After reviewing the preview on a phone, create the approval file:

```bash
python production/create_preview_approval.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --reviewer Borelli \
  --output approvals/mars-climate-orbiter-001-preview-approved.json \
  --approved
```

The command binds approval to the exact manifest, images, audio, captions, and
preview MP4. Any later input change invalidates the approval.

## GitHub Actions

Run **Render authorial episode** manually and select `preview` first. The workflow blocks `final` unless the approval file exists and matches the current manifest hash. The validated package is uploaded only after the release validator passes.

The example manifest is a contract template. Its audio and image assets must be supplied in `examples/assets/` before rendering.

## Operational rule

Preview first, final second. A failed render never replaces an existing output because the renderer writes to a temporary file and promotes it only after a successful mux.
