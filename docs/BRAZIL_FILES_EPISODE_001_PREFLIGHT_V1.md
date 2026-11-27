# Brazil Files — Preflight do Episódio 001

O caso selecionado é a **Noite Oficial dos OVNIs (1986)**. O brief está
versionado em:

`episodes/brazil-files/episode-001/case-brief.json`

O primeiro nível editorial está versionado em
`episodes/brazil-files/episode-001/narrative-beat-dossier.json`. Ele contém
16 beats, fontes identificadas, limites factuais e representação visual
proposta. Seu estado é **NARRATIVE_DOSSIER_READY_CLIP_RESEARCH_PENDING**:
isso não seleciona clipes nem comprova licença.

## Isolamento de namespace

O pacote legado `episodes/episode-001` é preservado. O arquivo
`episodes/brazil-files/episode-001/namespace-lock.json` comprova que:

- o legado não será sobrescrito;
- o EP001 real usa exclusivamente o namespace de staging;
- os dois pacotes permanecem separados e reversíveis.

Esse lock resolve a ambiguidade de namespace sem mover, apagar ou renomear o
pacote legado.

O preflight executável é
`production/brazil_files_ep001_preflight_v1.py`. Ele valida o brief, o
dossiê narrativo, o lock de namespace e bloqueia até que existam:

- dossiê visual de seleção com 16 beats;
- três a cinco candidatos por beat não-CTA;
- direitos e fingerprints verificados;
- recibos dos 11 blocos e 22 checkpoints;
- handoff canônico aprovado.

Estado atual comprovado: **BLOCKED**. O caso está selecionado para
desenvolvimento narrativo e pesquisa, mas não está liberado para seleção
aprovada de clipes, Runflow, TTS, render ou publicação.

A seleção editorial não é prova de licença audiovisual. Cada asset precisa de
origem, licença, fingerprint e revisão semântica própria.
