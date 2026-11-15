# Because Of This — Canonical Visual Editorial Lock

Status: active editorial lock; applies only to this project.

## Visual source of truth

The approved visual language is the cinematic-dread reference used by the validated Episode 001 and Episode 002 previews:

- photorealistic cinematic footage or clearly labeled cinematic reconstruction;
- each shot visibly enacts the current narration beat;
- continuity of subject, place, era, time, lighting, palette and consequence;
- 1080x1920 vertical, 60 fps, dark investigative atmosphere;
- no generic keyword-matched filler, no reused clips, no loops.

The audio-only EP005 Selpan candidate is quarantined technical evidence. Its inherited picture is not a style reference and is not release-authorized. Episode 006 v2/v7/v9/Realistic v10 experiments are not style authority.

## Editorial chain

`STORY -> HOOK -> AUDIO/TIMECODES -> BEATS -> SCENE CONTRACTS -> REVIEWED CLIPS -> MOTION -> CAPTIONS -> TRANSITIONS -> QA`

Never select a clip before defining what the viewer must see, understand and feel for that beat.

## Hook lock

The first 0-8 seconds must enter the real event immediately:

- 0-1s: visual/verbal interruption;
- 1-3s: factual premise;
- 3-8s: unanswered question and promised consequence.

No generic intro, exaggeration or frantic editing. The story must progress through
`CAUSE -> ESCALATION -> CONSEQUENCE -> WHY IT MATTERED`.

## Motion and transitions

Allowed only when motivated by the story and eased smoothly:

- restrained push-in, pull-out, pan, parallax or static hold;
- hard cut, motivated cross-dissolve/dissolve or dip-to-black;
- no random effects, shake, graphic overlays or technical diagrams.

## Voice and captions

- Direct Gemini TTS, model `gemini-3.8-flash-tts`, voice Charon, native US English;
- deep, controlled, restrained suspense; no Creative Claw or silent fallback;
- final narration is the master clock;
- word-level karaoke, maximum two lines, approved upper safe zone, white base with active word `#F04444`;
- em dash and en dash prohibited.

## Branding and endfilm

Use the transparent original Because Of This logo in its approved safe position. The story and narration end first. Then use the restrained identity/endfilm for approximately 5-6 seconds, followed by a dark fade to black; loop only when it improves the ending.

## Release gate

A technically valid audio candidate cannot promote a video when the visual scene contracts or visual style are unresolved. Human preview approval remains mandatory.


## Referência de clipes sem herança de overlays

Quando Borelli fornece um MP4 como referência de edição, ele pode definir apenas a sequência, a seleção e a continuidade dos clipes. O MP4 de referência nunca autoriza herdar legenda, karaokê, logo, posição, espaçamento, cor, tipografia, marca d'água ou outro elemento queimado na imagem.

A composição ativa é sempre reconstruída pela camada V2.1:

- logo: brand/because-of-this-wordmark-transparent.png, hash canônico validado;
- logo no vídeo: largura 360 px, eixo central, y=190;
- legenda: alinhamento 2, centralizada na faixa inferior, margin_v=650;
- máximo de duas linhas e até 42 caracteres por linha;
- karaokê por timestamps reais, ativo em #F04444;
- nenhum render pode aceitar os marcadores legados y=72, margin_v=320 ou logo 540/820.

Se a única fonte disponível já contiver esses overlays queimados, ela não é fonte de render final: é apenas referência visual. O render exige os clipes limpos ou os arquivos de origem para preservar a qualidade máxima.
