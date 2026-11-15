# Episode 005 — Intake V3 de mídia

- Data: 2026-11-15
- Engine: V2.1 factual / Gemini + Charon
- Escopo: intake, hash SHA-256, metadados técnicos e QA visual por frames dos candidatos da shortlist.
- Regra: nenhum arquivo abaixo foi promovido ao manifesto ativo; nenhum preview/render foi gerado.

## Resultado

- Arquivos baixados e examinados: 11
- Candidatos úteis ou condicionais: 7
- Rejeitados por conflito visual: 4
- Manifesto ativo: inalterado
- Render: continua bloqueado

## QA técnico e visual

| Shot | Arquivo / fonte | Duração | Dimensão | SHA-256 | QA visual | Decisão |
|---|---|---:|---:|---|---|---|
| S01 | Pexels 38958215 — https://www.pexels.com/video/close-up-button-operation-in-dark-control-room-38958215/ | 26.880s | 3840×2160 | `76b7ebcc774b63aea0e33df94e546be592f4150e2bec1d00c5986f632c4b656f` | Painel físico escuro; luzes vermelha/verde; mão real | PASSA COMO CANDIDATO |
| S02 | Pexels 854275 — https://www.pexels.com/video/satellite-orbiting-the-earth-854275/ | 144.810s | 1280×720 | `3b7cc1d7c80742c7a63877b6823626d4094542d705903ff7379948f824f4ac60` | Terra renderizada com anel orbital visível | REJEITADO: CGI/órbita gráfica |
| S04 | Pexels 6442796 — https://www.pexels.com/video/person-operating-button-panel-6442796/ | 8.895s | 1920×1080 | `d324ee2c854c7a06b29b243a2c79ab8e8b24b08ee1c434d617cda0ff1db04737` | Mão e painel físico; aparência industrial contemporânea | CONDICIONAL: crop/grade |
| S05 | Pexels 16943469 — https://www.pexels.com/video/a-close-up-of-a-control-panel-with-red-and-green-lights-16943469/ | 11.220s | 3840×2160 | `4573d81034a67d028cffa573a8a21888f3de02caa193af0c8388947c18eef273` | Painel moderno com várias etiquetas “DETENIDO” | REJEITADO: texto/contexto moderno |
| S06 | Pixabay 105764 — https://pixabay.com/videos/siren-alarm-warning-police-105764/ | 7.018s | 1920×1080 | `7fc59c9d24113833cd76ef6a90a4336c449a53f4c8a36f7c9be6e89a73ee5e85` | Ícone de sirene animado em fundo branco | REJEITADO: gráfico/ícone |
| S08 | Pexels 6442793 — https://www.pexels.com/video/a-person-operating-a-radar-6442793/ | 8.255s | 1920×1080 | `062be75f253bd3a9681c835c9a1f69e789357fc7b04562d98c64e66f9d82712a` | Operador e equipamento/radar físico; aparência analógica | PASSA COMO CANDIDATO |
| S09 | Mixkit 99890 — https://mixkit.co/free-stock-video/close-up-a-hand-writing-notes-on-a-notebook-with-99890/ | 8.175s | 1280×720 | `c75423da6e4381c40ec2cd31c63f1227d3495fc29c428089caa0dc648f068a30` | Mão escrevendo em caderno; laptop periférico pode ser cortado | CONDICIONAL: crop fechado |
| S12 | Pexels 10343918 — https://www.pexels.com/video/planet-earth-spinning-10343918/ | 300.010s | 1920×1080 | `11e0a9f793bd16ae3d9d1a60b605f08362bad637ca3a3637c3600e04de1bfd29` | Terra claramente renderizada/estilizada | REJEITADO: CGI/visualização |
| S12R | Pexels 40359652 — https://www.pexels.com/video/stunning-timelapse-of-cumulus-clouds-40359652/ | 9.520s | 3840×2160 | `1f272186f0b842768f591b66e6f847dfd56439448f83ae2ee4c2e0711eb07365` | Nuvens reais em footage; sem gráfico ou texto | CONDICIONAL: ponte de nuvens, não “sensor” literal |
| S13 | Pexels 8872970 — https://www.pexels.com/video/person-writing-on-a-paper-8872970/ | 15.720s | 1920×1080 | `0cfe217831c6e889574354fab25fc47a96f576f348c835b8f77ce94d19f1cf38` | Mão escrevendo em papel; sem documento histórico legível | CONDICIONAL: reconstrução, não prova |
| S15 | Pexels 3770195 — https://www.pexels.com/video/close-up-of-a-knob-and-a-switch-3770195/ | 5.005s | 1920×1080 | `cd5f8d6a31594cc8814ed79c5755351707f4a191aea91f55d7e4bd16f030db43` | Interruptor/luz vermelha físicos em ambiente escuro | PASSA COMO CANDIDATO |

## Direitos observados

- Pexels: as páginas consultadas exibem uso gratuito; a validação jurídica final continua pendente de registro no ledger.
- Pixabay 105764: rejeitado visualmente antes de qualquer promoção.
- Mixkit 99890: página declara Mixkit Stock Video Free License para uso comercial/pessoal; ainda depende de registro formal no ledger.
- Nenhum candidato recebeu `APPROVED_FOR_RENDER`.

## Correções resultantes

1. S02 não pode usar Terra com órbita renderizada; continua sem candidato aprovado.
2. S05 foi descartado por texto/contexto industrial moderno.
3. S06 foi descartado por ser ícone animado.
4. S12 original foi descartado por CGI; S12R passa a ser ponte visual real de nuvens, sem alegar que seja o sensor.
5. S09 só pode ser usado com crop fechado que elimine laptop/mouse.
6. S13 continua reconstrução visual; não pode ser apresentado como documento histórico autêntico.
7. S16 permanece exclusivamente logo original sobre preto.

## Próximo bloqueio

Ainda faltam candidatos reais para S02 e S06. A próxima alteração do manifesto só poderá ocorrer depois de:

- resolver S02/S06 com footage físico/fotorealista;
- registrar direitos e receipts;
- executar fingerprint global contra o catálogo;
- validar continuidade entre shots;
- obter aprovação editorial dos recortes.

