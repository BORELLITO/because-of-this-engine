# ESTADO_ATUAL.md — BECAUSE OF THIS

**Data da verificação:** 2026-11-28  
**Repositório canônico:** `BORELLITO/because-of-this-engine`  
**Branch canônica:** `main`  
**Commit verificado:** `b4c7d71560377a438b8fc4f893c07541943c242e`  
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
- PR #245 — B10-C01 integrado como recibo HOLD: mãos sem rosto organizando arquivos em prateleira 16:9, licença Pexels, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- PR #247 — B11-C01 integrado como recibo HOLD: céu noturno natural com estrelas e silhueta montanhosa em 16:9, licença Pixabay, fingerprint e probe técnico verificados; seleção e produção continuam bloqueadas.
- PR #250 — B12-C01 rejeitado por reutilização do asset B07-C01; B12-C02 adicionado em HOLD como reenactment documental distinto, sem promover o candidato nem liberar produção; reprodução do relatório SIAN permanece condicionada a direitos específicos.
- PR #252 — B12-C02 integrado como recibo HOLD: páginas com caracteres impressos em reenactment documental Pexels, fingerprint e probe H.264 verificados; não é o relatório SIAN original e seleção/produção continuam bloqueadas.
- PR #254 — B13-C01 integrado como recibo HOLD: pôr do sol, horizonte e silhueta natural do Pixabay, SHA-256/probe/fingerprint visual verificados; divergência de duração entre player e arquivo baixado registrada; seleção e produção continuam bloqueadas.
- PR #258 — B14-C01 validado e rejeitado semanticamente: vídeo vertical genérico de arquivo, com pessoa identificável, sem sinal brasileiro, pasta documental ou identificador SIAN; não foi criado receipt.
- B14-C02 — candidato Pexels em HOLD: estantes e pastas em 16:9, arquivo baixado e fingerprint verificados; ainda falta cue brasileiro e identificador SIAN documental claramente autorizado.
- PR #259 — B14-C02 registrado em HOLD após download, fingerprint, probe e revisão visual; não é receipt e não libera seleção ou produção.
- PR #260 — memória reconciliada após a pesquisa B14; produção e Runflow continuam bloqueados.
- B14-C03 — fonte oficial do Arquivo Nacional localizada para o relatório de 19/05/1986 (`BR_DFANBSB_ARX_256_p0005_0005`); permanece em HOLD porque o uso visual exige reconciliação de licença/Termo de Utilização.
- PR #262 — candidato oficial B14-C03 registrado em HOLD; nenhum arquivo foi reproduzido e nenhum direito foi presumido.
- B14-C04 — receipt Pixabay integrado em HOLD: close-up 4K de pastas/arquivos em 16:9, SHA-256/probe/fingerprint verificados; é reenactment genérico e não o documento SIAN primário.
- B15-C01 — receipt Pixabay integrado em HOLD: panorama aéreo noturno explicitamente identificado como São Paulo, Brasil, em 4K/16:9, SHA-256/probe/fingerprint verificados; é contexto geográfico, não evidência do evento de 1986.
- PR #264 — B14-C04 mesclado após CI, gate técnico, integração canônica, superfície ativa e núcleo imutável aprovados.
- PR #266 — B15-C01 mesclado após transparência formal, CI, gate técnico, integração canônica, superfície ativa e núcleo imutável aprovados; receipt permanece em HOLD.
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
   evidências verificadas: há 14 recibos válidos (B03-C02, B02-C01, B04-C02, B05-C03, B06-C03, B07-C01, B08-C02, B09-C01, B10-C01, B11-C01, B12-C02, B13-C01, B14-C04 e B15-C01) e faltam 8 para
   o mínimo de 22; B04-C01 foi rejeitado na revisão semântica por expor rosto. O dossiê
   completo de seleção, os 22 checkpoints, continuidade e
   revisão final de direitos/fingerprints continuam pendentes; B12-C02 permanece como reenactment documental, B14-C01 foi rejeitado por desalinhamento semântico e qualquer frame ou identificador do relatório SIAN ainda exige clearance específico.
5. Qualquer ativação de provedor, gasto, publicação ou dispatch de produção
   exige mudança separada e autorização específica.

## Próxima ação prioritária

Antes de ativar qualquer produção, validar B16-C01 contra o ativo interno aprovado e continuar a expansão dos recibos faltantes, mantendo B14-C04 e B15-C01 em HOLD e B14-C03 fora da produção até a licença/Termo de Utilização ser resolvido; depois concluir o caso editorial com os 22 checkpoints, direitos, mapa visual, karaoke, safe zone e QA. Somente então avaliar dispatch controlado do Runflow.
