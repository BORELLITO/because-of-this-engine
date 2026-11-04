# BECAUSE OF THIS — CENTRO DE CONTROLE (AUDITORIA V1.1)

**Audit ID:** BOT-AUDIT-20261104-V11-01  
**Atualizado:** 2026-11-04 (America/Sao_Paulo)  
**Status geral:** BLOCKED PARA NOVA PRODUÇÃO; auditoria PARTIAL  
**Risco:** ALTO (P0/P1 ainda pendentes)  
**Modo:** READ_ONLY em mídia, Drive, produção e branch main; implementação apenas nesta branch isolada.  
**Código canônico confirmado na main:** `d35d78cd4a92d12375f54076e3e21b56cbe25fad` (V7.3.1).  
**Candidata existente à parte:** `v7.4-editorial-story-engine` em `877e2e72073c77cd0f68d2bc277b0ef9ffbdaad4`.  
**Branch de auditoria:** `audit/because-of-this-v1-1-20261104` — [PR #65](https://github.com/BORELLITO/because-of-this-engine/pull/65) (DRAFT; não fazer merge automaticamente).  
**Histórico protegido:** ONE EXTRA MINUTE / *The Tape That Added One More Minute*. Não modificar, renderizar, republicar, duplicar, nem reutilizar mídias/derivações.  
**Provedor ativo comprovado na main:** `gemini_tts` (Charon), **NÃO** Google Cloud Text-to-Speech.  
**Meta ainda NÃO ativada:** `google_cloud_tts`, voz `en-US-Chirp3-HD-Charon`; configuração de duração 55–65 s preferencial (50–70 flexível), sujeita a aprovação e testes.

## Confirmado funcionando

- Acesso ao repositório e às pastas de produção/entrega no Google Drive.
- CI existente da V7.3.1 e render final histórico do episódio 004 na branch V7.4.
- MASTER histórico do One Extra Minute disponível e inspecionado de maneira não destrutiva.
- Verificador V1.1 READ_ONLY, sete testes e workflow de GitHub Actions executados com sucesso: [run 41869209468](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41869209468).
- Política de publicação manual declarada no código atual.

## Riscos e bloqueios essenciais

- **P0 — PROVIDER_DRIFT:** main/manifestos usam Gemini; prompt V1.1 deseja Google Cloud TTS. Não efetuar migração silenciosa.
- **P0 — MAIN_WORKFLOW_DRIFT:** workflow `episode-004-final-release.yml` da main referencia manifest e módulos somente presentes na branch V7.4.
- **P0 — NO_REUSE_UNVERIFIED:** proteção global contra mídia repetida ainda não reconciliada entre todas branches, manifests e Drive.
- **P0 — RIGHTS_UNVERIFIED:** licenças de todos os arquivos ainda não verificadas independentemente.
- **P1 — VISUAL_NARRATIVE_DRIFT:** auditoria de frames do One Extra identificou cenas genericamente relacionadas ou incompatíveis com a narração, apesar de JSON de QA automático PASS.
- **P1 — CAPTION_UI_UNVERIFIED:** margens ASS não substituem screenshots da interface TikTok/Shorts.
- **P1 — WORK_UNVERIFIED:** esta auditoria usou conectores e GitHub Actions; não houve inspeção da sessão real Work.
- **P1 — PIPELINE_STATE:** transições de estado permitem avanços que precisam de gates mais rigorosos.
- **P2 — DOCUMENTATION_DRIFT:** README_PT e .env.example descrevem Piper V7.1, enquanto main executa Gemini V7.3.1.

## 17 blocos de supervisão

| Bloco | Status | Evidência / pendência |
|---|---|---|
| Arquitetura | PARTIAL | Componentes presentes; conectividade ponta a ponta não totalmente exercitada |
| Pipeline | PARTIAL | Renders reais; transições exigem revisão |
| Creative engine | FAIL | Protagonista/gancho/consequência fracos no histórico |
| Visual engine | FAIL | Incongruência narrativa apesar de aprovação automática |
| Cloud TTS | BLOCKED | Gemini é o adaptador ativo |
| Áudio | PARTIAL | FFprobe e medição integradas; faltam stems e teste de escuta |
| Legendas | PARTIAL | Relatório ASS disponível; UI real não validada |
| Embalagem | UNKNOWN | Sem métricas e interface de canal |
| Render | PARTIAL | Histórico validado, novo fluxo não |
| Direitos | PARTIAL | Declarações em manifestos, comprovação abrangente pendente |
| Drive | PARTIAL | Pastas e artefatos inventariados; reconciliação pendente |
| GitHub | PARTIAL | Acesso PASS; main e V7.4 divergentes |
| Work | UNKNOWN | Ausência de log/execução observável da sessão |
| Gates | FAIL | Aceitam material visual historicamente fraco |
| Testes | PARTIAL | 7/7 novos PASS + CI antigo PASS; cobertura novo motor insuficiente |
| Rollback | PARTIAL | Branches existentes, exercício de recuperação pendente |
| Métricas | UNKNOWN | Sem dados confiáveis de retenção, distribuição ou custos |

## Evidências e links

- [PR de auditoria isolada](https://github.com/BORELLITO/because-of-this-engine/pull/65)
- [CI de auditoria V1.1](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41869209468)
- [CI de regressão anterior](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41869209400)
- [V7.4 render final real, episódio 004](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41376351220)
- [Arquivo histórico protegido (Drive)](https://drive.google.com/file/d/1rfSdXGFr8xsXQNWU4AtqSUt7TIf9YGVy/view)

## Critério de prontidão

NÃO emitir READY enquanto houver P0/P1 sem evidência E3–E5, direitos e histórico global não aprovados, Work não testado ou prévia da nova direção não aprovada. Manter publicação manual. Nenhum novo roteiro/mídia/render será iniciado antes da autorização prevista pelo prompt mestre.

## Atualização técnica da auditoria — 04/11/2026

**Correções reais implementadas em isolamento (PR #66, sobre V7.4):**

1. G3 bloqueia ausência de relatórios reais de visual/story QA e alinhamento da narração; relatório de draft não vale para o master final.
2. G6 reconhece o status real `CAPTION_QA_PASS` em vez de procurar `PASS` incorretamente.
3. G4 valida nomes reais de campos da V7.4 para TTS, sem alterar a voz.
4. G2 exige direitos aprovados para releases finais.
5. Corrigida a divergência entre a impressão digital computada pela configuração V7.4 (`52d6202bea79...`) e o valor da política V7.4 (`c9f6c107...`). O manifesto original de episódio 004 já usava o fingerprint computado.
6. Corrigido o singleton guard, que exigia um nome literal mesmo quando o orquestrador ligava o perfil por constante canônica.
7. Adicionado um contrato offline para uma futura integração Google Cloud TTS Chirp3 HD Charon: **não conectado, não autenticado, não ativado, sem API/SSML/voz gerada**.

**Evidências de regressão:**

- [PR #66 — Hardening V7.4](https://github.com/BORELLITO/because-of-this-engine/pull/66), **draft**.
- [Run de auditoria em V7.4 — 17 testes novos + 9 testes originais PASS](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41872148850).
- [CI de reuso existente — PASS](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41872148988).
- `main` continua no commit `d35d78cd4a92d12375f54076e3e21b56cbe25fad` sem merge.

**O que NÃO foi demonstrado:** render de nova história; teste real faturável do Cloud TTS; licenças independentes de todo histórico; comparação perceptual entre mídia de todos os branches/Drive; análise visual humana de cada clipe futuro; UI safe zones do TikTok/Shorts; execução em sessão real do Work; validação ponta a ponta com história nova. Por isso status geral permanece **BLOCKED PARA NOVA PRODUÇÃO / PARTIAL NA AUDITORIA**.

---
## Decisão do usuário — continuidade da voz aprovada (04/11/2026)

**VOCAL LOCK: preservar Gemini TTS / voz Charon**, a mesma rota aprovada no Because Of This. Não trocar para Google Cloud TTS Chirp3 HD Charon, pois o mesmo nome não garante a mesma identidade vocal. Preservar parâmetros e referência sonora do motor histórico; nenhum teste ou gasto Cloud TTS é necessário. O módulo `experimental/v11/chirp3_cloud_tts_contract.py` permanece não ativado e sem rota para produção; não o promover. A adaptação TTS não é pré-requisito para nova história. Próxima etapa: revalidar segurança, proveniência e geração da nova história mantendo o Gemini Charon e aprovação humana dos resultados.

## Execução incremental — segurança da memória de clipes e continuidade vocal (04/11/2026)

**PR #66 sobre V7.4 — duas vulnerabilidades confirmadas e corrigidas:**

- Fonte já usada em um **rascunho sem manifesto final** agora entra no histórico da verificação. Antes, `_all_manifests()` lia apenas `manifest.json`.
- `same_story_id` deixou de poder disfarçar outro `video_id` para dispensar a checagem global. Rascunho e final futuros devem usar o mesmo ID canônico. Rascunhos históricos não foram reescritos.
- O gate G3 agora executa uma **nova consulta ao catálogo de fontes a cada validação**, independentemente de existir relatório JSON antigo marcado PASS. Bloqueios reais não podem ser ocultados por cache obsoleto.
- A execução offline passou ao cruzar os **12 manifestos locais presentes no ramo e 13 registros de mídia do registry** para o episódio 004 usado como referência, com **zero colisões novas para aquele candidato**. Isso não equivale a pesquisar todas as branches do GitHub e todo o acervo no Drive.
- Preservado exclusivamente `gemini_tts` / `Charon`: o experimento Cloud TTS, criado somente pela auditoria e nunca ligado ao motor, foi **retirado da PR #66**. As configurações reais da voz não foram alteradas.
- O verificador da **PR #65** agora reconhece Gemini TTS Charon como voz aprovada e **bloqueia trocas para outra voz ou provedor**. Removeu-se o falso P0 de obrigação de migração para Cloud.

**Evidências da revisão pós-correção:**

- [PR #66 V7.4 (rascunho)](https://github.com/BORELLITO/because-of-this-engine/pull/66)
- [CI de hardening da V7.4 (21 novos testes + 9 testes existentes, sucesso)](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41891080369)
- [CI de reuso da V7.4 (sucesso)](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41891080161)
- [PR #65 (rascunho)](https://github.com/BORELLITO/because-of-this-engine/pull/65)
- [CI do verificador V1.1 (9 testes, sucesso)](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41891050953)
- [Regressão do motor principal V7.3.1 (sucesso)](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41891051065)

**Limitações e bloqueios ainda reais:**

1. **P0**: catálogo de ativos ainda não reconciliado com *todas* as branches e arquivos antigos do Drive; os 13 registros do registry não cobrem integralmente o histórico de 12 manifestos examinados. Existem sobreposições entre identificadores de episódios históricos; não modificar esses vídeos, mas impedir repetição futura.
2. **P0**: validade jurídica das licenças e as evidências pixel-a-pixel não foram verificadas de maneira independente; metadados `rights_status=APPROVED` isoladamente não bastam.
3. **P1**: a segurança visual de legendas sobre a interface real do TikTok/Shorts não foi testada em aparelho; tempos por palavra dependem de amostra real do áudio final.
4. **P1**: etapa do Work/navegação visual não executada nesta sessão; ausência de prova de ponta a ponta de nova produção, portanto **não promover READY**.

**Integridade e reversibilidade:** `main` não recebeu merge, os PRs permanecem draft, nenhum TTS foi consumido, nenhum vídeo antigo foi modificado, nenhum render/publicação nova foi realizado. Testes de CI são evidência de código, não de licença, áudio ou experiência de publicação.

---
## Resultado quantitativo da auditoria do catálogo — 04/11/2026

A PR #66 ganhou `audits/inventory_audit_v11.py`, sem qualquer consulta externa ou modificação de mídias. Os números foram gerados pelo próprio workflow no GitHub Actions:

| Indicador | Evidência |
|---|---:|
| Manifests locais analisados | 12 |
| Fontes únicas por chave de origem | 79 |
| Fontes ainda não representadas no registry central | **66** |
| Destas: vistas em manifesto com `FINAL_APPROVED` | **32** |
| Destas: apenas `ARCHIVED_HISTORICAL`, sem final atual | **12** |
| Destas: apenas rascunho/outro estado | **22** |
| Entradas atuais no registry | 13 |
| Entradas atuais no registry sem fingerprint visual | 13 |
| Chaves compartilhadas entre distintos `video_id` | 19 |
| Dessas com alias explícito de rascunho/final da mesma história | 8 |
| Demais sobreposições entre IDs, a revisar historicamente | 11 |

**Leitura técnica:** as 66 fontes não estão invisíveis para o gate local atualizado: ele lê também os 12 manifestos. Porém, **não estão consolidadas no registro persistente** para sobreviver a reorganizações, exclusões de branches ou futuras migrações. Não adicionar todas cegamente: 22 são somente drafts ou estados não finais e a aposentadoria automática gastaria material potencialmente reutilizável sem prova de uso público. Separar `CONSUMED_FINAL`, `ARCHIVED_CONSUMED` e `RESERVED_DRAFT` exige evidência de uso real e de direitos, não só metadados. O verificador permanece `LOCAL_METADATA_COVERAGE_PARTIAL`.

**CI de ponta a ponta desta auditoria offline:** [GitHub Actions #41892197120](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41892197120), **26 testes novos + 9 testes existentes PASS**; [CI de reutilização #41892196873](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41892196873), PASS. O CI de auditoria em `main` [#41891610891](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41891610891) também passou no ramo isolado da PR #65.

**Segurança:** comparação entre V7.4 e PR #66 confirma que NENHUM arquivo dentro de `episodes/` foi modificado; só módulos de validação, testes e auditorias. `main` mantém SHA `d35d78cd4a92d12375f54076e3e21b56cbe25fad`. One Extra Minute preservado.

---
## Reconciliação GitHub + Drive — 04/11/2026 | PR #66

**Execução comprovada e não destrutiva:**
- Auditor `audits/branch_history_audit_v11.py` percorreu **74 branches remotas**, **251 ocorrências** e **47 versões distintas** de manifestos. Todos os blobs escaneados puderam ser interpretados.
- A primeira contagem de 100 fontes tinha **5 aliases equivalentes de Pexels**. Após correção de identidade (inclusive IDs Drive sensíveis a caixa), o histórico registra **95 fontes distintas**: 79 presentes na árvore V7.4 atual + 16 adicionais encontrados somente em branches antigos.
- Os **16** adicionais foram preservados em `audits/git_history_review_queue_v11.json` como `PENDING_REVIEW_NOT_RETIRED`, sem proibição permanente nem prova de consumo. O guard de reutilização bloqueia um novo episódio que coincida com eles, sinalizando `HISTORY_REVIEW_REQUIRED`, até revisão humana específica.
- **Google Drive confirmou presença de 63 IDs de vídeos distintos:** 32 de manifestos FINAL_APPROVED; 13 dos dois episódios piloto arquivados; 12 do episódio arquivado 003; e 6 antigos vídeos somente de prévia. Os IDs do arquivado 004 coincidem com os 12 já contados nos finais e não foram duplicados. Nenhum download, alteração de vídeo ou verificação byte a byte foi realizado.
- A análise das páginas originais registrou **cinco evidências por item** (2 Mixkit Stock Video Free; 1 USGS Public Domain; 2 Wikimedia Commons Public Domain) em `audits/RIGHTS_AND_PROVENANCE_V11.md`. Licenças gerais Pexels/Pixabay/Mixkit foram revisadas, incluindo cautelas de imagem de pessoas, marcas e conteúdo de terror. As páginas não certificam a identidade dos arquivos derivados.
- O registro central original continua com **66 das 79 fontes atuais ainda sem entrada** (32 presentes em `FINAL_APPROVED`, 12 somente em arquivo histórico, 22 somente em drafts/outros estados); **13 registros sem fingerprint visual**. O novo gate lê a árvore de manifestos e a fila histórica, mas o registro persistente completo ainda não foi homologado.

**Evidências e testes:** 
- [PR #66 — hardening em V7.4 (draft)](https://github.com/BORELLITO/because-of-this-engine/pull/66).
- [Git history scanner: 74 branches, 95 fontes após normalização](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41899774117).
- [CI V7.4 — 39 testes de auditoria + 9 existentes, todos PASS](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41900806957).
- [CI de não-repetição existente — 6 testes PASS](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41900806908).
- [Evidência de páginas de licença](https://github.com/BORELLITO/because-of-this-engine/blob/audit/v74-v11-hardening-20261104/audits/RIGHTS_AND_PROVENANCE_V11.md).

**Bloqueios P0/P1 restantes:** verificação real de checksums e quadros de derivados no Drive; verificação individualizada de direitos/autorizações para mídias escolhidas futuramente (inclusive terceiros identificáveis); reconciliação final de áudio e trilhas históricas; preview real de legendas na interface de TikTok e Shorts; integração ponta a ponta no Work e aprovação humana da nova direção. **Não declarar o motor READY.**

**Não executado:** nenhum TTS, nenhum render novo, nenhuma postagem, nenhum merge, nenhum arquivo `episodes/` modificado, nenhum vídeo histórico alterado. Gemini TTS Charon mantém a configuração originalmente aprovada.

---
## E4: integridade real de arquivos e direitos de origem — 04/11/2026

**Resultado técnico real:** 12 arquivos `MP4` históricos do Episode 004 foram baixados exclusivamente para auditoria read-only pelo conector Google Drive. Comparados diretamente com o manifesto de produção V7.4:
- **12/12 SHA-256 idênticos** ao valor registrado no manifesto;
- **12/12 tamanhos em bytes idênticos**;
- **12/12 streams de vídeo lidos** por `ffprobe`;
- **36/36 quadros extraídos** por `ffmpeg` (25%, 50%, 75%);
- Originais intactos, sem qualquer alteração nas pastas de episódios, render, TTS, música ou publicação.

**Achado visual crítico:** S01 e S05 utilizam a **mesma fotografia histórica de Lituya Bay** em derivações diferentes (S05 inclui setas); correlação dos quadros centrais 0,972. Hashes de arquivos distintos **não** detectavam essa reutilização de imagem. S02/S10 tiveram alarme por dHash, mas inspeção visual verificou cenas diferentes (correlação 0,8769): não bloquear apenas por dHash. S04 página Pexels refere ondulações, sem prova suficiente nos quadros de queda da pedra.

**Correção isolada na PR #66:** novo `audits/e4_media_integrity_v11.py` verifica bytes, tamanho, metadados e quadros reais de candidatos, sem tocar nos arquivos. Semelhança forte ou incerta gera `E4_TECHNICAL_PASS_WITH_REVIEW` **com exit code 2** (bloqueio até revisão humana), não `PASS` automático. Checksum/tamanho incorreto ou arquivo ausente causa `BLOCKED`. O script jamais aprova direitos comerciais ou um novo episódio sozinho. Foram introduzidos testes com vídeos sintéticos para evitar depender de créditos ou material já consumido.

**Evidência técnica e documentação:** 
- [Relatório E4 no GitHub](https://github.com/BORELLITO/because-of-this-engine/blob/audit/v74-v11-hardening-20261104/audits/E4_REAL_MEDIA_INTEGRITY_V11.md)
- [Suíte V7.4 após instalação FFmpeg no runner](https://github.com/BORELLITO/because-of-this-engine/actions/runs/41915419803) — 46 testes novos e 9 testes existentes; última execução deverá manter o mesmo perfil.
- Páginas específicas de origem e termos consultados: 5 clips Mixkit Free, 3 Pexels Free, 1 Pixabay sob licença de conteúdo e 3 itens USGS/Wikimedia em domínio público nos EUA. **Ainda não comprovado**: autorização integral dos derivados para novos episódios, direitos de terceiros, música, segurança em interfaces reais e seleção editorial da próxima história.

**Escopo e limites:** E4 técnico concluído **somente para amostra histórica Episode 004** como ensaio de verificação. Não foi certificada a totalidade do acervo nem selecionadas mídias de episódio novo. One Extra Minute não foi editado, refiltrado, renarrado nem recuperado para reuso. `main` permanece intocada; voz Gemini TTS Charon preservada.

**Estado:** AUDITORIA PARCIAL / PRIMEIRA PRODUÇÃO NOVA BLOQUEADA.

---
## ÚNICO PRÓXIMO PASSO

**Auditar e fechar o contrato de trilhas musicais, efeitos sonoros e a memória global de áudio na V7.4, sem gerar nem trocar músicas existentes.** Confirmar proveniência, licenças, integridade e identidade sem repetição; bloquear ambiguidade no motor experimental. Depois revisar segurança de legenda e realizar aprovação editorial da primeira nova história. Não gerar TTS, render, mesclar branches, alterar One Extra Minute ou publicar.

**Ação do usuário agora:** nenhuma. O avanço ocorrerá apenas após evidências e gates, não por autodeclaração.
