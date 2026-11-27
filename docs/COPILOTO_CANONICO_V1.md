# BECAUSE OF THIS — COPILOTO CANÔNICO V1

**Status:** PROPOSTA OPERACIONAL APROVADA PARA IMPLEMENTAÇÃO CONTROLADA  
**Escopo:** somente `BORELLITO/because-of-this-engine`  
**Regra superior:** um único motor canônico ativo por vez

## 1. Função

O Copiloto Canônico é a camada de comando, supervisão, fila, memória e QA do projeto. Ele não é um segundo renderizador, não substitui `production/canonical_entrypoint.py` e não pode executar um motor alternativo.

Fluxo obrigatório:

`USUÁRIO → COPILOTO → FILA ÚNICA → SUBAGENTES SEQUENCIAIS → MOTOR CANÔNICO → QA → ENTREGA`

## 2. Regras invioláveis

1. Apenas um Runflow de produção pode estar ativo.
2. Nenhum subagente executa render, TTS, montagem, publicação ou alteração concorrente do estado.
3. Cada subagente produz um artefato versionado e devolve controle ao Copiloto.
4. O Copiloto atualiza `ESTADO_ATUAL.md` antes e depois de cada mudança relevante.
5. Estado desatualizado, conflito de versão, hash divergente ou gate bloqueado interrompe a fila (`FAIL_CLOSED`).
6. Subagentes não podem selecionar outro motor, provedor, prompt ou workflow.
7. Fallback silencioso é proibido.
8. Publicação, gasto, contato externo e alteração destrutiva exigem autorização específica.

## 3. Subagentes oficiais

| Ordem | Subagente | Responsabilidade | Pode escrever |
|---|---|---|---|
| 1 | **Research Analyst** | pesquisar fatos, fontes primárias e candidatos de clipe | cartão de pesquisa isolado |
| 2 | **Factual Reviewer** | conferir afirmações, datas, números e atribuições | recibo factual |
| 3 | **Story/Editorial Agent** | estruturar hook, narrativa, ritmo e payoff | roteiro candidato |
| 4 | **Rights & Provenance Agent** | verificar licença, restrições, origem, hash e não reutilização | ledger de direitos |
| 5 | **Visual Continuity Agent** | conferir aderência semântica, continuidade de luz, época, lugar e movimento | mapa visual |
| 6 | **Timeline & Caption Agent** | validar duração, word timestamps, karaoke e safe zone | preflight técnico |
| 7 | **QA/Release Reviewer** | consolidar gates, regressões, custo, segurança e integridade | recibo final de QA |
| 8 | **Delivery Agent** | reunir o artefato final, relatório e hashes para entrega manual | pacote de entrega |

## 4. Contrato de cada subagente

Cada execução deve receber somente o contexto mínimo necessário e devolver JSON/Markdown com:

- `agent_id`;
- `input_revision`;
- `source_artifacts`;
- `claims_or_decisions`;
- `evidence`;
- `status`: `PASS`, `EDIT`, `BLOCKED` ou `FAIL`;
- `blocking_reasons`;
- `output_artifact`;
- `output_sha256`;
- `next_gate`;
- `token_budget_used`.

Um subagente não pode declarar aprovação de outra área. Exemplo: o agente de direitos não aprova qualidade editorial; o agente editorial não aprova licença.

## 5. Estados do Copiloto

`IDLE → INTAKE → RECONCILING_MEMORY → RESEARCH → FACTUAL_REVIEW → EDITORIAL_REVIEW → RIGHTS_REVIEW → VISUAL_REVIEW → TIMELINE_PREFLIGHT → ENGINE_QUEUE → ENGINE_RUNNING → QA → DELIVERY_READY`

Qualquer falha crítica leva a `BLOCKED` ou `FAIL_CLOSED`. Não há salto automático de etapa.

## 6. Política de contexto e custo

- Ler primeiro a revisão e os hashes; não reenviar arquivos completos sem necessidade.
- Usar deltas e referências de artefatos em vez de repetir o contexto inteiro.
- Reutilizar evidências já verificadas quando a revisão/hash permanecerem válidos.
- Nunca chamar TTS, render ou serviços pagos durante pesquisa ou revisão.
- Um único agente mutável por vez; análises somente leitura podem ser enfileiradas, mas não alteram o estado simultaneamente.

## 7. Critério de entrega

O Copiloto só pode informar “vídeo pronto para entrega” quando:

- todos os recibos obrigatórios estiverem `PASS`;
- direitos e hashes estiverem reconciliados;
- timeline, karaoke e safe zone estiverem validados;
- QA técnico não tiver regressões;
- o artefato final tiver hash e localização verificáveis;
- publicação continuar manual, salvo autorização específica.

## 8. Dois níveis integrados

### Nível 1 — agentes especializados de análise, QA e entrega
O módulo `production/copilot_analysis_agents_v1.py` fornece os adaptadores executáveis do nível 1: ordem canônica, domínio de aprovação, hash do artefato, orçamento de tokens e `can_start_engine=false`. O executor é injetado; o adaptador não chama modelo, não grava memória, não inicia engine, não renderiza e não publica. Um resultado diferente de `PASS` interrompe a sequência.


Research, factual, editorial, direitos, continuidade visual e timeline/captions trabalham em sequência, seguidos por QA de release e empacotamento de entrega. Cada função possui escopo isolado e recibo próprio. Nenhum deles pode iniciar o motor ou aprovar outra área.

A resolução operacional ocorre por `production/copilot_executor_registry_v1.py`: cada papel recebe um executor explicitamente registrado por `agent_id`. Executor ausente gera recibo `BLOCKED` e encerra a lane; não há executor implícito, fallback, rede ou paralelismo.

A validação do recibo também reconcilia `input_revision`, artefatos/evidências, domínio de aprovação, hash, status, motivo de bloqueio e orçamento máximo de tokens antes de aceitar o próximo agente.

Os oito papéis executáveis são: `research_analyst`, `factual_reviewer`, `story_editorial_agent`, `rights_provenance_agent`, `visual_continuity_agent`, `timeline_caption_agent`, `qa_release_reviewer` e `delivery_agent`. Antes de qualquer executor ser chamado, `production/copilot_provider_readiness_v1.py` exige um manifesto explícito por `agent_id`. Cada registro precisa declarar provedor, modo sequencial, rede desativada, `can_start_engine=false` e custo incremental zero. Manifesto incompleto retorna `BLOCKED` sem chamar nenhum provedor; metadado inseguro falha fechado. Isso prepara a conexão futura de provedores reais sem criar fallback, paralelismo, gasto ou ativação de produção.

### Nível 2 — gate técnico consolidado

Depois do Nível 1, o gate técnico único consolida:

- testes do contrato e da fila;
- privacidade e segredos acidentais;
- escopo permitido do PR;
- compilação dos módulos;
- regressões do copiloto;
- produção desativada e fallback proibido.

Implementação: `production/copilot_technical_gate_v1.py`. Workflow: `.github/workflows/copilot-technical-gate.yml`. O gate é read-only, fail-closed e não inicia produção.

A implementação ocorre em branch própria, com testes de contrato e sem ativar produção. O motor canônico só pode ser chamado quando os dois níveis anteriores estiverem `PASS`.

## 8.1 Reconciliacao Brazil Files → Copiloto Canonico

Os 22 checkpoints editoriais do Brazil Files permanecem como fronteiras de
analise e revisao, mas nao criam agentes ou motores adicionais. O crosswalk
executavel em `production/brazil_files_canonical_crosswalk_v1.py` reutiliza
as oito capacidades canonicas, sempre em ordem sequencial e com
`parallel=false`. O `delivery_agent` so recebe o handoff terminal depois
dos 22 recibos em `PASS`. O contrato e o gate bloqueiam qualquer drift,
paralelismo ou engine secundario.

Documento operacional: `docs/BRAZIL_FILES_CANONICAL_CROSSWALK_V1.md`.

## 9. Fila técnica implementada

- Implementação isolada: `production/copilot_queue_v1.py`.
- A fila valida revisão da memória e hash da política antes de qualquer transição.
- `claim_next` permite somente uma reivindicação ativa; estado obsoleto, duplicidade, ownership incorreto ou falha registrada bloqueiam a próxima execução.
- A persistência é atômica e conserva pedidos enfileirados; o módulo não inicia o motor nem publica mídia.
- Testes: `tests/test_copilot_queue_v1.py`.

## 10. Fonte de verdade

- Política: `production/active_engine_policy.json`.
- Entrypoint: `production/canonical_entrypoint.py`.
- Guard: `production/v21_singleton_guard.py`.
- Memória: `ESTADO_ATUAL.md`.
- Este documento define o contrato do Copiloto, mas não autoriza produção por si só.
## 11. Ordem de integração

A governança do motor único deve ser efetivada antes da ativação do Copiloto. O PR que aplica a serialização global do Runflow é integrado primeiro; em seguida, o PR do Copiloto pode ser integrado porque mantém `production_activation.enabled=false`. A integração não autoriza Runflow, TTS, render, publicação ou gasto.
A aprovação de cada etapa depende dos checks obrigatórios do próprio evento do PR; checks de um head anterior não substituem a validação do head atual.
A revalidação de um PR após mudança da base deve usar o merge-ref e o corpo atuais; resultados de tentativas anteriores permanecem apenas como histórico.
A proteção imutável também exige o marcador de autorização no título quando a mudança toca a superfície `production/`; isso é uma exigência de governança, não uma autorização para iniciar produção.
