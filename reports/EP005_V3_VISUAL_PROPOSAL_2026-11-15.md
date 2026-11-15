# Episode 005 — Proposta visual V3 (sem ativação)

- Data: 2026-11-15
- Base: `main` após a auditoria V3
- Engine: V2.1 factual / Gemini + Charon
- Escopo: shortlist editorial de candidatos; não altera o manifesto ativo.
- Estado: `PROPOSAL_ONLY`; render e preview continuam bloqueados.

## Regra aplicada

Cada candidato precisa representar fisicamente a ação narrada, ser fotorealista/footage real, não usar mapa, HUD, gráfico, relógio, abstração ou texto inventado, e passar por intake, fingerprint, direitos e continuidade antes de qualquer promoção.

## Proposta de correção

| Shot | Ação visual V3 | Candidato proposto | Licença observada | Decisão |
|---|---|---|---|---|
| S01 | Mão opera painel físico escuro com luzes vermelhas/verdes | Pexels 38958215 — https://www.pexels.com/video/close-up-button-operation-in-dark-control-room-38958215/ | Pexels, Free; 3840×2160; 26s | SHORTLIST |
| S02 | Satélite/órbita sobre a Terra, sem mapa ou interface | Pexels 854275 — https://www.pexels.com/video/satellite-orbiting-the-earth-854275/ | Pexels, Free to use / CC0 indicado na página | SHORTLIST, validar se o trecho mostra a Terra e a estrutura simultaneamente |
| S03 | Operador/radio como reconstrução, sem alegação arquivística | Atual: Pexels 11764431 | Pexels, Free; manifest-only atual | PRESERVAR EM REVISÃO |
| S04 | Mão opera painel/controles físicos; sem diagrama de cadeia | Pexels 6442796 — https://www.pexels.com/video/person-operating-button-panel-6442796/ | Pexels, Free; 1920×1080; 9s | SHORTLIST |
| S05 | Indicadores/botões físicos em sequência; sem tela gráfica | Pexels 16943469 — https://www.pexels.com/video/a-close-up-of-a-control-panel-with-red-and-green-lights-16943469/ | Pexels, Free to use | SHORTLIST, validar ausência de assinatura moderna excessiva |
| S06 | Alarme físico/luz de emergência em aumento de tensão | Pixabay 105764 — https://pixabay.com/videos/siren-alarm-warning-police-105764/ | Pixabay Content License; free for use | SHORTLIST CONDICIONAL: usar crop fechado, sem contexto policial |
| S07 | Segmento arquivístico não-relógio de operador/sala de controle | Atual: archive-prelinger-onguard1956-s07 | Direitos públicos declarados; manifest-only | PRESERVAR, validar segmento exato |
| S08 | Operador diante de radar analógico físico; não usar tela como gráfico | Pexels 6442793 — https://www.pexels.com/video/a-person-operating-a-radar-6442793/ | Pexels, Free; 1920×1080; 8s | SHORTLIST |
| S09 | Mão escreve/insere decisão em papel/logbook físico | Mixkit 99890 — https://mixkit.co/free-stock-video/close-up-a-hand-writing-notes-on-a-notebook-with-99890/ | Mixkit Stock Video Free License; commercial/personal | SHORTLIST |
| S10 | Segmento arquivístico não-relógio de operador/painel | Atual: archive-gov-antps25-29604-s10 | Direitos públicos declarados; manifest-only | PRESERVAR, validar segmento exato |
| S11 | Céu noturno vazio como não-evento | Atual: Pexels 12590338 | Pexels, manifest-only atual | PRESERVAR EM REVISÃO SEMÂNTICA |
| S12 | Terra/nuvens vistas do espaço; ponte física/observacional, sem NASA | Pexels 10343918 — https://www.pexels.com/video/planet-earth-spinning-10343918/ | Pexels, Free to use | SHORTLIST |
| S13 | Mão sobre papel/logbook; não chamar de prova sem documento autêntico | Pexels 8872970 — https://www.pexels.com/video/person-writing-on-a-paper-8872970/ | Pexels, Free to use | CANDIDATO CONDICIONAL; evidência documental ainda necessária |
| S14 | Corredor institucional vazio como representação de obscuridade posterior | Atual: Pexels 20837 | Pixabay, manifest-only atual | REVISÃO; não promover sem melhorar vínculo narrativo |
| S15 | Interruptor/luz física vermelha em ambiente escuro, desligamento como ação | Pexels 3770195 — https://www.pexels.com/video/close-up-of-a-knob-and-a-switch-3770195/ | Pexels, Free to use | SHORTLIST, validar que o recorte termina em apagamento real |
| S16 | Fundo preto + PNG original transparente do canal; sem partículas ou clip externo | Nenhum clip externo | Asset original do projeto | SUBSTITUIR POR LOGO-ONLY |

## Fontes rejeitadas nesta rodada

- Mixkit 45032 — Earth from space: página indica download gratuito apenas para uso pessoal; não serve como base segura para o canal.
- Pexels 5523892 e 5523891 — LED vermelho isolado/abstrato: não representam o evento diretamente e continuam incompatíveis com a trava V3.
- Pixabay 205519 — alarme em tela/computador: interface e pânico genérico; não usar.
- Qualquer resultado com clock, watch, timepiece, countdown, HUD, mapa, radar gráfico, infográfico ou texto embutido.

## Ajustes de contrato propostos

- Trocar a truth class dos shots S01, S02, S04, S05, S06, S08, S09, S12 e S15 de `MAP_OR_DIAGRAM` para `REPRESENTATIONAL` somente após a aprovação editorial dos candidatos.
- Remover do registro de produção as frases históricas de relógio em S07/S10.
- Manter S16 sem candidato de banco: somente preto, PNG original e encerramento de marca.
- Manter todos os candidatos como `APPROVED_FOR_MANIFEST_ONLY` até intake, hash, fingerprint, continuidade e direitos finalizados.
- Não gerar preview nesta fase.

## Bloqueios ainda ativos

1. Nenhum candidato novo foi promovido ao manifesto.
2. S13 ainda precisa de evidência documental autêntica ou deve ser reescrito visualmente como reconstrução.
3. S06 depende de crop que elimine contexto policial.
4. S12 precisa de verificação de que o material não é NASA, NASA-derived ou uma visualização gráfica.
5. S07/S10 dependem do recorte público declarado; full-source substitution continua proibida.
