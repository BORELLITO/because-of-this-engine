# BECAUSE OF THIS — Motor Canônico V2.1

> **Fonte única de verdade:** `production/active_engine_policy.json`  
> **Entrypoint único normal:** `production/canonical_entrypoint.py`  
> **Guard de singleton:** `production/v21_singleton_guard.py`

Este repositório contém o único motor canônico do canal Because Of This. O estado ativo é o candidato V2.1 factual-documentary com Gemini TTS direto, voz Charon e publicação manual. Nenhum outro motor, prompt, workflow ou provedor pode ser selecionado silenciosamente.

## Contrato ativo

- Idioma: inglês norte-americano (`en-US`).
- Voz: Gemini TTS direto, modelo `gemini-3.8-flash-tts`, voz `Charon`.
- Fallback de provedor: proibido.
- Vídeo: 1080×1920, 60 fps, 60–75 s (exceção máxima de 80 s).
- Áudio final: relógio mestre; legendas por alinhamento forçado palavra a palavra.
- Legendas: no máximo duas linhas, safe zone superior aprovada, base branca, palavra ativa `#F04444`, sem travessão em/en.
- Visual: clipes/reconstruções cinematográficas fotorrealistas, coerentes com cada beat; sem gráficos, diagramas, HUD, mapas, loops, clipes reutilizados ou preenchimento genérico.
- Branding: logo transparente na posição aprovada; história/narração terminam antes do endfilm de 5–6 s e fade para preto.
- Custos: zero gasto adicional; novas chamadas externas não verificadas ficam bloqueadas.
- Publicação e Drive: somente manualmente; nenhuma automação publica ou grava mídia remotamente.

## Ordem obrigatória

`STORY → HOOK → AUDIO/TIMECODES → BEATS → SHOT MAP → RIGHTS → REUSE → HUMAN STORY APPROVAL → TTS → MIX → TRANSCRIPTION → CAPTIONS → VISUAL ASSEMBLY → PREVIEW → HUMAN PREVIEW REVIEW → RENDER → QA → DELIVERY → MANUAL PUBLICATION`

Um gate bloqueado é uma parada intencional. Não existe fallback silencioso, promoção automática ou substituição por outro motor.

## Entrypoints e validação

Antes de qualquer operação:

```bash
PYTHONPATH=. python production/v21_singleton_guard.py --repo-root .
PYTHONPATH=. python production/canonical_entrypoint.py \
  --repo-root . \
  --manifest episodes/episode-005/production-record.json \
  --report /tmp/episode005-v21-report.json
```

Testes canônicos:

```bash
PYTHONPATH=. python -m unittest discover -s tests -p 'test_v21*.py' -v
PYTHONPATH=. python -m py_compile production/*.py
```

O preview só pode existir quando os gates permitirem. A produção permanece desabilitada até autorização humana explícita.

## Histórico isolado

Implementações V7/Piper, Edge TTS, Creative Claw e outros experimentos permanecem somente como evidência histórica, rollback ou auditoria. Não são runbooks atuais, não são fallback e não podem ser escolhidos pelo runtime.

A identidade visual canônica está registrada em `docs/CANONICAL_VISUAL_EDITORIAL_LOCK_20261112.md`. O estado editorial do EP005 e suas fontes são mantidos nos artefatos canônicos da Library; a falta de cobertura visual ou de evidência de áudio mantém o episódio bloqueado.
