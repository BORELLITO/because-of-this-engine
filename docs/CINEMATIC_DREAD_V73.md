# Cinematic Dread — versão visual para aprovação

A branch V7.3 Atmosphere acrescenta um **diretor de atmosfera por cena**
sem alterar `Charon`, `Gemini TTS`, as legendas, o logotipo, a licença
do material, os vídeos de Drive ou o motor canônico.

## Fluxo técnico já ligado

`production.cinematic_dread.plan` interpreta story_beat e overrides →
`grade_for_scene` fornece cor, contraste e textura por cena →
`production.render_video_episode.render_scene` grava clipes tratados →
`music_filter` acompanha a tensão sem deixar a trilha dominar a narração →
`production.atmosphere_qa.inspect` extrai evidência real do MP4 →
`validate_video_release` só aceita relatório íntegro com SHA-256.

As alterações de cor/grão ocorrem **antes** das legendas e do logo.
Isso evita manchar os textos ou adicionar grafismos estranhos aos clipes.

## Gates

- **Opt-in e rollback:** `atmosphere` ausente = render absolutamente idêntico
  ao contrato anterior.
- **Planejamento:** preset aprovado, IDs existentes, motivos para overrides,
  intensidade inteira 1–4 e nenhum efeito de objeto inventado.
- **Luminância:** samples reais de dentro do quadro; pontos escuros e
  highlights excessivos bloqueiam. O gate preserva visibilidade, mas
  **não certifica sozinho que o vídeo ficou assustador**.
- **Áudio:** os ganhos do bed variam de 0,84 a 1,12 vezes o volume
  já existente, com sidechain intacto e sem alterar a voz.
- **Aprovação:** `director_review=PENDING` só permite provas técnicas;
  para `final` precisa ser `APPROVED` e apresentar o relatório da mídia
  exata. Publicação continua manual, sob os gates anteriores.

## Testes sem vídeo novo

```bash
PYTHONPATH=. python -m unittest -v tests.test_cinematic_dread_v73 tests.test_cinematic_dread_render_v73 tests.test_dread_ffmpeg_smoke
```

O storyboard do elevador será avaliado antes de habilitar a atmosfera no
manifesto ativo. Renderizar novamente um vídeo inteiro **não é necessário**
para os testes da arquitetura, apenas para a aprovação visual posterior.
