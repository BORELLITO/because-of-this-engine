# Brazil Files — Orquestração multiagente

O `Brazil Files Story Orchestrator` controla a preparação do episódio. Ele não
substitui o Runflow e não autoriza publicação.

Sua regra superior é `BRAZIL_FIRST_RESPECTFUL_DOCUMENTARY`: o Brasil é o
protagonista cultural e narrativo, enquanto o suspense organiza a experiência
do espectador.

## Fluxo contínuo com dupla validação

Cada bloco possui um agente analista e um agente revisor. O revisor não pode ser
substituído pelo próprio analista, e nenhum bloco pode ser pulado. O avanço só
ocorre quando os dois status são `PASS`.

| Bloco | Analista | Revisor | Trava principal |
|---|---|---|---|
| 01 Pesquisa | `CASE_RESEARCH` | `CASE_RESEARCH_REVIEW` | fontes e cronologia |
| 02 Verdade | `CLAIM_CALIBRATION` | `CLAIM_CALIBRATION_REVIEW` | fato, relato, lenda e hipótese separados |
| 03 Brasil | `BRAZILIAN_CONTEXT` | `BRAZILIAN_CONTEXT_REVIEW` | valor e respeito cultural |
| 04 Narrativa | `NARRATIVE_ARCHITECT` | `NARRATIVE_ARCHITECTURE_REVIEW` | causalidade e payoff |
| 05 Retenção | `RETENTION_ARCHITECT` | `RETENTION_REVIEW` | hook, emoção, escalada e CTA |
| 06 Inglês | `ENGLISH_LOCALIZATION` | `ENGLISH_LOCALIZATION_REVIEW` | naturalidade e fidelidade |
| 07 Mapa visual | `VISUAL_MATCH` | `VISUAL_MATCH_REVIEW` | âncora visual por beat |
| 08 Clipes | `VISUAL_CLIP_DIRECTOR` | `VISUAL_CONTINUITY_REVIEW` | semântica e continuidade |
| 09 Direitos | `RIGHTS_AND_CITATION` | `RIGHTS_REVIEW` | fonte e licença |
| 10 Marca | `BRAND_CONTINUITY` | `BRAND_REGRESSION_REVIEW` | voz, logo, legenda e outro |
| 11 QA final | `SCRIPT_QA` | `RED_TEAM_REVIEW` | todos os riscos fechados |

O orquestrador registra cada par, cada saída e cada trava. Se um revisor
retornar `BLOCKED`, o fluxo para naquele bloco e só continua após correção e
novo recibo. O Runflow nunca recebe um pacote baseado em aprovação implícita.

## Contrato visual do novo agente

O `VISUAL_CLIP_DIRECTOR` não escolhe clipes apenas por palavras-chave. Para
cada beat narrativo, ele precisa registrar:

- o que a frase afirma;
- o que o espectador precisa enxergar;
- por que o clipe representa diretamente essa informação;
- país, cidade, região, época e ambiente;
- direção de luz, movimento de câmera e emoção;
- relação de continuidade com o clipe anterior e o seguinte;
- origem, licença, SHA/fingerprint e status de não-reutilização.

Ele bloqueia material genérico, bonito porém errado, fora de época, fora de
localização, visualmente incoerente ou repetido em outro episódio.

## Contrato de saída

O pacote mínimo precisa conter `case-dossier.json`, `claim-calibration.json`,
`script-en-US.txt`, `visual-beat-map.json`, `rights-and-citations.json`,
`brand-continuity.json` e `script-qa.json`.

Qualquer agente bloqueado mantém o pacote fora do Runflow. Não há fallback
silencioso para roteiro sem fontes, visual genérico ou clipe sem proveniência.

