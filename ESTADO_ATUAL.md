# ESTADO_ATUAL.md — BECAUSE OF THIS

**Data da verificação:** 2026-11-27  
**Repositório canônico:** `BORELLITO/because-of-this-engine`  
**Branch canônica:** `main`  
**Commit verificado:** `1452560ca7cc21d934b90b3f52f6674c294409b0`  
**Transparência:** mudanças relevantes exigem relatório completo no PR.

## Estado canônico

O projeto possui um único motor canônico V2.1 e uma única fila operacional.
O Copiloto supervisiona análise, QA, handoff e entrega; não é um segundo
renderizador.

- Produção automática: **DESATIVADA**.
- TTS, render, Drive e publicação: **NÃO EXECUTADOS** nesta atualização.
- Execução paralela: **PROIBIDA**.
- Fallback silencioso: **PROIBIDO**.
- Karaoke, safe zone, direitos, continuidade visual e identidade do canal:
  **preservados**.
- O dispatch real do Runflow permanece manual ou em workflow separado,
  exigindo autorização específica.

## Arquitetura vigente

### Copiloto Canônico

Oito papéis sequenciais:

1. `research_analyst`
2. `factual_reviewer`
3. `story_editorial_agent`
4. `rights_provenance_agent`
5. `visual_continuity_agent`
6. `timeline_caption_agent`
7. `qa_release_reviewer`
8. `delivery_agent`

### Brazil Files

Os 11 blocos editoriais e 22 checkpoints de analista/revisor permanecem
preservados. O crosswalk executável reutiliza as oito capacidades canônicas,
sem criar agentes, motores ou filas paralelas.

- Módulo: `production/brazil_files_canonical_crosswalk_v1.py`
- Checkpoints: **22**
- Capacidades: **8**
- Modo: `SEQUENTIAL_REUSE_CANONICAL_AGENT`
- Handoff terminal: `delivery_agent`, somente após 22 recibos `PASS`

### Handoff para Runflow

O módulo `production/copilot_runflow_handoff_v1.py` é somente leitura. Ele
retorna `READY_FOR_RUNFLOW_PREPARATION_GATE` apenas quando:

- a fila está em `ENGINE_QUEUE`, sem execução ativa;
- os oito recibos canônicos estão em `PASS` e na ordem correta;
- o crosswalk Brazil Files está aprovado;
- a revisão da memória e o hash da política estão atuais.

Qualquer divergência retorna `RUNFLOW_HANDOFF_BLOCKED`.

## Evidências verificadas

- PR #211 — lane canônica de oito papéis integrada.
- PR #212 — crosswalk Brazil Files 22→8 integrado.
- PR #213 — handoff read-only Copiloto→Runflow integrado.
- PR #215 — preflight real do Brazil Files EP001 integrado, mantendo o caso bloqueado.
- PR #217 — dossiê narrativo sourced de 16 beats integrado ao preflight e ao gate técnico; clip research permanece pendente.
- PR #219 — registro fail-closed de fontes gratuitas de clipes integrado ao gate; licenças continuam verificadas por asset.
- PR #221 — semente de pesquisa com candidatos reais por beat, todos em HOLD, integrada ao gate sem liberar seleção.
- PR #223 — lock de isolamento de namespace integrado; o pacote legado permanece preservado e não é sobrescrito.
- PR #225 — primeiro recibo real de clipe (B03-C02) integrado com licença declarada, download, fingerprint SHA-256 e probe técnico; produção continua bloqueada.
- PR #227 — segundo recibo real de clipe (B02-C01, mapa do Brasil em 4K) integrado com licença declarada, download, fingerprint SHA-256 e probe técnico.
- PR #229 — trava fail-closed de inventário dos recibos de clipe integrada ao preflight; conta apenas JSONs válidos, rejeita duplicatas e não libera produção.
- PR #231 — contagem endurecida: recibos com erro local ou duplicatas não contribuem para os 22 válidos.
- PR #233 — B04-C01 rejeitado por mostrar rosto; B04-C02 integrado com mãos ajustando rádio, licença, fingerprint e probe técnico verificados.
- PR #235 — B05-C03 integrado como recibo HOLD: aeronave noturna em 16:9, licença, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- PR #237 — B06-C03 integrado como recibo HOLD: cockpit faceless em 16:9, licença Pixabay, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- PR #239 — B07-C01 integrado como recibo HOLD: mãos sem rosto organizando documentos de investigação em 16:9, licença Pexels, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- PR #241 — B08-C02 integrado como recibo HOLD: pastas de documentos em close-up 16:9, licença Pixabay, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- PR #243 — B09-C01 integrado como recibo HOLD: waveform de áudio em 16:9, licença Pixabay, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- Gate técnico do Copiloto: **PASS**.
- Active surface: **PASS**.
- Immutable core: **PASS**.
- Integração V2.1: **PASS**.
- CI canônico pós-merge: **PASS**.

## Pendências reais

1. Manifestos de provedores reais continuam ausentes; o provider readiness
   permanece fail-closed e sem custo.
2. O Runflow ainda não é disparado automaticamente pelo Copiloto; o handoff
   validado apenas prepara a autorização.
3. Nenhum vídeo final foi produzido por estas mudanças.
4. O preflight do EP001 reconhece o dossiê narrativo, o registro de fontes, a
   semente de pesquisa e o lock de namespace. A trava de recibos contabiliza somente
   evidências verificadas: há 8 recibos válidos (B03-C02, B02-C01, B04-C02, B05-C03, B06-C03, B07-C01, B08-C02 e B09-C01) e faltam 14 para
   o mínimo de 22; B04-C01 foi rejeitado na revisão semântica por expor rosto. O dossiê
   completo de seleção, os 22 checkpoints, continuidade e
   revisão final de direitos/fingerprints continuam pendentes.
5. Qualquer ativação de provedor, gasto, publicação ou dispatch de produção
   exige mudança separada e autorização específica.

## Próxima ação prioritária

Antes de ativar qualquer produção, validar um caso editorial completo com os
22 checkpoints, recibos dos oito agentes, direitos, mapa visual, karaoke,
safe zone e QA. Somente depois avaliar uma mudança separada para dispatch
controlado do Runflow.
