# Brazil Files — Crosswalk canônico V1

## Objetivo

Os 11 blocos editoriais do Brazil Files continuam existindo como checkpoints
independentes para preservar rastreabilidade, revisão dupla e evidências. Os
22 nomes de analista/revisor não são 22 motores nem 22 agentes de execução.

O módulo `production/brazil_files_canonical_crosswalk_v1.py` encaminha cada
checkpoint para uma capacidade do Copiloto Canônico, reutilizando os oito papéis
oficiais em uma única fila sequencial.

## Regra operacional

- 22 checkpoints editoriais permanecem visíveis.
- 8 capacidades canônicas são reutilizadas conforme o domínio.
- `parallel=false`.
- Nenhum checkpoint cria provedor, fila, engine ou workflow próprio.
- `delivery_agent` só é chamado como handoff terminal depois que os 22 recibos
  estiverem `PASS`.
- A entrega não publica, não faz gasto, não chama TTS/render e não altera
  memória sem a etapa autorizada correspondente.
- Falha, conflito de revisão ou recibo ausente mantém o fluxo
  `FAIL_CLOSED`.

## Mapeamento resumido

| Checkpoints Brazil Files | Capacidade canônica |
|---|---|
| Pesquisa do caso + revisão | Research Analyst → Factual Reviewer |
| Calibração de alegações + revisão | Factual Reviewer |
| Contexto brasileiro, narrativa, retenção e inglês | Story/Editorial Agent |
| Mapa visual, direção de clipes e continuidade | Visual Continuity Agent |
| Direitos e citações | Rights & Provenance Agent |
| Continuidade de marca | Timeline & Caption Agent |
| Revisão de regressão, QA e red team | QA/Release Reviewer |
| Handoff depois dos 22 checkpoints | Delivery Agent |

O mapeamento completo, com ordem, bloco, domínio de aprovação e regra de
handoff, é a fonte executável no módulo Python. O contrato não permite que uma
capacidade aprove outra área fora do seu domínio.

## Gate

O teste `tests/test_copilot_brazil_crosswalk.py` verifica:

1. exatamente 22 checkpoints;
2. preservação dos 11 blocos;
3. cobertura das 8 capacidades canônicas;
4. entrega terminal somente após o checkpoint 22;
5. bloqueio em caso de duplicidade ou drift;
6. ausência de paralelismo e de motor secundário.

Esta mudança é de reconciliação de governança. Ela não ativa produção nem
substitui o Runflow canônico.
