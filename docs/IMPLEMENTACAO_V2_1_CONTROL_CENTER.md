# BECAUSE OF THIS — V2.1 Integration Control Center

> **CANONICAL STATUS — 2026-11-07:** The active source of truth is `production/active_engine_policy.json`: V2.1 factual documentary, Gemini TTS / Charon, `production_enablement=false`, manual publication. Earlier Edge/Piper statements in this historical log are superseded. See latest addendum at the bottom.


- Implementation ID: IMPL-V21-20261105-01
- Audit ID: AUDIT-V21-20261105-01
- Specification: PROMPT_MESTRE_IMPLEMENTACAO_INTEGRACAO_BECAUSE_OF_THIS_V2_1_FINAL(2).txt
- Prompt SHA-256: 8f51c909363ead5c6d2964b733fcdf8909632dc68fef966802b1f8a56e2cb173
- Repository: BORELLITO/because-of-this-engine
- Base: main at d35d78cd4a92d12375f54076e3e21b56cbe25fad
- Candidate branch: integration/because-of-this-v2.1-20261105
- Draft PR: 67 (branch head is authoritative; commit history is tracked by GitHub)
- Status: PARTIAL_MANIFEST_VALIDATED_BLOCKED_RENDER
- Canonical entrypoint: production/canonical_entrypoint.py
- Canonical voice: Microsoft Edge TTS / ChristopherNeural active for zero-billing preview; Cloud/Gemini are not active routes
- Publication: manual only
- Historical protection: One Extra Minute is excluded from execution and reuse

## This changeset

- canonical_entrypoint.py is now the authority for the V2.1 read-only contract.
- The old v7_orchestrator.py delegates to the canonical entrypoint whenever the V2.1 policy is active.
- The old V2/V7 state machine is an explicit compatibility boundary; V2.1 records use pipeline_state_v21.py.
- The global asset registry is loaded automatically and missing/incomplete catalogs block.
- The production schema is validated by the canonical entrypoint, not only parsed as JSON.
- The final thumbnail manifest and delivery paths are mandatory for a canonical PASS.
- The singleton workflow audit is fail-closed in CI.
- Historical production workflows were moved to archive/v7/workflows/; they are no longer GitHub Actions entrypoints.
- Visual candidate intake and global fingerprint audit are manual-only, plan-driven and fail-closed; ordinary PR/documentation changes no longer download media. The search-v2 queue batches six page-verified candidates per unresolved shot, shortlists two, then dispatches one manual intake batch and one fingerprint audit for the explicit selected IDs. The fingerprint audit never scans the entire plan implicitly. These workflows produce evidence artifacts but cannot promote assets, update the global catalog, write Drive or render. Batch IDs are restricted to safe plan identifiers, capped at 12 candidates, limited to 200 MiB and 180 seconds per media file, restricted to verified Mixkit hosts, and rights/domain metadata are revalidated during fingerprint. A structural validator (`production/visual_plan_contract.py`) now checks the plan, partial manifest, candidate uniqueness, approval evidence, assignment reuse and promotion flags in CI without requiring the nine unresolved shots to be complete.

## Evidence

| Area | Status | Evidence |
|---|---|---|
| Main / refs / PRs | FOUND | GitHub API; main d35d78c; PR 67 |
| V2.1 contracts | TESTED | Candidate CI must pass unit, schema, adapter, singleton and clean-checkout gates |
| Canonical adapter | IMPLEMENTED | v7_orchestrator.py delegates to canonical_entrypoint.py under active V2.1 policy |
| Global no-reuse | VALIDATED_FOR_MANIFEST / BLOCKED_FOR_CATALOG | 16 assigned assets, 16 unique sources, no source/SHA/perceptual collisions in the latest fingerprint evidence; global catalog mutation remains false |
| Thumbnail | FINAL_APPROVED / DELIVERY_PACKAGED | `THE MACHINE LIED` approved by user; technical QA passed; PNG/JPG master, source frame, mobile preview and platform record versioned |
| Legacy workflows | ARCHIVED | Definitions retained under archive/v7/workflows/, outside .github/workflows |
| Drive | NOT RUN | No Drive write or media generation authorized |
| Work | UNKNOWN | No independent Work execution log |
| Edge TTS + captions preview | VALIDATED | Microsoft Edge / en-US-ChristopherNeural; 79.704 s; audio SHA-256 and provider-native caption record aligned; Whisper remains diagnostic only |
| Visual asset acquisition | PARTIAL_MANIFEST_VALIDATED_BLOCKED_RENDER | 42 active candidates, 22 approved for manifest, 16 assets assigned to 16 shots, 0 unresolved; intake/fingerprint are manual-only and no asset is approved for render/catalog/Drive |
| Canonical render route | MANUAL GATE IMPLEMENTED / EXECUTION BLOCKED | production/render_v21_manual.py and workflow episode005-v21-manual-render.yml are manual-only and fail-closed; actual render remains disabled while production_enablement=false |
| First new production | BLOCKED | Implementation stage does not authorize automatic production |

## Current blockers

- The visual plan and partial scene manifest are structurally validated: 42 active candidates, 22 approved for manifest, 16 assets, 16/16 shots assigned, 0 unresolved, and no duplicate source/SHA/perceptual collision detected. This does not authorize render or catalog mutation.
- All 16 assignments remain APPROVED_FOR_MANIFEST_ONLY; every asset keeps approved_for_render=false, global_catalog_updated=false and drive_written=false.
- The previous thumbnail candidate was removed. The replacement `THE MACHINE LIED` is now final-approved with technical QA and delivery files; this approval does not authorize render or publication.
- The canonical entrypoint is intentionally read-only. production_enablement=false, publication is manual-only, and there is no active V2.1 final-render workflow. The archived legacy renderer is not an acceptable fallback.
- Edge TTS and provider-native captions are validated and aligned to the frozen audio SHA-256; the 79.704-second duration is within the explicit 80-second exception, but the target window remains 60–75 seconds.
- Global catalog update, Drive write, render and publication remain unexecuted. The delivery bundle is versioned, but the PR is still draft and requires explicit review/post-merge audit.

READY remains forbidden while any P0/P1 is open.

## Addendum operacional — 2026-11-05

- O dispatch manual foi exposto no branch padrão sem habilitar execução automática: intake e fingerprint continuam `workflow_dispatch`, com IDs explícitos e sem promoção.
- Quatro candidatos Pixabay foram baixados no intake `42038088699`, artifact `13418919199`, digest `sha256:0f0e34d502ef7ff553fad4cee3c32cecd1e3e1055d6dda9adf12ab2eb97877a1`; estado permanece `CANDIDATE_DOWNLOADED_AWAITING_HUMAN_QA`.
- O fingerprint global corrigido passou no run `42039523926`, job `127286341600`, artifact `13420042319`, digest `sha256:f29e75ce9c73ea465dbbd6450fdf5d9a2ff37c463b30e0e6749aa27e4c3c63d2`, usando `video-fingerprint-v2-rgb24-q4`: 4/4 sem colisão de SHA-256, fonte ou fingerprint perceptual.
- A evidência foi registrada em `episodes/episode-005/visual/asset-acquisition-plan.json`; aprovação humana, render, catálogo global, Drive e publicação continuam bloqueados.
- O conflito do workflow `.github/workflows/episode005-visual-fingerprint-audit.yml` foi resolvido entre `main` e a branch candidata; o PR 67 está novamente `mergeable`, ainda draft.
- Próximo gate único: QA humano dos quatro clipes e aquisição dos nove shots restantes; só depois thumbnail final, render e Drive.

## Addendum de auditoria visual — 2026-11-05

- Foi detectada uma fraqueza real no QA anterior: os contact sheets eram gerados somente com os primeiros segundos do clipe e o crop 9:16 era verificado em um único frame.
- O workflow `.github/workflows/episode005-visual-candidate-intake.yml` foi corrigido no commit `9108c622adc0ab95d97be846e6294213a0056a6a` para amostrar cinco posições normalizadas — início, 25%, 50%, 75% e final — e produzir `qa-frames.jpg`, `qa-crop-9x16.jpg`, `qa-sampling.json` e os frames individuais.
- A inspeção preliminar foi registrada no plano, sem alterar a aprovação formal:
  - `pixabay-alert-alarm-war-205519`: rejeição preliminar por HUD/ícone/scan-lines gráficos persistentes; não passa no gate de fonte limpa.
  - `pixabay-radar-sonar-ping-2420`: condicional; sem logo/letterbox observado, mas é diagrama radar simbólico e não evidência arquivística.
  - `pixabay-radar-screen-4511`: condicional; crop sobrevive, porém é um insert abstrato de baixa informação e deve ser curto.
  - `pixabay-television-broadcasting-satellite-29483`: rejeição preliminar por aderência semântica fraca ao S12; mostra apenas uma televisão com tela branca.
- A intake dos quatro candidatos precisa ser rerodada para gerar a nova evidência antes de qualquer decisão humana. Nenhum candidato foi promovido; render, catálogo global, thumbnail, Drive e publicação continuam bloqueados.
- Próximo passo único atualizado: rerodar a intake Pixabay com a amostragem corrigida, substituir os dois rejeitados e então buscar aprovação humana explícita somente para os candidatos que passarem nos gates.

## Addendum — refresh explícito de QA visual concluído — 2026-11-05

- A primeira reexecução (#87, run `42042484037`) falhou de forma fail-closed porque o intake existente não podia ser sobrescrito implicitamente.
- Foi criada a entrada manual `refresh_existing`, desativada por padrão, que somente regenera evidência isolada de QA e não altera catálogo, manifesto aprovado, render, Drive ou publicação.
- A reexecução autorizada com `refresh_existing=true` foi concluída com sucesso:
  - run: `42043152146`
  - job: `127298967914`
  - commit do workflow: `61d1f3613e2a065aad3d1ccd931e027f597ea9f9`
  - artifact: `13422407818`
  - digest: `sha256:2c518303ddeab0806300fe1eb4e8e1c3a01b7d0de92f1118ccbe0e77b5c7381f`
- Evidência confirmada nos logs: quatro candidatos, cinco amostras normalizadas por candidato (início, 25%, 50%, 75% e fim menos 0,1 s), crops 9:16 e contact sheets de duração integral.
- Resultado de segurança: `promotion_allowed=false`, `render_allowed=false`, `global_catalog_updated=false` e `drive_written=false`.
- Os dois descartes preliminares permanecem: alerta/HUD para S06/S09 e televisão vintage para S12. Radar/sonar e radar-screen continuam condicionais, pendentes de aprovação humana explícita.
- Próximo único passo: substituir os dois descartes por candidatos semanticamente adequados; nenhuma integração de render, catálogo ou Drive deve avançar antes disso.


## Addendum — substitutos Pixabay, correção de JSON e fingerprint — 2026-11-05

- A intake corrigida foi executada no commit `af15b0bb20738b6ddcdfee098f992e958f006651`, run `42049521282`, artifact `13426556747`, digest `sha256:81604ae674a11d6e4c7b27769ab80b6b9a7aaa486260edae9c280220a9750e60`.
- Foi corrigido um defeito real no workflow: três relatórios eram gravados com os caracteres literais `\\n`, o que invalidava o JSON. A correção substituiu essas sequências por quebras de linha reais. Os três artefatos foram rebaixados e validados com parser JSON.
- Os dois candidatos receberam cinco amostras normalizadas, crops 9:16 e contact sheets de duração integral. Nenhuma promoção ocorreu: `promotion_allowed=false`, `render_allowed=false`, `global_catalog_updated=false`, `drive_written=false`.
- O fingerprint global passou no run `42049952757`, artifact `13424799852`, digest `sha256:c561091d1c94a2ef93b5e5d34b194e54c9990490da56dde60c9fedfa3921e99b`, usando `video-fingerprint-v2-rgb24-q4`: 2/2 sem colisões de SHA-256, fonte ou fingerprint perceptual.
- `pixabay-led-indicator-lights-316712`: revisão visual preliminar positiva, porém condicional; é uma textura abstrata de barras luminosas, adequada apenas como representação de indicadores em S06/S09, nunca como console soviético literal. Aprovação humana continua pendente.
- `pixabay-sky-clouds-satellite-95686`: rejeitado semanticamente para S12; é um céu/nuvem azul limpo, mas não mostra satélite, sensor ou geometria de luz suficiente para representar o mecanismo narrado.
- O plano canônico foi atualizado com as evidências, mantendo a distinção entre validação técnica e aprovação humana. O manifesto não foi promovido, o catálogo global não foi atualizado e render/Drive/publicação continuam bloqueados.
- Próximo passo único: obter sua decisão sobre o candidato LED e buscar um novo candidato distinto, visualmente coerente com o mecanismo sol/nuvens/satélite de S12.


## Addendum — novo candidato page-verified para S12 — 2026-11-05

- Foi identificado e verificado no navegador o candidato `pixabay-antenna-astronomy-communication-40041`.
- Página: https://pixabay.com/videos/antenna-astronomy-communication-40041/
- Mídia observada: `https://cdn.pixabay.com/video/2020/05/24/40041-424371544_large.mp4`
- Evidências da página: Pixabay Content License visível, duração indicada de 22 s e resolução 1920×1080.
- Leitura editorial: antena parabólica/estação terrestre real sob céu aberto, visualmente mais coerente com o mecanismo sensor–céu de S12 do que a textura genérica de nuvens rejeitada.
- Estado: `CANDIDATE_NOT_DOWNLOADED`. Ainda não houve intake, fingerprint, aprovação humana ou promoção.
- O candidato foi registrado no plano canônico. Próximo gate: intake controlada, amostragem integral, verificação 9:16 e fingerprint global.
- O LED permanece pendente de aprovação explícita; render, catálogo global, Drive e publicação continuam bloqueados.


## Addendum — intake e fingerprint do candidato S12 — 2026-11-05

- A intake controlada foi concluída com sucesso no run `42052509193`, job `127332058958`, artifact `13427442382`, digest `sha256:122fee7648e166d0eea6bce8920486107922b7c64a6c892e975dec535f65d87`, no commit `efd7a0e40545b9400d14c90977253a9c73992bdc`.
- O arquivo baixado foi validado com SHA-256 `e0a5b6cbf90c31c7f79c8cf6d9eaa515a83d4e986927a90a3840d7d36303e9b4`; metadata: 22,548 s, 1920×1080, H.264, 30 fps. A amostragem produziu cinco frames e crops 9:16.
- A inspeção visual preliminar passou: não foram observados textos queimados, logos de terceiros ou letterbox; a antena parabólica permanece legível no recorte vertical. A classificação é representacional/mapa-diagrama, nunca evidência literal de Petrov. Aprovação humana continua pendente.
- A primeira tentativa de fingerprint (`42052937565`) falhou de forma fail-closed com `candidate_missing_intake_artifact`, porque o plano ainda não continha o artifact recém-produzido. Nenhum arquivo foi promovido.
- A causa foi corrigida registrando a intake no plano no commit `7d3867d9fa72ca43068e72b550fd3fb0b4f28541`; a nova execução passou no run `42053792993`, job `127336595316`, artifact `13427769060`, digest `sha256:f92cb4eed9bfc2fbaf518540413f5ab363578156f7c58d947e69c692219e0c87`.
- Fingerprint: `FINGERPRINT_AUDIT_PASS`, algoritmo `video-fingerprint-v2-rgb24-q4`, sem colisão de fonte, SHA-256 ou fingerprint perceptual; perceptual hash `720e0b55776ac929e3c7f5be259dcaa7c848fe1cefb4fc2ffd501c6b2ee1059d`.
- Estado atual: candidato tecnicamente apto e semanticamente promissor para S12, mas `human_approval=PENDING`, `approved_for_render=false`, `global_catalog_updated=false`, `drive_written=false`. O LED também permanece pendente.
- Próximo passo único: aguardar sua aprovação explícita para o candidato S12 e, separadamente, para o LED antes de qualquer promoção ao manifesto ou renderização.


## Addendum — aprovação manifest-only de LED e S12 — 2026-11-05

- A autorização recebida foi aplicada somente no nível `APPROVED_FOR_MANIFEST_ONLY`; não houve renderização, mutação do catálogo global, escrita no Drive ou publicação.
- `pixabay-led-indicator-lights-316712` foi aprovado exclusivamente para S06, como textura abstrata de indicadores/electronics para a subida da intensidade do alarme. Não representa a interface soviética real. A regra de fonte única por shot foi preservada.
- `pixabay-antenna-astronomy-communication-40041` foi aprovado exclusivamente para S12, como infraestrutura representacional de antena/sensor. Não representa footage literal do incidente de Petrov.
- O manifesto parcial foi atualizado no commit `0d6fa696b712af04baaf87d671f30f4069db0493`. S06 e S12 deixaram de estar bloqueados; permanecem pendentes S05, S08, S09, S13, S14, S15 e S16.
- Evidências mantidas: LED fingerprint pass no run `42049952757`; S12 fingerprint pass no run `42053792993`. Ambos continuam com `approved_for_render=false`, `global_catalog_updated=false` e `drive_written=false`.
- Plano canônico atualizado no commit `ee24e2c01216af3e6e20e29e179c03506c3ec3a6`; a aprovação foi registrada com shot_ids explícitos para impedir reutilização acidental.
- Próximo passo único: adquirir candidatos distintos para os shots restantes e executar a validação final do manifesto. Render e publicação continuam bloqueados.

## Addendum — triagem de candidatos restantes — 2026-11-05

- O candidato page-verified `pixabay-hallway-dark-corridor-20837` foi registrado como `CANDIDATE_NOT_DOWNLOADED`, com fonte exclusiva para S14, licença Pixabay visível e mídia direta observada no link do provedor: `https://cdn.pixabay.com/video/2019/01/19/20837-312432073_large.mp4`.
- O candidato de documentos `pixabay-documents-papers-research-212509` foi rejeitado antes da intake: a inspeção visual mostrou documentos modernos legíveis, incluindo material semelhante a passaporte/visto e texto pessoal, incompatível com o tratamento de relatório/logbook desclassificado.
- O candidato `pixabay-red-light-blur-flare-250419` foi rejeitado antes da intake: é um gradiente vermelho abstrato, sem ação visual distinta de pulso de alerta e com sobreposição à família visual já usada em S01.
- Nenhum download, fingerprint, promoção, atualização de catálogo, escrita no Drive, renderização ou publicação ocorreu nesta triagem.
- Próximo passo único: formar uma nova shortlist page-verified para S05, S08, S09, S13, S15 e S16; S14 só poderá avançar para intake após manter a verificação técnica e a regra de fonte única.

## Addendum — correção do SHA e fingerprint S14 em andamento — 2026-11-05

- A primeira execução do fingerprint do corredor S14 falhou de forma fail-closed no run `42056451177`: o arquivo baixado tinha SHA-256 real, mas o campo correspondente no plano estava vazio. Não houve colisão visual aprovada nem promoção.
- A evidência foi corrigida no plano: SHA-256 `e6c20511f889daa57834ddf5f97ea076ffffedc0a321850a4ea8fa295479d72d`, duração 6,933 s, 1920×1080, H.264, 29,97 fps. Commit da correção: `829d8dfd35e1a87d00e95d852825b4a728fab4e8`.
- O fingerprint foi reexecutado explicitamente para `pixabay-hallway-dark-corridor-20837` no run `42056934162`, job `127347760300`, branch `integration/because-of-this-v2.1-20261105`. No momento deste registro, a etapa de instalação do FFmpeg está em andamento; o workflow permanece fail-closed.
- O plano foi atualizado para refletir `FINGERPRINT_AUDIT_RUNNING` no commit `3408330ba1380857a52ada76ece0ce185c438311`. Aprovação humana, promoção, manifesto, catálogo global, render, Drive e publicação continuam bloqueados.
- Próximo passo único: aguardar o término do run `42056934162`; se passar, registrar a evidência e manter S14 pendente apenas de QA/aprovação humana.


## Addendum — fingerprint S14 concluído com sucesso — 2026-11-05

- O run anterior `42056934162` ficou preso na instalação do FFmpeg no runner `ubuntu-latest`, durante a migração para Ubuntu 26.04. O fluxo não promoveu nenhum arquivo.
- O workflow foi corrigido para usar `ubuntu-24.04` enquanto a migração do runner estiver instável. Commit da correção: `44240bfd04eb9b61778a5a3c088a63e44cc16ee0`.
- A nova execução explícita para `pixabay-hallway-dark-corridor-20837` passou: run `42059893725`, job `127358312867`, artifact `13431651011`, digest `sha256:71428db1a7810ba8074da7c85139ff0a6720a06ea06aab169b5dd539f3ed7e8d`.
- Resultado técnico: `FINGERPRINT_AUDIT_PASS`, sem colisão de fonte, SHA-256 ou fingerprint perceptual. SHA do arquivo: `e6c20511f889daa57834ddf5f97ea076ffffedc0a321850a4ea8fa295479d72d`; perceptual hash: `40df89d9d2edf33d5a94509be3c9f3abb6073dd28ff1914aba8307eb1055aafd`.
- S14 continua como candidato representacional para corredor institucional vazio, não como evidência literal de Petrov. `human_approval=PENDING`, `approved_for_render=false`, `global_catalog_updated=false`, `drive_written=false`, `render_allowed=false`.
- O plano canônico registrou a evidência no commit `dbb4396b9178314b1e1da047e82e6666386d7dca`. O manifesto permanece sem promoção de S14; seguem sete shots não resolvidos: S05, S08, S09, S13, S14, S15 e S16.
- Próximo passo único: realizar QA visual e aprovação humana explícita do candidato S14; depois disso, manter a decisão de promoção separada da autorização de render, catálogo, Drive e publicação.


## Addendum — aprovação manifest-only do S14 — 2026-11-05

- Recebida aprovação humana explícita para `pixabay-hallway-dark-corridor-20837`.
- O candidato foi promovido somente para `APPROVED_FOR_MANIFEST_ONLY` e atribuído exclusivamente ao shot S14. A regra de fonte única foi preservada.
- Evidências: intake run `42056121022`, artifact `13428247933`; fingerprint pass run `42059893725`, artifact `13431651011`, sem colisões de fonte, SHA-256 ou fingerprint perceptual.
- O manifesto foi atualizado no commit `daa671382fd0a3b56ddfc0e6f8d4587fe6813aca`. S14 deixou de estar bloqueado; permanecem S05, S08, S09, S13, S15 e S16.
- O plano foi atualizado no commit `04adbb76cb7e70cd362c426a0482e3cc00a5dbaf`.
- Mantidos bloqueados: validação final do manifesto, renderização, atualização do catálogo global, escrita no Drive e publicação.
- Próximo passo único: formar shortlist distinta e page-verified para S05, S08, S09, S13, S15 e S16.


## Atualização — shortlist page-verified dos seis shots restantes

- Foram adicionados ao plano 12 candidatos distintos, dois por shot, para S05, S08, S09, S13, S15 e S16.
- Todos foram verificados diretamente nas páginas do Pixabay; a licença visível foi `Pixabay Content License` e não foi observado marcador de conteúdo gerado por IA.
- Nenhum candidato foi baixado, submetido ao intake, fingerprintado, aprovado para manifesto, promovido, catalogado, renderizado, escrito no Drive ou publicado nesta etapa.
- O candidato `pixabay-red-light-blur-flare-250419` continua rejeitado e não foi reintroduzido; as opções S15 registradas são rotas distintas e ainda simbólicas, pendentes de QA integral.

| Shot | Candidatos page-verified | Tratamento previsto |
|---|---|---|
| S05 | `pixabay-alert-alarm-war-danger-risk-205519`; `pixabay-radar-black-green-target-symbol-57670` | Escalada representacional de indicadores; sem alegação de interface soviética literal |
| S08 | `pixabay-radar-radar-screen-rotation-circles-4511`; `pixabay-radar-communication-military-261518` | Contradição entre monitoramento/radar e alerta; insert simbólico |
| S09 | `pixabay-button-press-red-business-click-502`; `pixabay-button-press-push-start-launching-221746` | Entrada técnica da classificação; sem interface celebratória |
| S13 | `pixabay-typewriter-typing-writing-author-1335`; `pixabay-typewriter-type-antique-writing-38626` | Tratamento de relatório/logbook; nenhum texto histórico inventado será usado |
| S15 | `pixabay-dark-light-lens-flare-abstract-250413`; `pixabay-abstract-light-streaks-motion-250417` | Pulso de aviso dissolvendo em preto; rota simbólica |
| S16 | `pixabay-particles-orange-red-dust-effect-7957`; `pixabay-colors-lines-lights-abstract-video-5072` | Fundo abstrato para outro de marca; logo só poderá entrar no renderer aprovado |

**Estado após a shortlist:** os shots não resolvidos continuam exatamente `S05,S08,S09,S13,S15,S16`; as flags `every_shot_assigned`, `final_visual_manifest_validated`, `global_catalog_update_authorized`, `render_authorized`, `drive_write_authorized` e `publication_authorized` permanecem falsas.

**Próximo gate único:** despachar explicitamente o lote de intake dos 12 IDs acima, somente como aquisição técnica isolada; depois revalidar SHA-256, QA integral, fingerprint e aprovação humana antes de qualquer promoção.


## Atualização — intake e fingerprint dos 12 candidatos concluídos

- O primeiro dispatch do lote (#93, run `42070599841`) foi cancelado por timeout de 15 minutos no `apt-get install ffmpeg`, antes de qualquer download.
- O workflow de intake foi corrigido no commit `c51e423ccda209b21cdb79e28d2294888c84074e` para usar FFmpeg/FFprobe estáticos com limites de tempo, sem gerenciador de pacotes. O fingerprint recebeu a mesma correção no commit `aaa1a77d85ff0f019e8a61a4e7b7b4c8fd307a23`.
- Intake isolado concluído com sucesso: run `42073828513`, job `127408597700`, artifact `13437466569`, digest `sha256:19b29cd3ea7ba77af62067c6f29bad72c3ffc8b837c0a44565252613b2b15057`. Resultado: 12/12 candidatos baixados, SHA-256, metadata e cinco amostras normalizadas com crops 9:16/contact sheets; todos `CANDIDATE_DOWNLOADED_AWAITING_HUMAN_QA`.
- Fingerprint global concluído com sucesso: run `42074599454`, job `127411317006`, artifact `13438400127`, digest `sha256:bf30a68cd1afe703492db843698ec9254b1e7563bbb161cab895bf4ad87c31b1`. Algoritmo `video-fingerprint-v2-rgb24-q4`; registry schema 2; 12/12 sem colisão de fonte, SHA-256 ou fingerprint perceptual; blockers vazios.
- A evidência foi registrada no plano canônico no commit `9532d5142f569bf50c41b0a74222044782f57332`. Os seis shots continuam exatamente `S05,S08,S09,S13,S15,S16`; nenhum candidato foi promovido ao manifesto.
- Flags permanecem fechadas: `human_approval=PENDING`, `approved_for_render=false`, `global_catalog_updated=false`, `render_allowed=false`, `drive_written=false` e publicação não autorizada.

**Próximo gate único:** executar QA visual humano dos 12 contact sheets e decidir candidato por candidato/shot; após aprovação explícita, atualizar somente o manifesto parcial, mantendo catálogo, render, Drive e publicação bloqueados.


## Atualização — aprovação humana do lote visual completo (2026-11-05)

- O usuário aprovou os 12 candidatos Pixabay baixados e fingerprintados no lote 42073828513 / fingerprint 42074599454.
- A aprovação foi registrada como APPROVED_FOR_MANIFEST_ONLY; ela não autoriza render, catálogo global, Drive ou publicação.
- O plano episodes/episode-005/visual/asset-acquisition-plan.json foi atualizado no commit d020f79ef3b5723b3bfc72ac50d0880ee3618008.
- O manifesto parcial episodes/episode-005/visual/scene-asset-manifest.json foi atualizado no commit 0a44b71b0e4cff540e9810bbe3f33f7fe98e8da8.
- Foram escolhidos os primários de maior score dentro de cada par aprovado:
  - S05: pixabay-alert-alarm-war-danger-risk-205519
  - S08: pixabay-radar-radar-screen-rotation-circles-4511
  - S09: pixabay-button-press-red-business-click-502
  - S13: pixabay-typewriter-typing-writing-author-1335
  - S15: pixabay-dark-light-lens-flare-abstract-250413
  - S16: pixabay-particles-orange-red-dust-effect-7957
- Auditoria estrutural read-only após a atualização: 16/16 shots atribuídos, 0 shots pendentes, 16 fontes únicas, 16/16 assignments com aprovação de manifesto, SHA-256/fingerprint/licença presentes.
- Estado de promoção permanece fail-closed: final_visual_manifest_validated=false, render_authorized=false, global_catalog_update_authorized=false, drive_write_authorized=false, publication_authorized=false.
- Próximo gate único: executar a validação final read-only do manifesto visual e dos direitos/estrutura; somente depois avaliar autorização separada para render.


## Atualização — correção de aliases duplicados e validação final estrutural (2026-11-05)

- A primeira execução do contrato visual encontrou uma causa-raiz real: dois IDs antigos apontavam para as mesmas páginas e URLs de mídia dos novos candidatos Pixabay — radar 4511 e alerta 205519.
- Correção fail-closed aplicada em duas etapas: os aliases foram marcados como REJECTED_DUPLICATE_SOURCE_ALIAS e removidos somente da lista ativa de candidatos; a evidência foi preservada em rejected_candidates.
- Commits de correção: bdcf190c93b78e0293e039269fc3947398ee7442 e d371da0ad7c72576bcd3e9f664baa6b03f89a5e4.
- Validação oficial executada localmente sobre o checkout da branch após o pull: VISUAL_PLAN_CONTRACT_PASS.
- Evidência da validação: 42 candidatos ativos, 22 aprovados para manifesto, 16 assets no manifesto, 16/16 shots atribuídos, 0 shots pendentes, promotion_allowed=false, render_allowed=false e global_catalog_updated=false.
- O bloqueio de reutilização foi resolvido sem apagar o histórico de rejeição e sem promover mídia para render.
- Próximo gate único: auditoria final de direitos/semântica e autorização separada para render; catálogo global, Drive e publicação permanecem bloqueados.


## Atualização — contrato visual final validado (2026-11-05)

- A validação oficial production/visual_plan_contract.py foi registrada como VISUAL_PLAN_CONTRACT_PASS.
- Evidência: 42 candidatos ativos, 22 aprovados para manifesto, 16 assets no manifesto, 16/16 shots atribuídos e 0 pendências.
- O plano foi atualizado no commit d2157a9e9bd7f15f8ff4b2f7a636323707f21f16 e o manifesto no commit 4d29b0fc4e75e9c5abc98b9d4bc283c8998e7524.
- Estado atual: PARTIAL_MANIFEST_VALIDATED_BLOCKED_RENDER; final_visual_manifest_validated=true, render_authorized=false, global_catalog_update_authorized=false, drive_write_authorized=false e publication_authorized=false.
- Próximo gate único: autorização explícita para render; a exigência de thumbnail final continua ativa antes de qualquer produção.


## Atualização — pré-voo de produção e thumbnail candidata (2026-11-05)

- Autorização do usuário para avançar registrada como autorização de render, sem autorização automática de publicação.
- Pré-voo técnico local passou: py_compile de production, 13 testes V2.1 e V21_SINGLETON_PASS.
- O motor canônico permanece deliberadamente read-only: production/canonical_entrypoint.py valida contratos, mas não chama TTS, geração de mídia, render, Drive ou publicação; active_engine_policy.json mantém production_enablement=false.
- Não existe workflow V2.1 de render final ativo na branch; nenhum render foi iniciado por essa limitação estrutural.
- Foi preparada uma thumbnail candidata original, simbólica e sem alegação de imagem histórica, com cinco indicadores vermelhos, radar e o texto FIVE MISSILES. Ela ainda requer aprovação visual humana e não foi integrada como thumbnail final.
- Próximo gate único: aprovar a thumbnail candidata e, em seguida, implementar/ativar a rota manual de render V2.1 sem contornar o entrypoint canônico e mantendo publicação manual.


## Atualização — thumbnail candidata registrada (2026-11-05)

- A thumbnail candidata foi aprovada para avançar como candidata técnica e registrada em episodes/episode-005/story-architecture.json.
- Asset: Cinco luzes vermelhas no bunker.png; dimensões 1080x1920; SHA-256 84fbac028247995943aa5c9e4fcfc698526215e83c2017edc225dbcebe307276; Library file id libfile_0a269bde796c81919bd777795b907361.
- Texto: FIVE MISSILES. A composição usa cinco indicadores vermelhos, radar verde, silhueta anônima e nuvens; é arte simbólica original, não evidência histórica.
- O status permanece CANDIDATE_READY_FOR_HUMAN_REVIEW; ainda não é thumbnail final aprovada para publicação.
- A rota de render V2.1 continua o único bloqueio estrutural: o entrypoint canônico é read-only, production_enablement=false e não existe workflow final ativo. Nenhuma rota legada foi reativada.
- Próximo passo técnico seguro: implementar uma rota manual V2.1 de render com contrato próprio, preservando o entrypoint canônico read-only, publicação manual e fail-closed.


## Atualização — auditoria profunda de integração e organização — 2026-11-05

- Checkout auditado no head a7d1836b32a5e02dc92c3046c13c8f68cca1a86f; branch correta, sem alterações locais e sem erro em git diff --check.
- Validação oficial VISUAL_PLAN_CONTRACT_PASS: 42 candidatos ativos, 22 aprovados para manifesto, 16 assets, 16/16 assignments e 0 shots pendentes; promotion_allowed=false, render_allowed=false e global_catalog_updated=false.
- Auditoria cruzada confirmou episode_id, story_id, cobertura S01–S16, 16 fontes únicas, SHA-256/fingerprint/licença presentes e flags de promoção fechadas.
- Pré-voo repetido com sucesso: py_compile de production/*.py, 13 testes V2.1 passando e V21_SINGLETON_PASS; nenhuma rota legada foi reativada.
- Conflito documental corrigido neste Centro de Controle: o resumo superior agora reflete o estado real atual; os addenda históricos foram preservados.
- Conclusão: a integração de contratos, TTS/captions, plano visual, manifesto, fingerprint e gates está implementada/testada como candidata V2.1. A integração operacional de render final ainda não está implementada e permanece corretamente bloqueada.
- A entrada manual V2.1 foi implementada em production/render_v21_manual.py e registrada na policy como manual_render_entrypoint; ela executa somente preflight fail-closed e não chama o renderer legado.
- O workflow .github/workflows/episode005-v21-manual-render.yml foi criado com workflow_dispatch, permissões somente de leitura e sem publicação/Drive.
- O contrato media_contract_v21.py e o fixture V2.1 agora apontam para a entrada manual; o renderer legado continua fora da rota ativa.
- Novos testes de gate passaram: 2 casos adicionais cobrindo production_enablement, autorização humana e thumbnail final obrigatória.
- Próximo passo único: preparar o production record e os arquivos finais de thumbnail/preview; somente após esses gates e autorização explícita será possível implementar/ativar a execução de mídia do render.


## Atualização — production record V2.1 preparado e validado — 2026-11-05

- Foi criado o registro canônico `episodes/episode-005/production-record.json`, com história, ledger factual, 16 direitos visuais, contratos TTS/áudio/captions/render/Drive e referência da thumbnail candidata.
- A primeira validação encontrou e corrigiu um conflito de vocabulário: `REPRESENTATIONAL` e `BRAND_OUTRO` não pertenciam ao vocabulário oficial do PACKAGE_GATE_PRE. Foram normalizados para `RECONSTRUCTION` e `ABSTRACT_ATMOSPHERE`, preservando o significado editorial.
- Validação final do registro: schema PASS, PACKAGE_GATE_PRE PASS com 10/10, source ledger PASS, global no-reuse PASS, TTS/audio/captions/render/Drive/adapters PASS.
- O registro permanece corretamente BLOCKED por dois gates reais: direitos ainda estão `APPROVED_FOR_MANIFEST_ONLY` e a thumbnail ainda não tem aprovação final, margens/legibilidade QA nem arquivos de delivery.
- O novo preflight manual confirmou `V21_MANUAL_RENDER_BLOCKED`, `production_enablement=false`, render NOT_RUN e publicação MANUAL_ONLY_NOT_RUN.
- O CI agora verifica automaticamente que o production record do Episódio 005 continue fail-closed.
- Próximo passo único: finalizar a aprovação/entrega da thumbnail e promover os direitos visuais de manifest-only para render somente após a revisão final; ainda não liberar produção automaticamente.


## Atualização — remoção da thumbnail candidata — 2026-11-05

- A thumbnail candidata `Cinco luzes vermelhas no bunker.png` foi removida do estado ativo do projeto a pedido do usuário.
- As referências ativas ao conceito, Library file id, SHA-256 e `FIVE MISSILES` foram retiradas de `story-architecture.json` e `production-record.json`; o registro agora usa `PENDING_REPLACEMENT`.
- O gate de thumbnail não foi removido: schema, QA, margens, legibilidade, direitos, delivery e aprovação continuam obrigatórios antes de qualquer render.
- O histórico de auditoria foi preservado nos addenda anteriores, mas a thumbnail antiga não é mais candidata utilizável.
- Próximo passo único: selecionar uma nova thumbnail candidata ou manter o episódio sem thumbnail até nova decisão editorial.


## Atualização — nova candidata de thumbnail registrada — 2026-11-05

- Foi criada uma nova candidata original, diferente da anterior: `episode005-thumbnail-machine-lied-v1.png`, com o texto `THE MACHINE LIED`.
- Composição: radar/alerta vermelho abstrato no bunker, céu vazio e operador anônimo; sem retrato reconhecível, sem interface soviética literal e sem alegação de imagem histórica.
- Dimensões normalizadas: 1080×1920. SHA-256: `60264e880f1260083241f34846322caf1262c992911a5f15557dd27877dec96`. Library file id: `libfile_6be06bdc4d04819183b0742de464c9cd`.
- Estado: `CANDIDATE_READY_FOR_HUMAN_REVIEW`; margens, legibilidade, direitos finais e delivery ainda não foram aprovados.
- O registro de produção continua bloqueado por direitos visuais manifest-only e thumbnail não finalizada. Render e publicação não foram executados.
- Próximo passo único: revisar visualmente esta nova candidata e decidir se ela deve avançar para QA final.


## Atualização — thumbnail final aprovada e delivery empacotado — 2026-11-05

- O usuário aprovou a candidata `THE MACHINE LIED` como thumbnail final do Episódio 005.
- QA técnico aprovado: master PNG/JPG e source frame em 1080×1920; preview mobile em 540×960; registro de aplicação por plataforma presente.
- Master PNG: SHA-256 `60264e880f1260083241f34846322caf1262c992911a5f15557dd27877dec96`; Library file id `libfile_6be06bdc4d04819183b0742de464c9cd`.
- `thumbnail_manifest`: `APPROVED`; `THUMBNAIL_QA`: PASS; `THUMBNAIL_FILES`: PASS. O validador foi corrigido para reconhecer corretamente o preview mobile 540×960, sem enfraquecer o requisito do master 1080×1920.
- O canonical entrypoint continua BLOCKED somente por `rights_ledger` manifest-only; os 16 assets visuais seguem `approved_for_render=false`. `production_enablement=false`, render NOT_RUN e publicação MANUAL_ONLY_NOT_RUN permanecem inalterados.
- Próximo passo único: revisar e aprovar formalmente os direitos dos 16 assets visuais antes de qualquer promoção para render; não habilitar publicação automática.


## Atualização — auditoria remota de direitos dos 16 assets — 2026-11-05

- As 16 páginas de origem foram reabertas e permaneceram acessíveis: 7 assets Mixkit e 9 assets Pixabay. Os títulos das páginas continuam identificando os itens como vídeos gratuitos.
- A licença oficial do Mixkit confirma uso comercial para itens sob a Free License, mas o próprio provedor mantém também uma Restricted License. Por isso, cada item precisa manter a evidência específica da página e o creator/author registrado; o ledger atual ainda tem o campo de autor não registrado para os 7 Mixkit.
- A licença oficial do Pixabay permite uso comercial e adaptação, mas ressalva conteúdo em estado standalone, marcas, pessoas reconhecíveis, direitos de imagem/privacidade e uso enganoso. Os assets com pessoas ou elementos potencialmente identificáveis não podem ser promovidos automaticamente sem QA visual e checagem de terceiros.
- O ledger mantém SHA-256, fingerprint perceptual, URL da fonte, URL da evidência, escopo de plataforma e uso único por episódio para os 16 assets. Não foi alterada nenhuma flag de promoção.
- Estado preservado: 16/16 APPROVED_FOR_MANIFEST_ONLY, 0/16 approved_for_render, catálogo global não atualizado, Drive não escrito, render não executado e publicação manual-only.
- Bloqueios remanescentes: (1) completar creator/author e confirmação da Free License nos 7 Mixkit; (2) concluir QA visual de pessoas, marcas e elementos de terceiros nos 16 assets, especialmente os shots S03, S04 e qualquer frame com conteúdo identificável; (3) somente depois registrar aprovação de direitos para render.
- Referências oficiais de licença: https://mixkit.co/license/modal/videoFree/ e https://pixabay.com/service/license-summary/.
- Próximo passo único: completar a ficha de direitos por asset e registrar aprovação explícita para render apenas nos itens que passarem essa verificação; não habilitar produção ou publicação automática.

- Foi criada a ficha individual `episodes/episode-005/rights/rights-audit-v21.json`, com 16 assets, URLs, licença declarada, SHA-256, fingerprint, shots atribuídos e pendências de direitos por item. O arquivo é somente auditoria; não altera nenhuma autorização de render.

- QA visual inicial dos shots S03 e S04 concluído no navegador: S03 mostra mãos/braço e creator identificado como Edgar Fernandez; S04 mostra apenas uma mão no painel, sem rosto e sem marca aparente. A evidência foi registrada na ficha, mas a revisão do arquivo completo e a aprovação para render continuam pendentes.

- QA integral dos 14 assets restantes executada por inspeção de páginas: os 5 Mixkit restantes exibem preview/licença; os 9 Pixabay exibem licença e página do item, porém o preview de mídia não foi renderizado neste navegador. Regra aplicada: licença de provedor não equivale a QA visual; nenhum asset foi promovido.
- Estado ajustado na ficha: Pixabay = `BLOCKED_BROWSER_PREVIEW_NOT_RENDERED`; Mixkit sem S03/S04 = `PENDING_FULL_FILE_QA`; S03/S04 = preview sem rosto, mas arquivo completo ainda pendente.

## Addendum — QA visual direta dos arquivos e correção de candidato — 2026-11-05

- A inspeção direta das amostras integrais foi concluída para S05, S08, S09, S13, S14, S15 e S16 usando os artifacts de intake 13437466569 e 13428247933, com contact sheets de cinco posições normalizadas e crop 9:16.
- S05 (pixabay-alert-alarm-war-danger-risk-205519) foi reprovado: o arquivo mostra um rosto adulto claramente reconhecível. A página do provedor também exibe alerta contra uso de imagens com pessoas reconhecíveis. O candidato foi marcado como REJECTED_CANDIDATE_REQUIRES_REPLACEMENT e não pode avançar.
- S08 radar, S09 botão vermelho, S13 máquina de escrever, S14 corredor, S15 flare abstrato e S16 partículas passaram a inspeção visual direta sem marca/logotipo identificável; S13 ficou registrado com guardrail de mecanismo genérico.
- S06 LED e S12 antena continuam sem QA direta do arquivo completo nesta etapa; não foram promovidos por licença de provedor ou inspeção de página.
- A ficha episodes/episode-005/rights/rights-audit-v21.json foi atualizada no commit 1e54e021ee2ca70125acb26505a532451a37b42a, mantendo approved_for_render=false, global_catalog_updated=false, drive_written=false e publication_authorized=false.
- O bloqueio correto agora é composto por: substituição do S05, QA integral pendente de S03/S04/S06/S12, confirmação final dos itens Mixkit pendentes e aprovação explícita de render por asset. A licença não foi tratada como autorização de render.
- Próximo passo único: substituir o candidato reprovado de S05 e completar a QA direta dos arquivos ainda pendentes; render, catálogo global, Drive e publicação permanecem bloqueados.

## Addendum — reconciliação do PR e validação CI após correções — 2026-11-05

- A auditoria de integração encontrou o PR 67 inicialmente `dirty`: a `main` estava três commits à frente, todos relacionados aos workflows visuais. A comparação confirmou que a branch já possuía versões posteriores e mais completas dos mesmos workflows, incluindo amostragem integral, runner `ubuntu-24.04` e FFmpeg estático limitado.
- A ancestralidade foi reconciliada preservando a árvore da branch no merge commit `b42fb6d3636a941141ce60ba9ed5e703dac2e2f7`, com `behind_by=0`; o PR voltou a `mergeable=true` e permanece draft. Nenhum código do motor foi descartado.
- O novo CI revelou duas inconsistências e ambas foram corrigidas: (1) o runner não instalava Pillow para inspeção dimensional dos arquivos de thumbnail; (2) o teste ainda esperava `THUMBNAIL_QA` bloqueado, apesar da thumbnail estar aprovada. Foi adicionada a instalação explícita de `Pillow==11.3.0` e a expectativa foi alinhada para exigir somente `rights_ledger` como bloqueio.
- Evidência final: CI canônico run `42119507950` — success; integração V2.1 run `42119507933` — success; captions congeladas run `42119507986` — success. No relatório: `THUMBNAIL_QA=PASS`, `THUMBNAIL_FILES=PASS`, `rights_ledger=BLOCKED`, render `NOT_RUN`, publicação `MANUAL_ONLY_NOT_RUN`.
- Estado preservado: `production_enablement=false`, todos os assets ainda `approved_for_render=false`, catálogo global não atualizado, Drive não escrito e publicação não autorizada.
- Próximo passo único: substituir o candidato S05 reprovado e concluir QA direta dos arquivos pendentes; não promover direitos para render antes desses gates.

## Addendum — substituição segura do S05 e revalidação final — 2026-11-05

- O candidato S05 `pixabay-alert-alarm-war-danger-risk-205519` foi removido da promoção após QA direta confirmar rosto reconhecível. Ele permanece apenas como histórico rejeitado no plano, com razão e artifact preservados.
- A alternativa já intakeada `pixabay-radar-black-green-target-symbol-57670` foi inspecionada nas cinco amostras normalizadas: radar/target genérico, sem pessoa reconhecível, marca ou texto de terceiros. Ela foi promovida somente para `APPROVED_FOR_MANIFEST_ONLY` em S05.
- Plano, manifesto e ficha de direitos foram atualizados em sequência para evitar commits órfãos. O manifesto mantém 16 assets, 16/16 shots atribuídos, 21 candidatos aprovados para manifesto, `promotion_allowed=false` e `render_allowed=false`.
- Revalidação final no head `d220fdead9c25170a22227ae50bbb84247f1b871`: CI canônico run `42120350391` — success; integração V2.1 run `42120350465` — success; captions congeladas run `42120350398` — success. O PR 67 está `mergeable=true`, aberto e draft.
- Direitos continuam sem promoção: todos os 16 assets permanecem `approved_for_render=false`; catálogo global, Drive, render e publicação seguem bloqueados. A ficha de direitos permanece globalmente bloqueada por QA/licença final pendente e aprovação explícita por asset.
- Próximo passo único: concluir a QA direta dos Mixkit S01/S02/S03/S04/S07/S10/S11 e dos Pixabay S06/S12; só depois avaliar aprovação explícita de render por asset.

## Addendum — QA visual direta completa e CI pós-gate — 2026-11-05

- A QA visual direta dos arquivos integrais foi concluída para os nove assets que ainda estavam pendentes nesta etapa: Mixkit S01, S02, S03, S04, S07, S10 e S11; Pixabay S06 e S12.
- Evidências utilizadas: artifacts de intake GitHub `13403209885`, `13403188677`, `13404636511`, `13406364533`, `13409661379`, `13411851653`, `13412703858`, `13426556747` e `13427442382`. Cada revisão considerou as cinco amostras normalizadas — início, 25%, 50%, 75% e final — e o crop vertical 9:16.
- Resultado: os nove assets passaram na inspeção visual direta. Não foram observadas pessoas reconhecíveis, marcas identificáveis, watermarks ou letterbox nos arquivos aprovados.
- Guardrails editoriais registrados: S03 usa tela genérica sem tratar o conteúdo como interface histórica; S04 usa painel industrial genérico sem alegação documental; S10 usa mecanismo/calendário genérico sem leitura histórica literal; S12 usa antena/infraestrutura representacional, nunca evidência literal do incidente. S13 permanece aprovado com guardrail equivalente para mecanismo genérico.
- A correção do S05 permanece válida: o candidato com rosto reconhecível continua rejeitado no histórico e o radar/target `pixabay-radar-black-green-target-symbol-57670` é o substituto ativo, aprovado apenas para manifesto.
- Estado consolidado da ficha de direitos: 16/16 assets com `full_asset_review_status=PASS_DIRECT_MEDIA_PREVIEW`; 0/16 com aprovação de render. A diferença entre QA visual aprovada e autorização de render foi preservada deliberadamente.
- O ledger ainda mantém pendência de author/creator e confirmação específica da Free License para cinco itens Mixkit: S01, S02, S07, S10 e S11. S03 e S04 já têm creator registrado; Pixabay segue sujeito às ressalvas de pessoas, marcas, privacidade e uso standalone da licença.
- CI no head `202e9ec2c93705eeb0536e30029cf1b732ec6eb5`: Canonical engine CI run `42124233586` — success; V2.1 canonical integration run `42124233599` — success; Frozen native captions run `42124233568` — success.
- Estado de segurança não mudou: `production_enablement=false`, `approved_for_render=0/16`, `global_catalog_updated=false`, `drive_written=false`, render `NOT_RUN` e publicação `MANUAL_ONLY_NOT_RUN`.
- Próximo gate único: confirmar os cinco creators/licenças Mixkit no ledger e, em seguida, preparar a aprovação explícita de render por asset; não executar render, catálogo global, Drive ou publicação antes dessa confirmação.

## Addendum — reconciliação final de contributors Mixkit e CI — 2026-11-05

- As cinco pendências de autoria/licença foram verificadas diretamente nas páginas oficiais dos itens Mixkit e reconciliadas no plano e no ledger.
- Contributors confirmados:
  - S01 `mixkit-abstract-red-glow-101432`: Mixkit — https://mixkit.co/@mixkit/
  - S07 `mixkit-slowly-approaching-clock-28897`: Arvizum — https://mixkit.co/@arvizum/
  - S11 `mixkit-cloudy-sky-118`: Edgar Fernandez — https://mixkit.co/@edgarfernandez/
  - S10 `mixkit-clock-mechanism-3651`: Edgar Fernandez — https://mixkit.co/@edgarfernandez/
  - S02 `mixkit-large-satellite-antenna-2650`: Matthias Groeneveld — https://mixkit.co/@matthiasgroeneveld/
- Em todos os cinco itens, a própria página exibiu `Mixkit Stock Video Free License`, com uso comercial ou pessoal, e essa evidência foi registrada junto ao contributor. Não foi inferido autor a partir de nome de arquivo ou de busca externa.
- O ledger agora reúne os sete contributors Mixkit: os cinco confirmados nesta etapa e Edgar Fernandez já confirmado anteriormente em S03/S04.
- A ficha de direitos deixou de bloquear por autoria/licença Mixkit. O bloqueio correto restante é apenas a aprovação explícita de render por asset, mantendo a separação entre `PASS_DIRECT_MEDIA_PREVIEW`, licença verificada e autorização de produção.
- CI após a reconciliação, head `ae26491d7858e26e2719d33cfec5e951a35d831f`: Canonical engine CI run `42124873659` — success; Frozen Episode 005 Captions run `42124873702` — success; V2.1 canonical integration run `42124873737` — success.
- Estado de promoção permanece fechado: `production_enablement=false`, `approved_for_render=0/16`, `global_catalog_updated=false`, `drive_written=false`, render `NOT_RUN` e publicação `MANUAL_ONLY_NOT_RUN`.
- Próximo gate único: obter/registrar aprovação explícita de render por asset e só então executar o preflight manual fail-closed; nenhuma publicação automática será habilitada.

## Addendum — aprovação explícita de render e correção do contrato canônico — 2026-11-05

- O usuário aprovou explicitamente a utilização dos 16 assets ativos no render do Episódio 005.
- A aprovação foi registrada no ledger de direitos e no production record com escopo `episode-005-render`, mantendo as restrições: `production_enablement=false`, sem catálogo global, sem Drive e com publicação manual-only.
- O arquivo `scene-asset-manifest.json` permanece deliberadamente `APPROVED_FOR_MANIFEST_ONLY`. Isso não é conflito: o validador estrutural exige que o manifesto visual não autorize render; a autorização de render fica no rights ledger e no production record.
- O primeiro preflight CI encontrou dois conflitos reais:
  - o vocabulário canônico do production record exige `rights_status=APPROVED`, enquanto o ledger de auditoria usa `APPROVED_FOR_RENDER`;
  - `RENDER_PREFLIGHT` não é um estado válido do `pipeline_state_v21`.
- Ambos foram corrigidos: o production record usa `rights_status=APPROVED`, `approved_for_render=true` e o estado válido `THUMBNAIL_QA`.
- O workflow canônico foi ajustado para validar um production record completo e aprovado sem confundir validação contratual com execução: o resultado esperado agora é `status=PASS`, `production_enablement=false`, `media_generation=NOT_RUN`, `render=NOT_RUN` e `publication=MANUAL_ONLY_NOT_RUN`.
- CI após a correção: Canonical engine CI run `42126150010` — success; V2.1 canonical integration run `42126150092` — success; Frozen Episode 005 Captions run `42126149955` — success.
- O preflight manual de render não foi executado: a workflow `.github/workflows/episode005-v21-manual-render.yml` existe somente na branch candidata e ainda não está exposta pelo Actions da revisão-base. Nenhum merge foi realizado para disponibilizá-la.
- Estado atual: direitos aprovados para render, contrato canônico validado, produção ainda desabilitada, render `NOT_RUN`, Drive não escrito e publicação não executada.
- Próximo gate único: decisão explícita sobre tornar a workflow manual disponível na revisão-base; somente depois executar o preflight `preview`, que deve permanecer fail-closed enquanto `production_enablement=false`.

## Addendum auditado — integração segura, rastreabilidade e provas (2026-11-07)

**Authority:** `production/active_engine_policy.json`. Perfil ativo V2.1, narrativa factual, Gemini TTS/Charon, `production_enablement=false`, `preview_enablement=true`, publicação exclusivamente manual. O `canonical_entrypoint.py` é um validador somente leitura, não um renderer.

### Integrado na main (verificar pelos PRs e commits, não por memória de conversa)

- [PR #122](https://github.com/BORELLITO/because-of-this-engine/pull/122), merge `fe49022d44f7991c886121d3204f7aa80cbc1787`: housekeeping semanal convertido para inventário READ-ONLY; rotas Edge TTS/legendas congeladas removidas de Actions ativas e arquivadas; singleton guard, verificação de identidade visual e testes de evidência; direitos, narrativas e legendas sem promoção automática. Rollback pré-merge `backup/main-pre-safety-20261107`.
- [PR #123](https://github.com/BORELLITO/because-of-this-engine/pull/123), merge `009722aa64ef889adb5baa5972e47e7a4e42890b`: `VISUAL_RIGHTS_CONSISTENCY` impede passar direitos de mídias antigas para novas. Comparação plano → manifesto → direitos, hashes, fingerprint, autorizações e escopo; CI usa prova negativa controlada.
- [PR #124](https://github.com/BORELLITO/because-of-this-engine/pull/124), merge `dfbb2143b3819ebeddfcd77628746cd87ed269e8`: `AUDIO_HISTORY_COVERAGE` read-only e bloqueio no preflight final; inventário de cinco manifestos históricos. Registro `audio-memory-registry.json` ainda com zero faixas e não deve ser declarado completo.
- [PR #125](https://github.com/BORELLITO/because-of-this-engine/pull/125) hotfix a promover somente após testes: a narração congelada do Episódio 006 foi sintetizada a partir de `read_text().strip()`; o verificador introduzido no PR #122 não pode incluir o newline final no hash. Identidade TTS aprovada `412c4bfa1c26abd7631ec1cad74cae2e07b6d33012631bbbac53df8c8e0b3112`; arquivo-fonte cru termina com newline e tem outro hash. Nenhuma nova voz será gerada por esse ajuste.

### Evidências verificadas e bloqueios

- Backups dos checkpoints: Episode 006 voz, Episode 006 voz+legendas e Episode 005 preview copiados para Google Drive; as três cópias foram recuperadas, hashes SHA-256 coincidiram com origem e todos ZIPs passaram no CRC. Recibos: `reports/ARTIFACT_PROTECTION_20261107.json`.
- CI V2.1 principal passou após PRs #122, #123 e #124. Isso comprova contratos e bloqueios esperados, **não uma execução audiovisual final**.
- Episode 005: manifesto visual inclui 16 clipes, porém somente 9 IDs correspondem às entradas de direitos; sete direitos antigos não representam sete substitutos. S09 `pexels-12213087` tem aprovação humana pendente no plano e fingerprint divergente no manifesto. O estado correto de `VISUAL_RIGHTS_CONSISTENCY` é BLOCKED até reconciliação e evidências reais, nunca auto-APPROVED.
- Histórico de áudio: cinco manifestos declaram trilhas; Episodes 001/002 indicam o mesmo Drive ID de música. Isso é uma duplicação **documental** de identidade, não prova de uso em material publicado. Auditar master e histórico antes de definir `coverage_status=VERIFIED_COMPLETE`. Detalhes: `reports/AUDIO_HISTORY_DISCOVERY_20261107.json`.
- Episode 006: checkpoint WAV real 73,64 s, 24 kHz mono, 164 palavras alinhadas, 21 eventos ASS; revisão perceptiva palavra a palavra e QA visual final continuam pendentes. A frase sobre qual bomba foi enterrada em Goldsboro está sob revisão factual em `episodes/episode-006/FACT_REVIEW_20261107.md`.
- Não houve publicação externa, Drive write de mídia final, novas chamadas TTS, render final ou alteração da identidade Charon/HUD aprovada durante esses upgrades.

**Próximo passo único:** reconciliar com evidência real as sete entradas de direitos faltantes do Episode 005 e a aprovação do candidato S09, sem promover qualquer estado por inferência; depois auditar o catálogo de áudio e os materiais reais antes de solicitar outro preflight de produção. A política permanece fail-closed.

### Upgrade de Reconciliação Visual — PR #126 integrado (2026-11-07)

- **Commit principal:** `9a1f7ea14b8a005322f4de809dd97ad16b8cdc7a`. PR #126: https://github.com/BORELLITO/because-of-this-engine/pull/126
- **Estado:** motor V2.1 Gemini/Charon preservado, `production_enablement=false`, publicação manual, nenhum render nem TTS novo executado. CI pós-merge aprovada: https://github.com/BORELLITO/because-of-this-engine/actions/runs/42386983454
- **Módulo novo (somente leitura):** `production/visual_reconciliation_dossier_v21.py`. Emite diagnóstico determinístico e propostas de registros `PENDING_INDEPENDENT_RENDER_RIGHTS` com `approved_for_render=false`. Não altera manifestos, direitos, vídeos nem configurações.
- **Inventário evidencial:** `reports/EP005_VISUAL_RECONCILIATION_EVIDENCE_20261107.json`. Dos 16 clipes ativos, **9 correspondem ao registro de direitos**, **6** têm aprovação apenas para o manifesto, **1** (S09) aguarda aprovação visual, e existem **7 entradas históricas** de direitos que não correspondem à seleção atual.
- **S09 recuperado:** GitHub Actions artifact `13480857827`, 99.183.545 bytes, ZIP SHA-256 `399aeb023d1a062f53dedb708b561edcd15914db5a8237050b85cc30de653c9c`, igual ao registro original e à cópia recuperada do Drive; integridade ZIP/CRC PASS. Arquivo interno `pexels-12213087/candidate.mp4`: SHA-256 `4a97068a2888c1146b238795504698709d38771e31f6d1f75ba2beaa12718c51`, igual ao plano. Cópia preservada no Google Drive ID `1EqPoDJMGD-vKA0RALPftABinqCUTi00p`.
- **Observação visual S09:** amostras nativas e 9:16 mostram mão regulando **mesa de som**, não um painel soviético de defesa; no máximo imagem representacional explicitamente não literal. A revisão humana do plano está PENDING; o fingerprint do manifesto permanece divergente. Não liberar automaticamente.
- **Políticas consultadas:** páginas oficiais das licenças Pexels, Pixabay e diretrizes NASA. O clipe NASA SVS 4819 é *modelagem de nuvens GEOS-5 de 2020* e não documento da defesa de 1983; deve ter contexto e atribuição corretos, sem sugerir endosso NASA. Licença geral não é aprovação individual de render.
- **Próximo passo:** verificar autorizações específicas das seis mídias, inspecionar completamente as evidências e colher decisão editorial para S09; reconciliar os IDs e hashes com evidências antes de alterar `rights_ledger` ou executar novo preflight. Proteções de `VISUAL_RIGHTS_CONSISTENCY` e `AUDIO_HISTORY_COVERAGE` continuam BLOQUEADAS até prova real.

### Estudo real S09 / revisão de direitos — 2026-11-07

- Busca e download de candidatos gratuitos no Pexels, sempre em workflow experimental isolado. Nenhum asset foi incorporado ao plano/manifesto ativo.
- `pexels-6442793` (ArtHouse Studio, 1920x1080/24fps/8,255s) teve **cinco amostras nativas e verticais examinadas**. A descrição prometia radar analógico, mas o vídeo mostra equipamento parecido com monitor/vectorscópio, inscrições modernas e iluminação verde contemporânea; **reprovado por incoerência**. SHA vídeo `062be75f253bd3a9681c835c9a1f69e789357fc7b04562d98c64e66f9d82712a`; run #42388122655.
- `pexels-8888977` (MART PRODUCTION, 4096x2160/25fps/24,6s) passou no download/ffprobe/CRC e inspeção das cinco amostras e recortes 9:16: mãos digitando teclado bege de aparência antiga sob luz baixa. **Melhor candidato para representar a entrada da classificação S09**, nunca arquivo histórico de Petrov/1983. SHA do vídeo original `b5e41fafc252a88d3959fbb3df0294010397e6687d833d884bc5a0bfdd48fa51`. Run GitHub #42388510746, artifact #13580144522.
- Preview de QA gerado (4s, 1080x1920, 60fps duplicados a partir de fonte nativa 25fps, áudio removido), SHA `9e13600c4f2ccbf3836334d56591835ae353cedb65dd291d2b7cc28d6a1f0784`. É apenas prova de corte técnico, não preview do episódio final.
- Artefato #13580144522 copiado para Drive ID `1rdUiMhgJ05YK8CMRsqB2VqzBq3KE_N_E`; restaurado e verificado SHA-256 `c7dbc26fc3da1d80036f962df6f9df2266ad26ef7af413fbef0cce195094a338`, integridade ZIP/CRC correta. Arquivos originais preservados.
- Evidências versionadas: `reports/EP005_S09_CANDIDATE_COMPARISON_20261107.json` e `reports/EP005_SIX_ASSET_LICENSE_REVIEW_20261107.json`. Seis mídias verificadas em páginas individuais e termos Pexels/Pixabay/NASA; metadados/fingerprints internos correspondem ao manifesto, mas **não há seis direitos independentes aprovados para render**. Pessoa em stock, marcas ou contexto falso devem ser revistos. NASA SVS 4819 exige contexto de visualização GEOS-5 2020 e créditos.
- Workflow experimental arquivado em `archive/v21/workflows/episode005-s09-candidate-qa-runbook-20261107.yml` após uso; **nenhum novo workflow ativo introduzido**.
- `pexels-12213087` permanece como S09 do manifesto ativo, com conflito e bloqueio; `pexels-8888977` é somente candidato preferencial. Nenhuma promoção de direitos, mudança canônica de cena, história, Charon, legendas, áudio, output ou publicação.
- **Próximo passo único:** obter a decisão editorial humana sobre o teclado retro, verificar nova impressão perceptual e histórico global de reuso, reconciliar permissões de render para os seis clipes e a fonte S09, depois propor numa revisão separada a troca efetiva do ativo. CI verde aqui prova qualidade de contratos, não direitos de publicação.

### S09 escolhido pelo usuário e fingerprint físico comprovado — 2026-11-07

**Decisão editorial recebida:** após o preview de 4 segundos, o usuário autorizou seguir com a recomendação. A mídia `pexels-8888977` (MART PRODUCTION, mãos digitando teclado retrô, representação simbólica) substitui `pexels-12213087` (mesa de som) APENAS no plano de aquisição e no manifesto de cenas. Fonte original `pexels-12213087` permanece no plano como histórico para rollback. Nenhuma edição do áudio, vídeo final, direitos, catálogo global ou publicação.

**Prova real do arquivo:** SHA-256 original `b5e41fafc252a88d3959fbb3df0294010397e6687d833d884bc5a0bfdd48fa51`. Fingerprint `video-fingerprint-v2-rgb24-q4`: `11084cf2f2f6ddf92255d82bcb19c5cc04003c2dbc1b7c21f0bf617aa87915a8`. GitHub Action bem-sucedida #42390022588, artefato #13581475505 (digest ZIP `87ebe742d0f9816f6f8f37152ca8963007f3524fa826fcd7c55292d01d6cf819`). Confrontadas **13 entradas** do catálogo global e **56 cenas** de 5 manifestos históricos: **zero colisões**. Isso não cobre fontes externas ou outras mídias não catalogadas. Arquivo bruto 4096×2160 @ 25 fps, 24,6 s, sem trilha de áudio. A amostra de 4s em 1080×1920 @ 60 fps duplica frames; não tem 60 fps nativos.

**Aprovação registrada no código:** `episodes/episode-005/visual/asset-acquisition-plan.json` e `episodes/episode-005/visual/scene-asset-manifest.json` — `APPROVED_FOR_MANIFEST_ONLY`, `human_approval=APPROVED_FOR_MANIFEST` com origem textual explícita da decisão do usuário. `approved_for_render=false`, `global_catalog_updated=false`, `drive_written=false`. A referência histórica permanece em `reports/EP005_S09_CANDIDATE_COMPARISON_20261107.json`; prova da promoção atual em `reports/EP005_S09_APPROVED_MANIFEST_ONLY_20261107.json`.

**Licença e riscos:** Pexels permite usos comerciais conforme licença geral, mas marcas, pessoas identificáveis e associações enganosas podem exigir cuidados. Retratar teclado genérico como o console real de 1983 ou o operador como Petrov é proibido. Direitos individuais de render, revisão final de pessoas/elementos do quadro, histórico global de áudio e conformidade editorial permanecem pendentes. Os **sete IDs** ainda ausentes no ledger de render não foram preenchidos com aprovações inventadas. Registros dos antigos direitos não foram apagados.

**Estado esperado da CI:** `VISUAL_PLAN_CONTRACT_PASS` (apenas plano e manifesto) enquanto `VISUAL_RIGHTS_CONSISTENCY=BLOCKED` e `AUDIO_HISTORY_COVERAGE=BLOCKED`. Produção e publicação continuam bloqueadas/manual. Qualquer futura autorização para render exige evidência própria, testes e liberação explícita.

**Único próximo passo:** reconciliar seis direitos independentes de fontes atuais + S09 (Pexels 8888977), mantendo os sete direitos antigos rastreáveis, e fazer preflight completo apenas após comprovação individual.

### Reconciliação estrutural dos sete direitos de render do Episode 005 — 2026-11-07

**Objetivo:** eliminar a discrepância entre 16 clipes atualmente selecionados e 16 entradas do antigo ledger que incluíam sete autorizações para mídias descartadas.

**Mudança efetiva na branch, sujeita à CI/PR:** `episodes/episode-005/production-record.json` agora registra exatamente os **16 IDs do manifesto atual**, preservando as **nove entradas anteriormente aprovadas** sem modificações e substituindo no cadastro ativo os sete IDs antigos pelos **sete ID/hash/fingerprint corretos**, todos com `rights_status=PENDING_INDEPENDENT_RENDER_RIGHTS`, `approved_for_render=false`, `commercial_use=false`, `approval_scope=null`, `used_by=[]` e escopo autorizado vazio. Isso é reconciliação de identidade e fila de pendências, **não** concessão de licenças, uso efetivo ou autorização de render.

**Histórico preservado:** backup principal `backup/main-before-ep005-rights-ledger-20261107`, e snapshot íntegro `reports/archives/EP005_RIGHTS_LEDGER_BEFORE_ACTIVE_RECONCILIATION_20261107.json` contendo as 16 entradas originais e destacando as sete aprovadas para cenas agora aposentadas. Licenças antigas jamais migradas automaticamente para os substitutos.

**Referência individual:** `reports/EP005_ACTIVE_RIGHTS_RECONCILIATION_20261107.json` enumera os sete clipes ativos, artista quando confirmado, fonte original, SHA-256, fingerprint, termos oficiais Pexels/Pixabay/NASA e restrições históricas, de marcas/pessoas e propaganda. NASA SVS 4819 é uma visualização **GEOS-5 de 2020**, não uma gravação real dos sensores soviéticos de 1983; creditar NASA Scientific Visualization Studio, Greg Shirah e Trent L. Schindler, e não insinuar endosso.

**Testes obrigatórios:** cobertura de identidade exata 16/16, snapshot histórico idêntico, nove aprovações intactas, sete pendências sem `used_by` ou direitos concedidos, hashes iguais ao arquivo de aquisição, e testes negativos impedindo liberação ao editar somente um campo. A CI precisa exigir `rights_ledger=BLOCKED`, `VISUAL_RIGHTS_CONSISTENCY=BLOCKED`, `AUDIO_HISTORY_COVERAGE=BLOCKED`, enquanto o contrato de manifesto segue `PASS`. Um teste negativo aprovado não equivale a produção liberada.

**Próximo passo único:** concluir revisão individual de marcas, pessoas, fidelidade histórica e comprovação do escopo comercial/YouTube/TikTok; autorizar cada entrada somente após evidência verificável, sem trocar novamente S09 nem gerar áudio, e revisar também o histórico global de trilhas antes do preflight final.

### 2026-11-07 — Motor de aprovação AUTÔNOMA por evidência (V2.1)

O usuário determinou explicitamente que o próprio motor deve **decidir se o clipe está apto**, sem pedidos repetidos de aprovação. A implementação em `production/rights_autonomy_v21.py` avalia origem oficial/termos, SHA-256 e fingerprint correspondentes ao vídeo real recuperado, inspeção de cinco amostras 9:16, rosto/marcas, classe factual, áudio externo, histórico conhecido de reuso e requisitos de crédito. No modo atual, a decisão automatizada consome a evidência visual previamente estruturada em `reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json`. Para mídias futuras, é preciso alimentar essa evidência com um processo automático de visão, sem afirmar que ela já é feita fim a fim.

**Cinco decisões autônomas elegíveis ao render editorial daquele episódio:** S04 rádio vintage, S05 radar gráfico, S06 luz vermelha, S09 teclado retrô, S11 céu noturno. Direitos `APPROVED`, `commercial_use=true`, `approved_for_render=true`, com `render_approval_status=AUTO_APPROVED_EVIDENCE_BOUND_V21` e escopo estrito `episode-005-render`. Não representam verdade documental primária, pessoas reais do incidente ou publicação aprovada. `used_by` indica intenção autorizada, não vídeo publicado.

**Duas recusas fundamentadas do próprio motor:** S03 homem com rosto identificável (não atribuir ao Petrov ou operador soviético verdadeiro); S12 NASA modelo atmosférico de 2020 (precisa prova de crédito NASA SVS/Greg Shirah/Trent L. Schindler e aviso de que não se trata de dados do sistema soviético de 1983). O motor decide BLOQUEAR e deve tentar resolver/substituir autonomamente sem pedir liberação genérica ao usuário.

**Segurança:** fonte e fingerprint da cena não foram alterados; antigos nove direitos preservados; o histórico de áudio ainda está INCOMPLETO. `RIGHTS_AUTONOMY_V21` é gate adicional canônico e do pré-voo manual. O episódio não está apto a publicação nem a render final, Gemini/Charon e regras de mídia mantidos. Este estágio distingue autonomia **do decisor** versus automação completa de novas análises visuais, que ainda exige integrar visão upstream e validação do render composto.

Documentação de política, decisões e fontes: `docs/RIGHTS_AUTONOMY_V21.md`.

### 2026-11-07 — Bloqueios visuais S01 e S12 resolvidos por evidências reais

**Atualização de autoridade**: após o PR #131 (decisor automático), o próximo upgrade revisou a cena REAL no `scene-asset-manifest.json` e descobriu discrepância em `source_role`: o ator Pexels `pexels-11764431` está no **S01** (gancho de 0–4s), não no S03; o rádio `pixabay-radio-vintage-old-171435` está no S03, não no S04. O `source_role` legado é histórico e não deve controlar o render; a verdade executável é `shot_assignments`.

**Decisão autônoma sobre a cena S01**: cinco vídeos de mãos sem rosto foram baixados em workflows isolados, comparados quanto a SHA, fingerprint, 9:16, luz, época, emoção e coerência. Todos foram reprovados por modernidade, brilho, recorte que perdia gesto ou carta romântica legível. Em vez de sacrificar o gancho aprovado, o motor manteve o clipe escuro original e configurou texto legível **DRAMATIZATION - NOT ARCHIVAL FOOTAGE**, garantindo que o ator não seja identificado como Stanislav Petrov, e créditos/isenção também na descrição de plataformas. Preview real 4s @1080×1920/60fps e frame SHA registrados em `reports/EP005_S01_S12_TRUTH_LABEL_QA_20261107.json`. A face continua visível — não declarar anonimização.

**Decisão autônoma sobre a cena S12**: NASA SVS GEOS-5 de 2020 continua como visualização simbólica, não como registro militar de 1983. O texto exato **NASA GEOS-5 MODEL (2020)** e **Illustration - NOT 1983 sensor footage** foi aplicado em sample real 5s @1080×1920/60fps; SHA e frame conferidos. Créditos da página oficial `https://svs.gsfc.nasa.gov/4819/`: NASA Scientific Visualization Studio, Greg Shirah, Trent L. Schindler, Ryan Fitzgibbons; sem alegação de endosso. Texto completo está em `episodes/episode-005/visual/scene-disclosures-v21.json`.

**Integração rígida**: `production/scene_disclosures_v21.py` valida IDs, SHA, posição exata S01/S12, status de representação, textos de aviso, dados de créditos, hash de samples, duas plataformas e `publication_policy=manual_only`. `render_v21_preview.py` queima avisos **somente** nas cenas correspondentes. Os validadores canônico e manual ganharam o gate `SCENE_DISCLOSURES_V21`, e `rights_autonomy_v21.py` só considera o ator reconhecível e NASA aptos a render editorial **quando o contrato de disclaimers verificado passa**. Sem contrato o motor BLOQUEIA. O rights ledger mantém as 9 aprovações anteriores e as 7 novas, todas com escopo ao Episode005 e sem publicação.

**O que os testes NÃO comprovam**: nenhum vídeo final composto do Episode005 foi executado, a sincronia de áudio/legendas do master não foi revisada, as descrições das plataformas ainda não foram efetivamente publicadas e não houve autorização para postagem. `final_assembled_video_metadata_verified=false`. O histórico global de áudio `episodes/audio-memory-registry.json` continua vazio e `AUDIO_HISTORY_COVERAGE=BLOCKED`. `production_enablement=false`, Gemini TTS/Charon travado, publicação manual, nenhuma chamada TTS adicional.

**Próximo passo único**: reconciliar áudio histórico com evidência real (músicas e efeitos realmente usados nos masters), sem marcar registro completo por inferência; posteriormente teste da montagem inteira e QA perceptiva antes de qualquer publicação. Arquivos antigos e fontes originais preservados.

### Áudio histórico — fontes originais recuperadas, masters ainda não comprovados (2026-11-07)

A auditoria do áudio deve distinguir **arquivo-fonte identificado**, **uso efetivo comprovado no master** e **licença/distribuição validada**. Essas são provas distintas; não promover automaticamente ao estado completo.

- Foram recuperados diretamente do Google Drive os três arquivos MP3 originais: `1bDbbr-bMA3puBvrQ2QzvSTfbicXJmdni` (Mixkit, 3.243.407 bytes, SHA-256 `144384cf2bcda8070a0d11c8aa98c3ae547de861a553275788669b7cf6a57bcd`), `1u-1ZKkVxKTw_E6vEzW0VcpF2lfjGfmeI` (Mixkit/Andrew Ev, 9.052.021 bytes, SHA-256 `49842074dc06f05a40690c2b3af42bd32be76a5f6505a65cfe952b2fe1ccb5de`), `1LJtxg5fXoheepYVK5HO1M1DhEo_pVIDg` (Pixabay/DELOSound, 4.353.462 bytes, SHA-256 `dd57de53251011da1cc72f22c81595e80c03151c46d4a43e71aa6baaf2bc98cc`). Todos decodificáveis em MP3 segundo `ffprobe`.
- O áudio Mixkit `871.mp3` está declarado igualmente nos manifestos dos Episodes 001 e 002, com o MESMO ID do Drive e o MESMO hash SHA-256 do arquivo original. **Colisão de fontes declaradas, não prova de música publicada duas vezes.** O histórico não deve silenciar essa divergência.
- O manifesto `episodes/video-001/manifest.json` declara a composição procedural `V73-PROCEDURAL-SUSPENSE-BED-001`, mas ainda sem a gravação final identificada e conferida independentemente. Não declarar esse áudio comprovado.
- `episodes/audio-memory-registry.json` passou de vazio para **cinco registros documentais**: 4 declarações de MP3 históricos (3 fontes distintas verificadas) + 1 geração procedural declarada. Cada um registra `actual_master_audio_verified=false`, `published_use_verified=false`, e `approved_for_new_episode_reuse=false`. `coverage_status=PARTIAL_SOURCE_VERIFIED_MASTERS_UNVERIFIED`. Os efeitos sonoros também não têm histórico de uso verificado.
- `production/audio_history_audit_v21.py` passou a exigir recibo verificável do master com hash do áudio mixado, hash do master, artefato e log de mix comprovando a presença da fonte, mais cobertura independente de SFX. Um campo `VERIFIED_COMPLETE` isolado ou uma mera declaração de hash não podem tornar o histórico PASS. A colisão histórica continua bloqueando aprovação global até reconciliação.
- Evidência detalhada: `reports/AUDIO_HISTORICAL_SOURCE_VERIFICATION_20261107.json`. Os diretórios de renders antigos encontrados no Drive não forneceram arquivos MP4 acessíveis na busca de seus subdiretórios principais. Nenhum render, voz, alteração de master, publicação ou consumo TTS nesta etapa.
- **Estado esperado pós-upgrade:** `AUDIO_HISTORY_COVERAGE=BLOCKED`; `verified_original_source_count=3`; `registry_track_count=5`; `verified_master_audio_count=0`. Autonomia não significa inventar evidências de uso. `production_enablement=false`, publicação manual, Gemini/Charon preservados.

**Próximo passo único:** localizar os masters históricos ou logs reais de mix, extrair o áudio e comparar evidências de trilhas/efeitos. Se os masters não estiverem disponíveis, manter os itens documentados como desconhecidos; não repetir músicas já declaradas em episódios novos.

### 2026-11-07 — Recuperação REAL dos quatro masters e quarentena da música reutilizada

A busca por nome, pasta e MIME no Google Drive não retornava os MP4s históricos. Investigação de logs antigos de **GitHub Actions** recuperou os IDs EXATOS de quatro masters no Drive. Os arquivos foram baixados integralmente e os SHA-256 foram calculados a partir dos bytes; cada um é **idêntico ao output_sha256 no respectivo log de execução**, com streams AAC verificados por FFprobe.

- **001 (V7):** Drive `1PJUyr6vSQhbBekRvh-byP592-8kKy511`, run `41103303509`, master SHA `6d019c3c5e2f2570b3bb975ca20de2e733140f8f380188880eebb2e3b7dc78b4`; trilha procedural `music.wav` original SHA `ada559a1f992984e1b501fd76639478501615c617fed5034c43e99a745521ccf`.
- **002 (V7):** Drive `1rfSdXGFr8xsXQNWU4AtqSUt7TIf9YGVy`, run `41248538051`, master SHA `0659c0cd5d2f07602cd21e147ac9587419039b8bc2ce6b31155920ae9d46a216`; trilha procedural `music.wav` do Drive `1P7NlvP50-V2Y8CaZQXPE2EhU99t_Zy9X`, SHA `4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24`.
- **003 (V2):** Drive `1Y1wPxgkXlIsm4JYAjOqOJfLtAv3jyVA-`, run `40616131845`, master SHA `b7af5dc8e534135da9d51f55b2419ca6124cb9717c51df397961cb37f975f682`; áudio mostra forte correspondência temporal com Mixkit Echoes, SHA original `49842074dc06f05a40690c2b3af42bd32be76a5f6505a65cfe952b2fe1ccb5de`.
- **004 (V7):** Drive `1YkgYxxniXZVTZK4iwgpgcSl6DP-aQJhn`, run `41376351220`, master SHA `9e9edc0e307301b8ea028174a63391b2eb56b7b8fe8a4a566e86558394eb6111`; trilha procedural `music.wav` do Drive `19dFe9lPreCmDh5Ubb29YN9AyF4O6yuxO`, SHA `4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24`.

**Achado grave P0:** os arquivos `music.wav` dos renders finais 002 e 004 são EXATAMENTE IDÊNTICOS, byte por byte, não somente parecidos. Testes com FFmpeg e correlação cruzada por janelas de 8 segundos a 2 kHz, tolerando ±2 s, apontam presença dessa mesma trilha em AMBOS os masters. Não alterar os vídeos já produzidos: **quarentena do hash da música** para todo episódio novo. A prioridade de não repetir trilha é mais forte do que declarações antigas.

**Conflito entre gerações:** manifestos `episodes/episode-001/manifest.json`, `...002` e `...004` documentam fontes MP3 de versões antigas, MAS os masters V7 posteriores acima apresentam trilhas procedurais. Não atribuir automaticamente uma música antiga ao master de geração nova por nome/ordinal. Os cinco registros legados continuam documentados com `actual_master_audio_verified=false` até reconciliação por artefato e versão. Os quatro masters reais estão agora **separadamente** em `episodes/audio-rendered-master-registry.json`, com hashes do contêiner, áudio extraído, proveniência GitHub, trilha original e confiança da análise. A correlação de forma de onda não prova isoladamente todos os instrumentos/efeitos.

**Proteções novas:** `production/audio_candidate_gate_v21.py` valida os bytes SHA do novo áudio contra todos os hashes/IDs de trilhas já declaradas e já existentes nos masters; licença item-específica, revisão acústica e SFX cooldown também condicionam elegibilidade. `production/audio_history_audit_v21.py` consome o novo registro real, exige quatro provas e acusa colisão confirmada; histórico de master, SFX e publicação não é falsamente promovido a `VERIFIED_COMPLETE`. Testes negativos e CI devem esperar quatro MP4s históricos verificados, uma colisão de trilha, gate ainda BLOCKED.

**Próximo passo:** implantar recibos de mix *desde a próxima renderização*, com hash de fontes, render e áudio resultante, e acionar revisão de composição antes da produção. Para SFX históricos sem evidência, manter desconhecido; nenhuma TTS, renderização, nova postagem, alteração de HUD/voz ou mudança do motor canônico ocorreu nesta auditoria.

**Limite hard-lock do novo guard:** mesmo com identidade SHA nova, licença e revisão acústica declaradas, `audio_candidate_gate_v21.py` verifica a decodificação real via FFprobe e **NUNCA** emite `ready_for_render=true` sozinho. O PASS só significa identidade exata não reutilizada no catálogo conhecido; autorização do áudio, fingerprint acústico e renderização composta continuam dependências independentes. Não aceitar campos informados pelo próprio candidato como prova suficiente de direitos.

### 2026-11-07 — Detecção acústica com arquivos alterados e recibos reais de mixagem

**Objetivo:** impedir a repetição de músicas mesmo com reencodificação, alteração de ganho e extração de trechos; gerar prova reexecutável de áudio e efeitos realmente presentes no mix, sem alterar o perfil sonoro canônico.

**Implementado em branch isolada:** `production/audio_acoustic_fingerprint_v21.py` usa FFmpeg Chromaprint algoritmo 1 em áudio real e compara sequências de fingerprints com tolerância temporal. Em teste local de uma fonte real, trecho de 17 segundos recortado a partir de 19s, volume 30%, AAC 96k: similaridade **0,99056** contra a origem e **0,74740** contra a fonte V7 001 distinta. Política: >=0,88 implica `LIKELY_REUSE`; >=0,78 implica revisão obrigatória; ausência de match NÃO é prova mundial de originalidade. Banco `episodes/audio-acoustic-fingerprints-v21.json` inicia com duas fontes V7 reais SHA-256 verificadas: 001 e a fonte idêntica de 002/004. Faltam as três assinaturas das fontes históricas MP3 para cobertura dos cinco registros conhecidos; não declarar catálogo completo. Detector conectado ao `production/audio_candidate_gate_v21.py`, falha fechado por falta de registro, sem liberar render/publicação.

**Recibo reexecutável:** `production/audio_mix_receipt_v21.py` recebe o comando FFmpeg do renderizador futuro sem alterar o filtergraph, confere hashes dos stems de narração, música e SFX; executa FFmpeg local em temp, registra hashes dos bytes e PCM 48 kHz. Auditoria repete a mixagem, exige PCM idêntico e, por *contrafactuais*, silencia um stem por vez para comprovar que ele contribuiu ao mix. `verify_master_binding()` compara a faixa mixada ao áudio do MP4 final, protegendo contra "recibo correto, master diferente". São testes com áudio sintético, nenhum vídeo do usuário foi alterado.

**Integração segura:** `production/render_v21_manual.py` oferece `validate_completed_audio_mix(...)` para futura execução de pós-voo. O motor V2.1 AINDA não dispõe de renderização ativa; o adapter não executa sozinho nem cria novo orquestrador. Não marcar produção, pós-voo ou publicação como concluídos porque um teste isolado passou. Identidades de Gemini/Charon, 1080x1920/60 fps, filtros, legendas, clips e publicação manual preservadas.

**Próximo passo único:** completar as três entradas faltantes de fingerprint a partir das fontes MP3 já recuperadas e tornar o pós-voo obrigatório quando existir uma renderização final V2.1 autorizada, validando som e vídeo efetivos.

### 2026-11-07 — Cobertura acústica das 5 fontes históricas conhecidas

O motor agora possui fingerprint FFmpeg/Chromaprint completo dos **cinco áudios históricos únicos** conhecidos — duas trilhas procedurais dos masters V7 e três MP3s recuperados e verificados pelo SHA-256 do Google Drive. Os novos MP3s: Mixkit Fright Night SHA `144384cf2bcda8070a0d11c8aa98c3ae547de861a553275788669b7cf6a57bcd` (797 quadros de fingerprint), Mixkit Echoes SHA `49842074dc06f05a40690c2b3af42bd32be76a5f6505a65cfe952b2fe1ccb5de` (1.806 quadros), DELOSound/Pixabay SHA `dd57de53251011da1cc72f22c81595e80c03151c46d4a43e71aa6baaf2bc98cc` (1.077 quadros). Assinaturas aprovadas anteriores dos masters 001 e 002/004 foram preservadas sem mudança.

**Testes reais em áudio original:** cada MP3 teve um trecho de 17s recortado em 17s, volume reduzido a 35% e recodificação AAC 96 kb/s; o detector recuperou o original com similaridade 0,95215 (Fright Night), 0,97721 (Echoes) e 0,96159 (DELOSound). Todos os dez pares distintos ficaram abaixo de 0,88. O par mais próximo, 0,77995, evidencia margem apertada em relação ao limiar de revisão 0,78, portanto manter revisão conservadora e nunca inferir liberação por similaridade baixa.

**Hard gate adicionado:** `catalog_coverage(repo_root)`, dentro de `production/audio_acoustic_fingerprint_v21.py`, cruza os SHA dos áudios do `audio-memory-registry.json` e `audio-rendered-master-registry.json` com os fingerprints do catálogo `episodes/audio-acoustic-fingerprints-v21.json`. `audio_candidate_gate_v21.py` bloqueia novas músicas se algum áudio histórico conhecido estiver faltando no catálogo, mesmo quando seu hash for diferente e não houver match perceptivo. Testes de regressão removem artificialmente registros e exigem o bloqueio.

**Evidência:** `reports/AUDIO_ACOUSTIC_FIVE_SOURCE_QA_20261107.json`. Este upgrade completa apenas a cobertura acústica dos cinco áudios atualmente registrados, **NÃO** o histórico global desconhecido de SFX, versões sem registro, licenciamento de terceiros ou incorporação automática do pós-voo ao futuro renderizador. A produção e publicação seguem manual/bloqueadas, sem TTS, render de episódio, alterações visuais ou de voz.

**Próximo passo único:** definir o ponto real do renderizador V2.1 autorizado que chamará obrigatoriamente o adaptador de mix e pós-voo e validar com um master completo sob política de produção aprovada; até lá, não liberar render/publicação.

### 2026-11-07 — Trava obrigatória de áudio na entrega final Drive (V2.1)

**Causa-raiz:** o V2.1 já tinha `verify_master_binding()` e `validate_completed_audio_mix()`, mas o adaptador `production/google_drive_delivery.py` ainda conseguia enviar um MP4 sem invocar os testes do áudio. Esse caminho de fuga foi fechado no próprio `deliver()`, **antes** de inicializar a rede ou credenciais Drive.

O módulo `production/final_delivery_v21.py` exige o vídeo master exato, política V2.1 de produção habilitada, permissão separada de entrega final, identidade Gemini/Charon, final H.264 1080×1920 60fps + AAC 48kHz 60–80s, gates independentes de histórico de áudio/direitos/verdade visual, recibo de mix com replay e participação real de narração/música/SFX e correspondência acústica ao master. Falha na ausência ou inconsistência de QUALQUER prova. Cobertura: MP4/MOV/MKV/WEBM/M4V/AVI entregues por `google_drive_delivery.deliver()`, mesmo aninhados em pastas. Backups sem vídeo permanecem fora desse escopo, preservados.

**Travas permanentes em vigor:** `production_enablement=false`, `final_drive_delivery_enablement=false`, Charon/Gemini e `publication_policy=manual_only`. `production/v21_singleton_guard.py` agora denuncia remoção da integração e habilitação silenciosa da entrega final. Não há rota ativa de renderização FINAL que produza novo áudio e recibo; o novo código é uma barreira real do adaptador existente, não execução automática de vídeo. A prévia isolada do GitHub Actions continua distinta de publicação/entrega final.

**Testes:** `tests/test_v21_final_delivery_gate.py` cobre produção desabilitada, falta de recibo, master trocado, direitos e histórico SFX bloqueados, vídeo escondido em pasta, bypass da API `deliver()` e caso positivo sintético isolado. CI principal garante, via monkeypatch, que a chamada Drive `service()` nunca é alcançada por um vídeo não autorizado. Não houve upload, TTS, render ou publicação nesta etapa. Evidências e limites em `docs/V21_FINAL_DRIVE_DELIVERY_AUDIO_LOCK.md`.

**Próximo passo único:** planejar e testar o renderizador V2.1 autorizado que chame o adaptador de mixagem aprovado e o pós-voo antes de entregar. Não reativar V7 nem habilitar produção sem aprovação específica, provas de direitos e histórico de áudio.

### 2026-11-07 — Renderizador FINAL V2.1 único (implementado em isolamento)

**Decisão arquitetural:** NÃO reconstruir as 16 cenas nem reabrir o V7. A nova rota `production/render_v21_final.py` usa a saída com SHA verificado do atual `render_v21_preview.py` como picture master congelado; valida report, Gemini/Charon, legenda na margem 650, logo/cores/continuidade e usa `ffmpeg -c:v copy` para preservar exatamente o fluxo H264. Substitui apenas a faixa sonora, mixando narração + música inédita + SFX pré-temporizados sob `production/audio_mix_receipt_v21.execute_with_receipt`; faz replay e testes contrafactuais de cada stem, pós-voo com `validate_completed_audio_mix`, comparação de hashes do stream de vídeo e do master AAC, e gera artefatos locais auditáveis.

**Travas:** CLI só acessa mídia depois de `validate_request(mode=final)`. A política vigente mantém `production_enablement=false`, `final_drive_delivery_enablement=false` e `publication_policy=manual_only`. `production/audio_mix_profile_v21.json` define volume musical e SFX como **proposta candidata não aprovada em escuta**, e exige futura passagem para `INDEPENDENT_AUDIO_QA_PASS` antes de renderização final real. O histórico de efeitos e colisão entre 002/004 continuam bloqueadores separados. Não gerar Gemini/Charon novamente ou alterar vídeos aprovados.

**Teste E2E:** `tests/test_v21_final_render.py` constrói vídeo/áudios sintéticos com FFmpeg, verifica mix real, replay, SFX presente, transcodificação AAC, master e identidade do bitstream visual, sem 1 crédito de TTS. O teste reduz a duração apenas no helper isolado; requisitos 1080×1920/60 fps/60–80s permanecem no contrato real de entrega. O singleton e CI verificam a rota única e bloqueio canônico. Evidência detalhada: `docs/V21_CANONICAL_FINAL_RENDER_ROUTE.md`.

**Próximo passo único:** concluir SFX/histórico e prova perceptiva de mixagem, rodar teste de render final real 1080×1920/60fps em ambiente privado sob autorização e só então habilitar produção manual, sem autopublicação.

