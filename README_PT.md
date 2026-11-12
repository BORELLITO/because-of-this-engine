> **ESTADO CANÔNICO (07/11/2026):** consulte primeiro `production/active_engine_policy.json`.
> A política declara a candidata V2.1 factual com Gemini TTS/Charon direto,
> `production/canonical_entrypoint.py` como validador somente leitura,
> `production_enablement=false` e publicação manual.
> As instruções V7/V7.2/Piper abaixo são HISTÓRICAS, não autorizam execução.
> Confira as configurações e aprovações atuais antes de qualquer operação.
> Consulte `docs/QUALITY_SAFETY_HARDENING_20261107.md`.

# BECAUSE OF THIS — Motor canônico V2.1 Gemini TTS/Charon

Este é o único motor ativo do canal. A política canônica é `production/active_engine_policy.json` e aponta para o runtime V2.1 factual, com Gemini TTS/Charon direto, renderizador V21 e publicação manual. Creative Claw, Piper, Edge, Google Cloud TTS e qualquer outro motor não fazem parte da execução normal.

O motor permanece fail-closed: `production_enablement=false`, novos gastos e novas chamadas TTS não autorizadas ficam bloqueados, e nenhum preview ou relatório autoriza publicação automaticamente.

## Estado e autoridade

- Branch oficial: `main`. Apenas o código desta branch pode executar o runtime canônico.
- Política ativa: `production/active_engine_policy.json`: `active_engine_version=2.1`, `active_engine_profile=because-of-this-v2.1-canonical-factual-gemini-charon-2026-11`.
- Perfil de voz: Gemini TTS, Charon, `gemini-3.8-flash-tts`, mono 24 kHz PCM. **Sem fallback automático e sem Creative Claw.**
- Publicação **sempre manual**. Nenhum preview técnico, relatório ou cache autoriza postagem.
- Material histórico de outros projetos (Corte Fino, Rajada, CaptaPronto) não tem rota de execução para este motor.

## Registro histórico preservado — não canônico

Título: **The Elevator That Stopped on a Floor That Didn't Exist**.

- Execução histórica preservada; não representa a rota V2.1 atual: https://github.com/BORELLITO/because-of-this-engine/actions/runs/40986385249
- MP4 existente: https://drive.google.com/file/d/1C3mkxkKy1uZh8pBKlDOmaaRr4Gk_DDVR/view
- WAV de narração existente: https://drive.google.com/file/d/1fFI8b5RzDq3qu_T44lEh-BHCqIHl4ttH/view
- Pasta completa com relatórios e manifesto: https://drive.google.com/drive/folders/1HkjYfLf4vXJuJ1XjE-pQWVdjPGho6NDh

Este registro antigo é mantido somente para auditoria. Ele não pode ser usado como rota de execução do V2.1, nem autoriza reutilização automática de áudio, clipes ou render.

## Arquitetura vigente do V2.1

1. **Roteiro e intenção visual.** O motor organiza cenas, âncoras narrativas e material licenciado antes do processamento.
2. **Gemini TTS/Charon / cache inteligente.** A identidade do áudio é vinculada ao roteiro, ao perfil Charon, ao SHA-256 e ao contrato de custo zero. WAV fora de 60–75 segundos, com checksum ou perfil divergente, não pode ser reutilizado.
3. **Legenda a partir do áudio final.** Vosk gera timestamps reais. Legendas karaoke ficam sincronizadas com a voz; não aceitar estimativas inventadas.
4. **Materiais de Drive.** Cada clipe tem ID, origem, direitos, SHA-256 e identidade visual. Fonte inteira consumida **não pode aparecer em outros episódios**, mesmo se foi usada numa história arquivada ou recortada de outra forma.
5. **Músicas e efeitos.** Trilhas completas não podem ser repetidas entre histórias; histórico antigo conta. A semelhança acústica e o intervalo mínimo de reutilização dos efeitos ainda exigem verificações específicas e não são presumidos a partir da igualdade do nome.
6. **FFmpeg e gates.** Saída 1080×1920, 60 fps, 60–75 segundos; narrativa, suspense, logo, transições e legenda conforme o perfil canônico. Validação de reutilização e proveniência agora depende de auditorias reais, não de marcadores estáticos.
7. **Reutilizar antes de produzir.** Ao iniciar o episódio 001 com roteiro, manifesto e código idênticos, o preview original pode ser reconhecido e sua produção é pulada. Para episódios diferentes, a política de não repetir clipes prevalece.
8. **Entrega e publicação.** O Drive guarda os resultados; previews são candidatos e nunca equivalem à aprovação editorial. Publicação somente após aprovação humana e validação de licença.

## Controles operacionais

- `.github/workflows/episode005-v21-preview.yml` e os fluxos V2.1 de áudio/legenda: execução manual, sem publicação automática.
- `.github/workflows/video-engine-ci.yml` e `.github/workflows/v21-integration-readonly.yml`: validam somente contratos V2.1, sem síntese nova não autorizada nem publicação.
- `production/v21_singleton_guard.py`: verifica a identidade do runtime, o custo zero, a política de legenda e a ausência de defaults legados ativos.

## Limitações explicitamente mantidas

- A voz Charon e qualquer chamada externa continuam subordinadas ao contrato de custo zero e à autorização explícita da política ativa.
- O primeiro MP4 foi entregue como `DRAFT_PREVIEW_ONLY`: sua finalização/publicação depende de revisão e aprovação editorial.
- Restauração e retomada do fluxo novo foram cobertas por testes de unidade/contrato, mas a produção continua bloqueada até os gates manuais do V2.1 serem resolvidos.
- Os arquivos ASS/alinhamento **não** estavam no pacote anterior; os workflows atualizados passam a entregá-los nas produções futuras.
- Sem regras de proteção de branch garantidas por API: permissões do GitHub devem ser configuradas na plataforma caso se deseje obrigatoriedade de PR.

## Diagnóstico sem gastar créditos

```bash
PYTHONPATH=. python -m unittest discover -s tests -p 'test_v21*.py' -v
PYTHONPATH=. python -m py_compile production/*.py
```

**Princípio permanente:** evitar retrabalho, mas nunca reutilizar um arquivo de outra história, com direitos desconhecidos, alterado ou incompatível.

As referências V7/V7.2/Piper mantidas no histórico do repositório existem apenas para auditoria e rollback. Elas não são rotas executáveis do V2.1.
