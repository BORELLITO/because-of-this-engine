# BECAUSE OF THIS — V2.1 Integration Control Center

- Implementation ID: IMPL-V21-20261105-01
- Audit ID: AUDIT-V21-20261105-01
- Specification: PROMPT_MESTRE_IMPLEMENTACAO_INTEGRACAO_BECAUSE_OF_THIS_V2_1_FINAL(2).txt
- Prompt SHA-256: 8f51c909363ead5c6d2964b733fcdf8909632dc68fef966802b1f8a56e2cb173
- Repository: BORELLITO/because-of-this-engine
- Base: main at d35d78cd4a92d12375f54076e3e21b56cbe25fad
- Candidate branch: integration/because-of-this-v2.1-20261105
- Draft PR: 67 (branch head is authoritative; commit history is tracked by GitHub)
- Status: PARTIAL / BLOCKED_FOR_PRODUCTION
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
| Global no-reuse | BLOCKED when incomplete | Registry is required and independent perceptual hashes are required |
| Thumbnail | BLOCKED when incomplete | Final manifest, delivery paths and strict file checks are required |
| Legacy workflows | ARCHIVED | Definitions retained under archive/v7/workflows/, outside .github/workflows |
| Drive | NOT RUN | No Drive write or media generation authorized |
| Work | UNKNOWN | No independent Work execution log |
| Edge TTS + captions preview | NATIVE_PROVIDER_TIMING_VALIDATED_GROUPED_BOUNDARIES | Audio run 41961294784 + frozen caption run 42027607644; 79.704 s; ChristopherNeural; 175 provider tokens; 2 grouped boundaries; caption artifact 13388300361 |
| Visual asset acquisition | BATCH_SEARCH_V2_READY | 15 Pexels fallback candidates plus 7 Mixkit candidates mapped to Episode 005 beats; seven are approved for manifest-only use and seven shots remain blocked. Intake/fingerprint are now manual-only and resolve URLs from the acquisition plan, eliminating duplicated defaults/allowlists and accidental downloads during PR updates |
| First new production | BLOCKED | Implementation stage does not authorize automatic production |

## Remaining blockers

- The 13 historical registry assets were fingerprinted from their verified Drive MP4s with the versioned video-phash-v1 algorithm; future assets must use the same catalog contract.
- Real thumbnail files and platform cover records are not yet available for a V2.1 episode.
- Renderer accepts provider-native grouped boundaries as synchronized units; no provider interval is subdivided synthetically. Final render remains blocked only by missing approved assets, thumbnail and the remaining release gates.
- Offline contracts for TTS, audio, captions, render and Drive are integrated; the canonical entrypoint verifies the real adapter files and symbols. Real Edge TTS audio and provider-native caption timing are generated and validated. Two provider boundary groups remain intentionally unsplit; the Whisper acoustic audit is retained as diagnostic and is not allowed to replace provider timing. The approved artifact is frozen; the synthesis workflow is manual-only because independent runs can produce different audio hashes. Visual asset acquisition is partially executed: seven Mixkit candidates have technical intake artifacts and explicit manifest-only approval; the mechanism is assigned to S10 only, the satellite antenna to S02 only, the young-engineer reconstruction to S03 only and the worker control-panel reconstruction to S04 only. The casual computer candidate for S03 was rejected for weak semantic fit, and Mixkit 5572 was rejected before intake because the free download is restricted to personal use. The S03 and S04 candidates are explicitly representational reconstructions, never literal Petrov archival evidence. The partial scene manifest still blocks repeated-source reuse within the episode, with seven shots unresolved. Thumbnail, render, Drive write and publication remain unexecuted. Pexels direct media download was blocked by the browser; Mixkit remains the preferred acquisition route, with license-page verification and per-file QA mandatory. The GitHub intake workflow resolves browser-verified media URLs from the plan, records SHA-256/metadata and emits QA frames without promotion. Search-v2 requires six page-verified candidates per unresolved shot, shortlists two, then runs one manual intake batch followed by one fingerprint audit for the same explicit candidate IDs. Batch inputs are comma- or newline-separated plan IDs, capped at 12 per dispatch; IDs, Mixkit domains, license, file size and duration are revalidated; there are no implicit full-plan scans.
- Promotion to main still requires explicit approval and post-merge audit.

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
