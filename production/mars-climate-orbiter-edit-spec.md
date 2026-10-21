# BECAUSE OF THIS — Mars Climate Orbiter

## Production status

This is the independent production specification for the first Short. It does
not modify Capta Pronto, Corte Fino, Publisher, Creator, or any other GitHub
engine.

| Item | Status | Evidence / next gate |
|---|---|---|
| Script | CANONICAL / reconciled | Transcript is also stored in `examples/mars_climate_orbiter.txt` and bound by SHA-256 |
| Voice | GENERATED | Google AI Studio, Charon |
| Audio duration | VALIDATED | Local Charon WAV, PCM 24 kHz mono, 58.36s |
| Visual source | RENDERED | NASA-backed 1080×1920 assets plus controlled motion source, 30 fps |
| Beat map | EXECUTED | Scene timing aligned to the approved script and real duration |
| Captions | RENDERED / TRANSCRIPT_BOUND | ASS caption layer, phrase-level timing, mobile-safe styling |
| Final mix | TECHNICALLY_VALIDATED | Voice-first mix; -18.3 LUFS integrated, -1.0 dBFS true peak |
| Final export | TECH_VALIDATED / REVIEW_REQUIRED | H.264 + AAC, 1080×1920, 58.37s |

The final MP4 is now rendered. Caption timing is sentence/phrase-level rather
than an independently generated word-level ASR transcript; this remains the
one editorial limitation to improve if a word-timing transcript becomes
available.

## 1. Pre-production verdict

The story is strong enough for a Short: a long mission, an apparently tiny
unit mismatch, a physical consequence, and a systems-level lesson. The main
editorial risk is oversimplification. The unit mismatch is a documented cause
of the navigation error, but the failure also involved communication and
systems-engineering problems. The edit must preserve both facts.

The approved narrative arc is:

`journey → invisible mismatch → trajectory divergence → fatal approach → silence → systemic lesson`

The current 58-second length is viable for this script. It is not too short,
but it has no room for an intro, a logo animation, or a generic CTA. The
senior-editor motion pass is intentionally sparse: each scene receives one
eased camera move, while hard cuts remain the default transition.

## 2. Approved narration

> NASA’s Mars Climate Orbiter traveled for nine months to reach Mars. Then, during its arrival, contact disappeared.
>
> The cause sounds almost impossible: two parts of the mission were using different units.
>
> Ground software reported thruster forces in pound-seconds. Navigation expected metric units: newton-seconds. So the force data was interpreted incorrectly, and the spacecraft’s calculated path drifted from its real one.
>
> When the orbiter reached Mars on September 23, 1999, it passed too close to the planet. NASA later concluded it likely burned up in the Martian atmosphere.
>
> But the unit mismatch was only part of the failure. Investigators also found communication and systems-engineering problems that kept warning signs from being resolved in time.
>
> A spacecraft crossed millions of miles, and a mismatch between pounds and newtons helped decide its fate.
>
> Because of this, the lesson was bigger than “check your units.” Every team had to understand how its data affected the whole mission.

## 3. Beat map

The timecodes below are editorial estimates from the 58-second render. They
must be replaced by word-level timestamps from the actual WAV before final
rendering.

| Beat | Est. time | Narration function | Emotion | Visual job | Retention reason |
|---|---:|---|---|---|---|
| B1 | 0.00–9.40 | Nine-month journey; contact disappears | Intrigue → alarm | Show Mars, trajectory, then remove the signal | Immediate unanswered failure |
| B2 | 9.40–15.00 | “Different units” reveal | Surprise | Split the same force into two incompatible systems | Concrete mystery |
| B3 | 15.00–27.50 | Incorrect interpretation moves path | Tension | Calculated path separates from actual path | Visible cause-and-effect |
| B4 | 27.50–37.80 | Arrival and too-close pass | Dread | Narrow approach corridor and atmospheric burn | Physical consequence |
| B5 | 37.80–47.30 | Unit mismatch was not the whole story | Reassessment | Signal line weakens; warning markers remain unresolved | Prevents simplistic “one mistake” ending |
| B6 | 47.30–52.40 | Millions of miles; pounds vs newtons | Weight / tragedy | Pull back from spacecraft to Mars | Emotional compression |
| B7 | 52.40–58.00 | Systems lesson | Clarity | Cause → event → consequence relationship | Memorable takeaway without CTA |

## 4. Retention map and drop-off risks

| Window | Why the viewer continues | Risk | Countermeasure |
|---|---|---|---|
| 0–1s | Mars mission already in danger | Generic space opening | Start on a spacecraft approaching a large Mars edge; no logo |
| 1–3s | “Contact disappeared” is unresolved | First image too abstract | High contrast, one focal object, signal line visibly cuts |
| 3–5s | Cause is promised | Overlong setup | Hard cut to the unit split on “different units” |
| 5–10s | Viewer wants the impossible explanation | Dense technical words | Use a simple visual comparison, not a fake NASA UI |
| 10–20s | Mechanism is becoming clear | Repeated static panels | Move from labels to two diverging paths |
| 20–35s | Consequence approaches | Payoff feels delayed | Keep Mars growing in frame; narrow the approach corridor |
| 35–48s | Nuance changes the interpretation | “More problems” sounds like a list | Use one visual interruption: signal disappears, warning markers remain |
| 48–55s | Emotional summary | Generic ending | Pull back to the whole mission, not another close-up |
| 55–58s | Lesson | Moralizing or CTA | Hold a clean final frame; no subscription ask |

## 5. Direction, look, and factual visual policy

- Format: vertical 9:16, 1080×1920 working master; do not upscale to 4K unless
  the final source assets justify it.
- Palette: deep navy and charcoal for space/uncertainty, restrained Mars
  orange for consequence, cool cyan for navigation/signal, warm amber for
  the unit mismatch. Keep the grade subtle.
- Visual language: editorial reconstruction and information graphics. The
  graphics are illustrative and must not look like recovered NASA telemetry.
- Never invent an archival screenshot, NASA interface, document, quote, or
  mission photograph. If a real source image is later added, identify its
  source in the asset manifest.
- No baked captions in generated art. Captions are a separate edit layer.
- Brand: a tiny BECAUSE OF THIS mark only in a safe corner after the hook;
  no opening bumper.

## 6. Storyboard / scene list

| Scene | Time (provisional) | Narration / beat | Visual type | Camera / motion | Transition | Caption intent | SFX / music |
|---|---:|---|---|---|---|---|---|
| S01 | 0.00–9.40 | Nine months; contact disappears | Editorial space reconstruction | Wide Mars edge; slow push toward orbiter; signal line fades at “disappeared” | Hard cut on disappearance | Short blocks; highlight `NINE MONTHS`, `CONTACT DISAPPEARED` | Low space bed; one restrained radio dropout |
| S02 | 9.40–15.00 | Different units | Cause/effect graphic | Two panels converge, then amber/cyan mismatch separates | Motivated cut on `different units` | Highlight `DIFFERENT UNITS` | Tiny low tick; music remains minimal |
| S03 | 15.00–27.50 | Pound-seconds vs newton-seconds; path drifts | Technical diagram / map | Slow pan along two trajectories; 4–6% push-in | Match cut from unit split to path split | Highlight `POUND-SECONDS`, `NEWTON-SECONDS`, `DRIFTED` | Subtle pulse rising; no glitch |
| S04 | 27.50–37.80 | Too-close pass; likely burn-up | Editorial reconstruction | Mars grows; approach corridor tightens; slight downward reframe | Hard cut on `September 23, 1999` | Highlight date and `TOO CLOSE` | Low boom under reveal; brief micro-silence before “burned up” |
| S05 | 37.80–47.30 | Other communication / systems problems | Signal and warning abstraction | Signal arcs collapse; warning markers remain unresolved; motion reduces | L-cut narration across image change | Highlight `ONLY PART`, `WARNING SIGNS` | Radio noise recedes; music drops one layer |
| S06 | 47.30–58.00 | Consequence and system lesson | Wide consequence image with clean causal hold | Pull back from orbiter to full Mars; hold the final causal frame | Hard cut or restrained dissolve, depending on audio | Highlight `MILLIONS OF MILES`, `THE WHOLE MISSION` | Single low impact, then quiet release |

## 7. Image sourcing / asset queue

Generate in this order only if higher-quality assets are needed:

1. **CRITICAL:** S01 hook (orbiter, Mars edge, disappearing signal).
2. **CRITICAL:** S04 approach / likely atmospheric burn.
3. **IMPORTANT:** S03 trajectory divergence graphic.
4. **IMPORTANT:** S05 signal and unresolved warning abstraction.
5. **SUPPORTING:** S02 unit comparison and S06/S07 consequence graphics.

The default free path now uses the NASA Image and Video Library adapter. It
downloads a semantically matched source image, converts it to 1080×1920, and
writes a provenance sidecar. The source is editorially framed; it must not be
presented as mission telemetry or as proof of the exact event unless the item
itself supports that claim. The optional generative adapters remain opt-in.

### Prompt rules for generated art

Use a consistent editorial reconstruction style: realistic but clearly
illustrative, vertical composition, deep navy space, Mars orange rim light,
restrained cyan instrumentation glow, cinematic contrast, clean negative space
for captions, no logos, no readable text, no fake interface, no watermark,
no invented archival look.

For S01: “A small 1990s-era interplanetary spacecraft approaching the dark limb
of Mars, a thin radio signal beam fading into space, wide vertical composition,
editorial reconstruction, physically plausible spacecraft proportions, deep
navy and Mars-orange palette, clear lower-third negative space, no text, no
logo, no NASA insignia.”

For S04: “An illustrative interplanetary probe passing dangerously low over
Mars, thin atmospheric glow along the limb, spacecraft remains small enough to
show scale, suspenseful but factual editorial reconstruction, no explosion,
no text, no logo, no archival claim.”

For S03: “Minimal technical editorial graphic showing one spacecraft and two
clean trajectory lines slowly diverging near Mars, one cyan and one amber,
dark navy background, no readable labels or fake telemetry, vertical safe
composition, crisp geometry.”

Inspect every generated image for anatomy/objects/text/reflections/lighting
errors before use. Any critical asset with a visible artifact blocks final
rendering.

## 8. Asset manifest

| Asset ID | Scene | Type | Source | Status | License / provenance |
|---|---|---|---|---|---|
| A01 | S01 | Mars Climate Orbiter source image | NASA adapter | GENERATED / REVIEW_REQUIRED | Source URL and item metadata in sidecar; verify credits |
| A02 | S02 | Mission-control source image | NASA adapter | GENERATED / REVIEW_REQUIRED | Source URL and item metadata in sidecar; verify credits |
| A03 | S03 | Mars Climate Orbiter source image | NASA adapter | GENERATED / REVIEW_REQUIRED | Source URL and item metadata in sidecar; verify credits |
| A04 | S04 | Mars source image | NASA adapter | GENERATED / REVIEW_REQUIRED | Source URL and item metadata in sidecar; verify credits |
| A05 | S05 | Mission-control source image | NASA adapter | GENERATED / REVIEW_REQUIRED | Source URL and item metadata in sidecar; verify credits |
| A06 | S06 | Mars source image | NASA adapter | GENERATED / REVIEW_REQUIRED | Source URL and item metadata in sidecar; verify credits |
| VO01 | All | Narration | Google AI Studio / Charon | GENERATED / LOCAL | Manual collection; model ID remains unknown |
| MUS01 | All | Music bed | FFmpeg lavfi procedural | GENERATED / LOCAL | Original deterministic bed; hash in episode manifest |
| SFX01 | S01/S05 | Radio dropout / signal texture | Not selected | NOT EXECUTED | Must be sourced or generated with permission |

## 9. Motion and transition plan

Motion is deliberately sparse and is now executable in
`production/build_mars_visual_ai.py` as `senior-editor-v1`. S01 and S04
receive the strongest push-in; S05 and S06 reduce motion so the loss and lesson
can land.

| Scene | Start scale | End scale | Position | Easing | Reason |
|---|---:|---:|---|---|---|
| S01 | 1.00 | 1.06 | center → slightly right | ease-in-out | Move toward the unresolved arrival |
| S02 | 1.00 | 1.02 | left/right split stays stable | ease-out | Let the mismatch be understood |
| S03 | 1.00 | 1.05 | pan left → right along paths | ease-in-out | Follow divergence |
| S04 | 1.02 | 1.09 | center → lower Mars limb | ease-in | Escalate approach danger |
| S05 | 1.04 | 1.01 | signal center → empty space | ease-out | Remove motion as contact vanishes |
| S06 | 1.08 | 1.00 | pull back to whole Mars | ease-in-out | Restore scale and consequence |
| S06 | 1.00 | 1.00 | locked | none | Give the final insight room |

Default transition is a hard cut. The only candidate dissolve is S05→S06,
and it should remain a hard cut if the narration has a strong consonant or
impact there. No random glitch, shake, or transition pack.

## 10. Caption plan

- English captions, one or two short semantic lines, mobile-safe lower third.
- White primary text with one restrained amber highlight per block.
- Highlight only numbers, consequence words, unit names, or the reveal.
- Never let captions cover Mars, the spacecraft, or the causal graphic.
- Final timing must come from actual WAV word boundaries. The current scene
  timecodes are not caption timings.

## 11. Music, SFX, and mix plan

Music states: `HOOK minimal tension → CONTEXT restrained pulse → BUILD low
pressure → REVEAL brief impact → PAYOFF quiet release`.

Mix target is voice first. Keep narration intelligible on a phone speaker;
duck music under speech and remove decorative SFX before lowering the voice.
Use silence around the contact-loss and burn-up moments. No SFX on every cut.
Final loudness and true-peak values are to be measured after the WAV is
attached; do not normalize a missing audio file by guesswork.

## 12. Timeline / EDL logic

The final edit must contain, for each scene: `TIME_IN`, `TIME_OUT`, `ASSET_ID`,
`TRANSFORM`, `TRANSITION`, `AUDIO_CUE`, and `CAPTION_ID`. The authoritative
source for `TIME_IN/TIME_OUT` is the narration transcript, not the provisional
scene lengths. Audio-led cuts should occur on “different units”, “drifted”,
“September 23, 1999”, “burned up”, “only part”, and “Because of this”.

## 13. Quality gates

Critical gates: `SCRIPT_SYNC_OK`, `AUDIO_SYNC_OK`, `VISUAL_RELEVANCE_OK`,
`CAPTIONS_OK`, `MIX_OK`, `MOBILE_OK`, `PAYOFF_OK`, `EXPORT_OK`.

Additional gates: `IMAGE_QUALITY_OK`, `CONTINUITY_OK`, `MOTION_OK`,
`TRANSITIONS_OK`, `MUSIC_OK`, `SFX_OK`, `BRAND_OK`, `SAFE_ZONES_OK`,
`FACTUAL_VISUAL_OK`, `RETENTION_OK`.

`TRANSCRIPT_IDENTITY_OK`, `CAPTIONS_OK`, `MIX_OK`, and `EXPORT_OK` are passed for
the rendered draft. Word-level ASR is not implemented. A final human
mobile-speaker watch remains required before publishing.

## 14. Red-team findings and corrections

1. **Risk:** viewer remembers only “NASA forgot units”.
   **Correction:** keep the communication and systems-engineering sentence in
   S05 and show unresolved warning markers rather than another unit graphic.
2. **Risk:** factual source images feel disconnected from the narrative.
   **Correction:** keep scene-specific NASA queries, preserve provenance, and
   use restrained motion/reframing rather than decorative effects.
3. **Risk:** estimated timings drift from the real Charon read.
   **Correction:** attach the WAV and derive word-level timestamps before
   captions or final cuts.
4. **Risk:** fake “NASA” interface implies evidence.
   **Correction:** use editorial reconstruction; no agency logo or invented
   telemetry.
5. **Risk:** music masks technical nouns.
   **Correction:** voice-first ducking and phone-speaker test are release gates.

## 15. Simplification pass

Do not add a CTA, logo intro, extra scene, glitch pack, or more than one major
SFX per narrative turn. The video becomes stronger by clarifying the existing
cause → event → consequence chain, not by increasing effect count.

## 16. Current scorecard (draft only)

These are editorial diagnostic scores, not performance predictions:

| Dimension | Score | Reason |
|---|---:|---|
| Hook visual | 72 | Clear Mars/trajectory concept; needs stronger final hook asset |
| Script ↔ visual match | 78 | All major beats represented; timing still provisional |
| Audio sync | 78 | Real WAV is present; timing is phrase-level, not word-level ASR |
| Visual quality | 64 | Clean procedural draft, not final cinematic asset set |
| Continuity | 82 | Palette and spacecraft language are consistent |
| Pacing | 76 | 58s works; exact pauses still unmeasured |
| Motion | 68 | Senior-editor motion plan is implemented; mobile review remains |
| Transitions | 70 | Hard-cut structure is appropriate; audio-led validation pending |
| Captions | 76 | Readable and safe; final word-level polish remains possible |
| Mix / mobile | 78 | Voice-first mix, peak -1.0 dB; phone-speaker listening still recommended |
| Payoff | 80 | Systems lesson is stronger than a one-cause moral |
| Overall professionalism | 63 | Production architecture is sound; final audio and motion are the gates |

## 17. Required next action

The audio was successfully collected from the existing AI Studio player and the
independent GitHub workflow has produced the six source assets plus the motion
source. The next human gate is to inspect the six frames and watch the motion
source once on a phone speaker before approving a final captioned render.
