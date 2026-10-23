# Authorial rendering

This is the independent rendering layer for Because of This. It does not connect
to or modify Capta Pronto, Corte Fino, Publisher, or Creator.

## Official pipeline

1. close the factual script and narration;
2. mark beats, pauses, reveal and payoff;
3. build the visual plan and provide reviewed authorial images;
4. render a low-cost `preview`;
5. inspect the preview on a mobile screen;
6. create an approval file bound to the exact manifest hash;
7. render `final`;
8. run the release validator;
9. deliver the validated package.

A final render without a matching preview approval is blocked.

## Motion and transitions

The official renderer uses deterministic, subpixel-stable motion. Supported
movement types are `slow_push_in`, `slow_pull_out`, directional pans,
`focus_reframe`, `static_hold` and `subtle_rotation_push_in`. The motion engine
chooses a safe default from the narrative metadata when a scene does not specify
one. It does not use random movement and never applies shake/glitch effects.

Each scene may provide:

```json
"motion": {
  "type": "slow_push_in",
  "easing": "smoothstep",
  "intensity": 1.0,
  "focus": {"x": 0.5, "y": 0.5}
}
```

Transitions default to a short crossfade for backward compatibility. A scene
may set `transition.type` and `transition.duration` when the beat warrants it.
The validator rejects invalid values and three identical motions in a row.

## Modes

- `preview`: 1080x1920, fast review render;
- `final`: 2160x3840, delivery render.

## Manifest contract

The release manifest must provide `schema_version: "1.1"`, `video_id`,
`audio.path` pointing to mono 24 kHz 16-bit WAV, unique scenes, captions,
output path, and provenance sidecars. For the strongest gate set, enable
`require_visual_plan: true` and `require_music: true` only after the episode has
a real licensed music entry.

Every scene should contain `story_beat`, `visual_intent`, `image_type` and
`emotion`. Images are illustrations/reconstructions unless independently
verified; the engine must never present generated pixels as documentary proof.

## Validation and workflow

```bash
python production/render_authorial_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview --validate-only

python production/validate_authorial_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview
```

The validator checks image readability, provenance, visual-plan metadata,
motion variety, timeline-to-narration, caption timing/identity, output
dimensions, H.264/AAC streams and optional music licensing. `PREVIEW_VALIDATED`
is not `APPROVED`; a human mobile review and exact approval hash are required.

## Operational rule

Preview first, final second. A failed render never replaces an existing output:
the renderer writes to a temporary file and promotes it only after a successful
mux. Providers never fall back silently.
