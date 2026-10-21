# Authorial rendering

The independent render layer uses FFmpeg. It is not connected to Capta Pronto, Corte Fino, Publisher, or Creator.

## Modes

- `preview`: 1080x1920, fast review render
- `final`: 2160x3840, delivery render

The renderer always preserves the same scene order and applies only:
- slow deterministic zoom
- short fade crossfades
- optional external ASS captions
- narration muxing
- vertical H.264/AAC export

There is no shake effect and no image regeneration during assembly.

## Manifest contract

The render manifest must provide:
- `video_id`
- `audio.path` pointing to a mono 24 kHz 16-bit WAV
- one or more scenes with `scene_id`, `image`, `duration`, and optional `zoom_end`
- optional `captions.path`
- optional `output.path`

All referenced files must live inside the episode directory. Missing files, invalid audio, unsafe zoom values, path escapes, or invalid durations stop the render before FFmpeg starts.

## Local command

```bash
python production/render_authorial_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview
```

Use `--mode final` only after the preview is approved.

## GitHub

Run the **Render authorial episode** workflow manually. Select `preview` first. The rendered MP4 is uploaded as an Actions artifact. The example manifest is a contract template; its assets must be supplied in the referenced episode asset folder before rendering.

## Operational rule

Preview first, final second. A failed render never replaces an existing output because the renderer writes to a temporary file and promotes it only after a successful mux.
