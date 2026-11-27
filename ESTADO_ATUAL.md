# ESTADO_ATUAL.md — BECAUSE OF THIS

**Data da verificação:** 2026-11-27  
**Repositório canônico:** `BORELLITO/because-of-this-engine`  
**Branch canônica:** `main`  
**Commit verificado:** `0844267447211cf29e51ed7ed1538e099f654c05`  
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
- Handoff terminal: `delivery_agent), somente após 22 recibos `PASS`

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
4. O preflight do EP001 reconhece o dossiê narrativo de 16 beats e o registro de
   fontes, mas permanece `BLOCKED` por falta do dossiê de seleção de clipes,
   recibos dos 22 checkpoints, direitos/fingerprints e colisão com o namespace legado.
5. Qualquer ativação de provedor, gasto, publicação ou dispatch de produção
   exige mudança separada e autorização específica.

## Próxima ação prioritária

Antes de ativar qualquer produção, validar um caso editorial completo com os
22 checkpoints, recibos dos oito agentes, direitos, mapa visual, karaoke,
safe zone e QA. Somente depois avaliar uma mudança separada para dispatch
controlado do Runflow.
