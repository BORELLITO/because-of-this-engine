# Brazil Files — Preflight do Episódio 001

O caso selecionado é a **Noite Oficial dos OVNIs (1986)**. O brief está
versionado em:

`episodes/brazil-files/episode-001/case-brief.json`

O primeiro nível editorial agora está versionado em
`episodes/brazil-files/episode-001/narrative-beat-dossier.json`. Ele contém
16 beats, fontes identificadas, limites factuais e representação visual
proposta. Seu estado é **NARRATIVE_DOSSIER_READY_CLIP_RESEARCH_PENDING**:
isso não seleciona clipes nem comprova licença.

Esse namespace é deliberadamente separado do legado
`episodes/episode-001`, que contém um pacote ficcional histórico e não pode
ser sobrescrito automaticamente.

O preflight executável é
`production/brazil_files_ep001_preflight_v1.py`. Ele valida o brief, o
dossiê narrativo e bloqueia até que existam:

- dossiê visual de seleção com 16 beats;
- três a cinco candidatos por beat não-CTA;
- direitos e fingerprints verificados;
- recibos dos 11 blocos e 22 checkpoints;
- ausência de colisão de namespace;
- handoff canônico aprovado.

Estado atual comprovado: **BLOCKED**. O caso está selecionado para
desenvolvimento narrativo, mas não está liberado para pesquisa aprovada de
clipes, Runflow, TTS, render ou publicação.

A seleção editorial não é prova de licença audiovisual. Cada asset precisa de
origem, licença, fingerprint e revisão semântica própria.
