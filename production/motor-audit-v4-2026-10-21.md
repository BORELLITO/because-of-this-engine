# BECAUSE OF THIS — Auditoria Motor Audit v3.0

Data da auditoria: 2026-10-21  
Escopo: somente o motor independente **BECAUSE OF THIS** e o episódio Mars Climate Orbiter 001.  
Protocolo aplicado: `REVISAO MOTOR.txt` — Motor Audit v3.0.  
Estado desta entrega: **ANALYZED (snapshot pré-upgrade)**. As correções posteriores estão registradas em `motor-upgrade-review-v2.md`. Nenhuma alteração foi feita nos motores protegidos.

> Regra de evidência: `DECLARED` é uma afirmação/documentação; `IMPLEMENTED` é código ou configuração existente; `VERIFIED` é comportamento observado em teste/execução. Quando não há prova, o estado é `UNKNOWN` ou `PARTIALLY_VERIFIED`.

## 1. EXECUTIVE VERDICT

**Classificação atual: OPERATIONAL WITH BLOCKERS para o episódio; OPERATIONAL BUT FRAGILE como motor repetível.**

Há prova de que a bancada renderiza um MP4 real: 1080×1920, 30 fps, H.264/AAC, 58,366667 s, áudio 24 kHz mono, hash conferido, quatro testes unitários verdes e pipeline CI verde no repositório independente. Isso comprova produção técnica de uma versão.

Há, porém, um bloqueador de correção: o manifest aponta `examples/mars_climate_orbiter.txt` como roteiro e registra seu hash, mas a ASS e a especificação de edição contêm outro texto, substancialmente mais longo. O validator somente verifica existência/hash do TXT, presença de eventos e duração; não verifica identidade semântica entre roteiro, áudio e captions. Portanto `TECH_VALIDATED` não significa que o conteúdo exibido é o conteúdo aprovado.

O motor não está pronto para publicação nem para escala. O próximo passo correto é corrigir a fonte canônica do episódio e endurecer o gate de sincronização antes de qualquer melhoria estética, publicação ou automação em lote.

## 2. REAL OBJECTIVE

Produzir repetidamente Shorts faceless em inglês, com suspense documental sobre fatos científicos, para o canal BECAUSE OF THIS, usando uma operação gratuita/prioritariamente gratuita, voz consistente, visual editorial claramente ilustrativo, captions sincronizadas, rastreabilidade factual, aprovação humana e isolamento absoluto dos demais motores.

O resultado de sucesso não é “um MP4 que o FFmpeg exportou”. É um episódio factual, compreensível em celular, sincronizado, versionado, diagnosticável, reproduzível o bastante para manutenção e bloqueado quando qualquer requisito crítico falhar.

## 3. SCOPE / OUT OF SCOPE

**Dentro:** roteiro e claims; áudio Charon; frames procedurais; motion FFmpeg; captions ASS; mix; export; validação; manifest; testes; documentação; repositório privado independente.

**Fora:** Capta Pronto, Corte Fino, Publisher, Creator e qualquer outro motor/repositório; publicação automática; analytics; descoberta automática de temas; fila; schedule; ASR word-level; banco externo; escala massiva.

O repositório independente verificado é `BORELLITO/because-of-this-engine`, privado, com workflow de validação concluído com sucesso. Não há evidência nesta auditoria de alteração nos repositórios protegidos.

## 4. AS-IS ARCHITECTURE

```text
TXT manual + claims JSON + especificação editorial
        ↓
WAV Charon coletado manualmente no AI Studio
        ↓
frames PIL procedurais → segmentos FFmpeg com motion
        ↓
ASS manual com frases e timecodes
        ↓
bed procedural + mix voz-primeiro + captions queimadas
        ↓
MP4 final → ffprobe/volumedetect/validator
        ↓
revisão humana de celular (ainda pendente)
```

As etapas de análise, filtros, scoring, ranking e decisão de pauta são editoriais/manuais; não existe motor runtime de ranking. Monitoring, resultado, feedback e learning ainda não existem como ciclo operacional.

## 5. SYSTEM INVENTORY

| Componente | Responsabilidade | Estado | Evidência | Falha principal |
|---|---|---|---|---|
| `narrate.py` | TTS Gemini API, WAV e sidecar | IMPLEMENTED / UNIT TESTED | 4/4 testes | chamada real do CLI não foi reproduzida nesta auditoria; sem retry classificado |
| AI Studio / Charon | áudio usado no episódio | VERIFIED LOCAL | WAV 58,36 s, hash | modelo exato e parâmetros da coleta manual desconhecidos |
| `build_mars_visual_draft.py` | seis frames procedurais | IMPLEMENTED / EXECUTED | PNGs locais | config hardcoded; concat inicial redundante |
| `build_mars_visual_motion.py` | motion silencioso | IMPLEMENTED / EXECUTED | seis segmentos + MP4 | não lê o manifest; não valida assets antes de executar |
| `render_mars_final.py` | bed, mix, captions e export | IMPLEMENTED / VERIFIED | MP4 real | caminhos hardcoded, `-y`, sem output temporário/lock |
| `validate_episode.py` | gate técnico | IMPLEMENTED / VERIFIED | `TECH_VALIDATED` | falso positivo semântico; gates de mix/editorial não são exigidos |
| `run_episode.py` | orquestra render/validação | IMPLEMENTED / PARTIALLY VERIFIED | execução local | sem estado FAILED/RETRYING, run_id ou lock |
| episode manifest | intenção de SSOT | IMPLEMENTED / PARTIAL | JSON presente | visual/captions/mix não são totalmente consumidos/checados |
| claims register | claims e fontes | IMPLEMENTED / PARTIAL | 4 claims VERIFIED | não cobre todas as frases do roteiro/captions |
| ASS captions | texto/timing | RENDERED / PARTIAL | 14 eventos | texto não coincide com TXT canônico; sem ASR |
| GitHub Actions | compile, unit, JSON | IMPLEMENTED / VERIFIED | run CI success | não executa FFmpeg E2E, media QA ou segurança de paths |
| docs Markdown | direção e operação | IMPLEMENTED / DRIFT | arquivos presentes | alguns estados históricos continuam descritos como atuais |
| publicação/analytics | delivery e aprendizado | PROPOSED / ABSENT | nenhuma integração | não há feedback loop real |

## 6. CURRENT SYSTEM SPEC

| Regra | Valor válido hoje | Estado | Precedência |
|---|---|---|---|
| isolamento | nunca modificar os motores protegidos | HARD LOCK / IMPLEMENTED POR ESCOPO | 1 |
| custo | free-first; não contornar quota habilitando cobrança sem decisão explícita | DECLARED | 2 |
| canal | BECAUSE OF THIS, faceless, inglês | IMPLEMENTED neste episódio | 3 |
| voz | Charon para este episódio | VERIFIED no WAV | 3 |
| visual | reconstrução editorial, sem fingir telemetria/arquivo NASA | IMPLEMENTED no visual/spec | 3 |
| formato | vertical 1080×1920, 30 fps | VERIFIED no MP4 | 3 |
| aprovação | `TECH_VALIDATED` não é `APPROVED`; revisão humana antes de publicar | PARTIALLY IMPLEMENTED | 2 |
| captions | inglês, frases curtas, safe zone, branco/âmbar | PARTIALLY VERIFIED | 3 |
| CTA/bumper | não adicionar ao episódio | IMPLEMENTED | 3 |
| claims | cada afirmação material precisa de fonte | PARTIAL: register existe, cobertura incompleta | 2 |
| duração | autoridade é o WAV real deste episódio | IMPLEMENTED no render | 3 |

O texto canônico, a transcrição narrada e a ASS precisam ser unificados. Hoje essa regra é ambígua e o sistema não a impõe.

## 7. RULE PRECEDENCE

1. Segurança e isolamento dos projetos.
2. Hard locks explicitamente aprovados.
3. Regra específica do episódio.
4. Instrução mais recente e explícita.
5. Regra geral do canal.
6. Default do código.

Conflitos atuais: `examples/mars_climate_orbiter.txt` versus ASS/edit-spec; seis cenas no código/manifest versus sete na edit-spec; `mix_valid:false` enquanto a documentação descreve mix final; documentos históricos que ainda dizem que o repositório não existia. O conflito de texto é P0; os demais são P1/P2.

## 8. HARD LOCKS

**Não negociáveis:** isolamento dos outros motores; não expor API keys; não publicar sem aprovação humana vinculada à versão; não transformar visual ilustrativo em evidência; não inventar fatos; falha em gate crítico interrompe o release; MP4 aprovado não deve ser sobrescrito.

**Adaptáveis:** número de cenas; duração por roteiro; intensidade de motion; assets premium; bed; word-level ASR.

**Experimentais:** automação de coleta AI Studio, troca de modelo, publicação e analytics.

Qualquer ajuste de hard lock exige autorização explícita e regression test.

## 9. DECLARED vs IMPLEMENTED vs VERIFIED

| Item | Classificação |
|---|---|
| repositório independente privado | IMPLEMENTED / VERIFIED |
| CI compile/unit/JSON | IMPLEMENTED / VERIFIED |
| isolamento por intenção e escopo | IMPLEMENTED / PARTIALLY VERIFIED; não há guard automatizado completo |
| geração TTS via API | IMPLEMENTED / UNIT TESTED; execução real do CLI não verificada aqui |
| áudio Charon local | VERIFIED |
| render MP4 técnico | VERIFIED |
| claims com algumas fontes | IMPLEMENTED / PARTIALLY VERIFIED |
| sincronização semântica TXT→áudio→captions | UNKNOWN e provavelmente incorreta; P0 |
| loudness integrado e inteligibilidade em celular | PARTIALLY VERIFIED; celular pendente |
| aprovação humana por hash | DECLARED / NÃO IMPLEMENTED como registro verificável |
| retry/recovery/lock/queue | PROPOSED / ABSENT |
| publicação e analytics | PROPOSED / ABSENT |
| aprendizado de resultados | PROPOSED / ABSENT |

## 10. REQUIREMENTS TRACEABILITY MATRIX

| Requisito | Implementação | Teste/evidência | Observabilidade | Status |
|---|---|---|---|---|
| não tocar outros motores | escopo/repo separado | inspeção do pacote | ausência de paths externos | PARTIAL |
| roteiro versionado | TXT + SHA-256 no manifest | hash passa | `script_sha256` | PARTIAL: texto usado não é o mesmo da ASS |
| factualidade | claims JSON | 4/4 claims marcados VERIFIED | claims count | PARTIAL |
| voz Charon | WAV + sidecar | wave/hash | duration/hash | VERIFIED técnico |
| captions sincronizadas | ASS | bounds apenas | eventos/duração | FAIL/P0 sem identidade textual |
| vertical e codecs | FFmpeg | ffprobe | stream metadata | VERIFIED |
| mix voz-primeiro | filtro FFmpeg | mean volume; LUFS observado fora do gate | falta LUFS no relatório | PARTIAL |
| não sobrescrever aprovado | guard no orchestrator | caminho de aprovação não coberto | status | PARTIAL |
| aprovação humana | processo manual | sem registro/hash de revisão | ausência de log | GAP |
| feedback | nenhum componente | nenhum | nenhum | ABSENT |

## 11. WHAT IS EXCELLENT — DO NOT TOUCH

Preservar: isolamento; escolha de Charon já aprovada para este episódio; tom factual/sombrio contido; inclusão de contexto sistêmico além do erro de unidades; reconstrução editorial sem falsa telemetria; formato vertical; voz acima do bed; ausência de CTA/bumper; escrita atômica do TTS; proteção contra sobrescrita no CLI; validator fail-closed para vários checks mecânicos; documentação que explicita limitações.

Não trocar a voz nem adicionar efeitos apenas para “parecer upgrade”. O problema atual é de contrato e rastreabilidade, não de quantidade de recursos.

## 12. P0 FINDINGS

### P0-01 — Fonte de roteiro divergente do texto narrado/captions

**Evidência:** o manifest e o sidecar apontam SHA-256 `87e0c2...7e7fbe` para `examples/mars_climate_orbiter.txt` (121 palavras normalizadas); a ASS contém outro texto, aproximadamente 186 palavras normalizadas, incluindo “nine months”, “different units”, “September 23, 1999”, “burned up” e “whole mission”, enquanto o TXT contém “170 kilometers”, “correction maneuver number five” e outros trechos ausentes da ASS.

**Impacto:** o sistema pode narrar uma versão, exibir outra e declarar TECH_VALIDATED. Isso quebra o objetivo factual e o contrato de sincronização.

**Ação:** escolher uma única transcrição aprovada; salvar exatamente essa transcrição como SSOT; regenerar WAV/captions ou atualizar hash/proveniência; adicionar teste de cobertura textual e, idealmente, ASR.

### P0-02 — Gate `SYNC_VALID` não comprova sincronização

O validator verifica apenas início/fim dos eventos ASS contra duração do WAV. Não compara palavras com roteiro, não detecta legenda de fala errada e não usa timestamps de áudio. `gates.sync_valid:true` no manifest é, portanto, uma afirmação mais forte do que a evidência disponível.

### P0-03 — Claims não cobrem o texto efetivo

Os quatro claims são úteis, mas não rastreiam todas as frases da versão longa nem todos os detalhes da versão curta. Uma lista de claims parcial não pode provar factualidade do output inteiro.

## 13. P1 FINDINGS

1. `validate_episode.py` rejeita qualquer manifest `APPROVED` antes mesmo de considerar um approval hash; o caminho positivo de aprovação está quebrado.
2. Manifest é SSOT apenas nominal: render usa caminhos hardcoded e validator não valida `visual.source_motion`, hash de captions, hash do visual ou hash do bed.
3. `run_episode.py` não gera estados persistentes `FAILED`, `BLOCKED`, `RETRYING` ou `REJECTED`, nem `run_id`.
4. Não há lock por episódio; dois runs podem sobrescrever WAV/bed/MP4/segmentos.
5. `-y` e paths fixos tornam reexecução destrutiva para uma versão não aprovada.
6. Mix só registra `mean_volume`; integrated LUFS/true peak/inteligibilidade não fazem parte do relatório técnico.
7. CI não instala/roda FFmpeg, render E2E, validator com artefatos ou testes de path boundary.
8. Proveniência manual do AI Studio não registra modelo/parâmetros/conta/projeto com prova verificável.
9. Bed procedural não tem seed explicitado nem hash registrado; re-render pode não ser bit-a-bit reproduzível.
10. Documentos históricos estão misturados com o estado atual e podem induzir decisão errada.

## 14. P2 / P3 FINDINGS

**P2:** ASR word-level; golden fixtures audiovisuais; restore test; JSONL por etapa; configuração fora do código; registro de versões de FFmpeg/Pillow/Python; batch test com poucos episódios; cleanup de intermediários.

**P3:** assets premium S01/S04; refinamentos de motion; comparação de vozes; dashboard; publicação automática; ranking de temas. Nenhum desses deve preceder P0/P1.

## 15. DATA / CONTEXT FLOW

O contexto factual nasce em conversa/documentação, é materializado parcialmente no TXT e parcialmente em claims/spec. O áudio manual não carrega uma transcrição verificável. A ASS é outra cópia textual. O render recebe somente paths, não recebe claims, fontes, scene IDs ou aprovação. O validator lê o manifest e alguns paths, mas não valida todos os paths declarados.

Há perda de contexto entre: claims→script, script→áudio, script→captions, manifest→render e gates→status. A duplicação textual é o principal problema de fluxo.

## 16. DATA LINEAGE

**Técnico comprovado:** WAV local → mix AAC; frames → motion H.264; ASS → captions queimadas; hashes de script/WAV/MP4 registrados.

**Factual incompleto:** fonte NASA/JPL → claims JSON → TXT/ASS/áudio não é uma cadeia única. Não há claim IDs em cada sentença, nem transcrição do áudio coletado manualmente.

**Proveniência faltante:** versão do modelo AI Studio, parâmetros de geração, projeto/conta (sem expor segredo), versão de FFmpeg, configuração do bed e hash dos assets visuais.

## 17. STATE MACHINE

Estado observado: `TECH_VALIDATED` + `approval_status: REVIEW_REQUIRED`, com gates booleanos. A máquina anterior é implícita e não tem terminais de falha.

Estado recomendado:

`NEW → SCRIPT_VALIDATED → FACTS_VALIDATED → AUDIO_READY → VISUAL_READY → SYNC_VALIDATED → RENDERED → TECH_VALIDATED → EDITORIAL_REVIEW → APPROVED → DELIVERED → MEASURED → LEARNING_REVIEW`.

Qualquer gate crítico leva a `FAILED` ou `BLOCKED`; mudança após aprovação cria nova versão; nunca altera o artefato aprovado.

## 18. DECISION QUALITY

Não existe score/ranking runtime. As decisões editoriais são manuais e coerentes com o formato: hook imediato, causa concreta, consequência física e lição sistêmica. Isso é adequado para o piloto; não deve receber score cosmético.

O problema de decisão atual é de aprovação do input, não de algoritmo de ranking: o sistema aceita como “sync válido” uma cadeia cuja identidade textual não foi demonstrada.

## 19. ARBITRARY RULES / THRESHOLDS

| Número/regra | Classificação | Observação |
|---|---|---|
| 1080×1920 / 30 fps | requisito de formato | razoável e verificado |
| tolerância vídeo-áudio 0,5 s | HEURISTIC | precisa justificar por plataforma/uso |
| WAV >1 s | HEURISTIC | não substitui duração esperada/transcrição |
| mean volume > -60 dB | HEURISTIC | fraco para inteligibilidade |
| limiter 0,93 | HEURISTIC | true peak deve ser medido no output |
| font size 48 / margins ASS | HEURISTIC | precisa de mobile QA |
| 58,36 s | DADO deste áudio | não é regra global |
| 6 cenas | decisão do episódio | deveria ser manifest-driven |
| zero retry no TTS | política de segurança | falta retry só para erros transitórios idempotentes |

## 20. FALSE POSITIVES / NEGATIVES

**Falso positivo provável:** MP4 técnico passa com captions de outra versão; arquivo WAV trocado mantendo nome; claim register parcial; mix audível no desktop mas mascarado no celular; `APPROVED` não vinculado ao output.

**Falso negativo provável:** um áudio correto é rejeitado porque o validator não suporta aprovação; arte procedural editorial coerente é descartada por preferência sem teste; duração abaixo de 60 s é rejeitada apesar de roteiro completo.

O erro mais caro é o falso positivo factual/sincronização, porque pode chegar ao público com aparência de controle.

## 21. AI / MODEL AUDIT

TTS via API é probabilístico; o adaptador fixa modelo/voz/style, mas não seed nem todos os parâmetros. A coleta efetiva deste episódio foi manual no AI Studio e não prova o model ID. O visual procedural é determinístico por seeds de cena; o bed pode não ser reproduzível.

Não há fallback pago configurado, o que respeita free-first. Também não há health check, quota ledger ou freshness check automatizado. O motor deve tratar indisponibilidade do modelo como `BLOCKED`, não inventar áudio alternativo.

## 22. HALLUCINATION / GROUNDING RISKS

O risco de falsa interface NASA foi bem reduzido pela política visual. O risco factual permanece porque a fonte canônica não governa o texto efetivo. Claims com URL não substituem a exigência de mapear cada afirmação à versão narrada. Qualquer futura ingestão web deve tratar conteúdo externo como dado não confiável, nunca como instrução de sistema.

## 23. AUTOMATION AUDIT

Não há cron, fila, scheduler, retry worker, publish job ou alerta de missed run. A ordem correta depende do operador. Isso é aceitável para um piloto assistido; não é operação semanal autônoma.

CI existe e foi verificada, mas só cobre compile/unit/JSON. Ela não é a automação de produção audiovisual.

## 24. IDEMPOTENCY / DUPLICATION

O TTS impede sobrescrita sem `--overwrite` e usa escrita atômica. Os renderizadores usam `-y` e nomes fixos. Não existe chave de idempotência nem diretório por run.

Chave recomendada: `episode_id + version + script_sha256 + audio_sha256 + render_config_sha256`. Mesmo input deve reutilizar resultado validado; nova variação exige `force_new` e nova versão.

## 25. CONCURRENCY / RACE CONDITIONS

Não há workers atuais, mas a implementação é vulnerável a dois comandos simultâneos: ambos podem gerar o mesmo bed, substituir segmentos e atualizar o manifest. Antes de qualquer batch, usar diretório imutável por versão e lock por `episode_id`.

## 26. FAILURE MATRIX

| Falha | Classe | Detecção atual | Resposta correta |
|---|---|---|---|
| roteiro vazio/ausente | DATA | parcial no CLI | abortar |
| script alterado após áudio | DATA | hash do TXT, mas sem sync textual | bloquear e regenerar |
| key ausente | AUTH/CONFIG | CLI | abortar sem segredo |
| 429/quota | RESOURCE/TRANSIENT | exceção genérica | backoff limitado + estado BLOCKED |
| WAV inválido | DEPENDENCY/DATA | RIFF/rate/canais | abortar |
| captions de outra versão | QUALITY | não detectado | comparar transcript/hash; abortar |
| FFmpeg falha | LOGIC/RESOURCE | exit code | FAILED + preservar versão anterior |
| frame errado com nome válido | QUALITY | não detectado | asset hash/QA visual |
| aprovação antiga | STATE | não detectado | approval hash + version check |
| execução concorrente | OPERATIONAL | não detectado | lock/dedupe |
| storage cheio | RESOURCE | exit code eventual | FAILED + cleanup seguro |

## 27. SILENT FAILURES

1. **Texto divergente:** passa duração; sinal atual inexistente; severidade crítica; resposta: gate de transcript.
2. **Caption fora da fala:** bounds passam; detectar por ASR/alinhamento; bloquear.
3. **Mix baixo/mascarado:** mean volume passa; medir LUFS/true peak e revisar celular.
4. **Frame errado:** ffprobe passa; detectar hash/manifest/QA visual.
5. **Bed diferente em rerun:** output muda sem razão registrada; seed/hash.
6. **Docs stale:** operador toma decisão errada; arquivar histórico e gerar estado atual.
7. **Falha parcial usando MP4 anterior:** nome fixo pode mascarar falha; output temporário + atomic rename.

## 28. STOP-THE-LINE CONDITIONS

Parar imediatamente se: transcript canônico ausente; script/áudio/captions não correspondem; claim material sem fonte; WAV corrompido/silencioso; asset obrigatório ausente; output fora de 1080×1920; streams divergem; aprovação ausente; output aprovado seria sobrescrito; path aponta para outro motor; quota/conta/projeto não confirmados; validação crítica falha.

## 29. DEPENDENCY REGISTER

| Dependência | Criticidade | Estado/risco |
|---|---:|---|
| Google AI Studio | alta | coleta manual, UI/modelo/quota variáveis |
| Gemini API/SDK | alta | chave, modelo, quota, drift de API |
| Python | média | versão deve ser fixada/testada |
| Pillow | média | gera assets procedurais |
| FFmpeg/libass | crítica | motion, captions, mix/export |
| sistema de arquivos | crítica | media local e outputs |
| GitHub Actions | média | validação de código; não renderiza mídia |
| Library/persistência | alta | recuperação e retenção ainda não testadas |
| YouTube/analytics | futura | fora do escopo atual |

Para cada dependência faltam, em geral, versão registrada, health check, quota/custo e fallback formal.

## 30. VERSION / FRESHNESS RISKS

`requirements.txt` usa intervalo (`google-genai>=2.25.0,<3.0.0`), portanto builds futuras podem mudar. FFmpeg/Pillow/Python não estão registrados no manifest. O modelo manual está `UNKNOWN_FROM_MANUAL_COLLECTION`. Documentos de auditoria anteriores contêm afirmações históricas sobre GitHub que já não são atuais.

Fix: registrar toolchain no report e marcar docs antigos como `ARCHIVED`; não atualizar modelo/API sem canary e revalidação.

## 31. RESOURCE / QUOTA RISKS

Não há contador de chamadas, duração diária, quota restante, espaço, tempo de render ou custo por episódio. O modo free-first reduz risco financeiro, mas não torna quota infinita. Quota esgotada deve produzir `BLOCKED`, não fallback silencioso.

## 32. SECURITY / PERMISSIONS

Pontos positivos: chave via ambiente; `.env` ignorado; nenhum segredo no código; repositório privado; media não versionada. Gaps: não há rotação documentada, verificação de conta/projeto, allowlist de paths ou teste automatizado que impeça cross-project contamination. Comentários não são enforcement.

## 33. OBSERVABILITY

Existem hashes, `ffprobe`, `volumedetect` e relatório JSON. Faltam `run_id`, timestamps por etapa, hashes de todos os inputs/outputs, config hash, versão de ferramentas, erro classificado, retries, quota e correlação entre manifest e log.

## 34. LOGGING / ALERTING

Adicionar um JSONL por execução com `run_id`, `episode_id`, `version`, `stage`, `status`, input/output hashes, duration_ms, tool versions, error_class, retry_count e reason. Alertas apenas para gates críticos, segurança, quota, overwrite, drift e aprovação pendente; não criar alerta decorativo por frame.

## 35. QUALITY GATES

Gates necessários: `SCRIPT_VALID`, `FACTS_VALID`, `AUDIO_VALID`, `VISUAL_VALID`, `TRANSCRIPT_SYNC_VALID`, `CAPTIONS_VALID`, `MIX_VALID`, `EXPORT_VALID`, `EDITORIAL_APPROVED`.

Estado atual: script/facts/audio/visual/sync/export aparecem como true no manifest, mix e editorial como false. O problema é que alguns booleans foram preenchidos manualmente e o validator não prova todos. `TECH_VALIDATED` deve significar apenas gates técnicos efetivamente executados; `APPROVED` exige gates editoriais e registro humano.

## 36. OUTPUT CONTRACT

Um episódio válido deve entregar: `episode_id`, `version`, transcript hash, claims coverage, audio/visual/captions/mix/output hashes, duração, dimensões, fps, codec, voz/modelo/proveniência, gate results, status, approval record e timestamps.

O output aprovado é imutável. Correção cria `v2`, preserva `v1` e invalida qualquer approval que não corresponda ao hash exato.

## 37. METRICS / KPIs

**North Star:** Shorts válidos aprovados por episódio, sem incidentes factuais.

**Leading:** taxa de gates aprovados, tempo script→audio, audio→render, intervenção manual, correções de caption, tempo de recuperação, custo/quota por output válido.

**Quality guardrails:** erro factual, mismatch de transcript, falha silenciosa, duplicidade, quota failure, clip de true peak, reclamação de inteligibilidade.

**Resultado futuro:** retenção em 1–3 s, average percentage viewed, conclusão, replay, compartilhamento/comentário e inscritos por mil views. Views isoladas são métrica de vaidade.

## 38. FEEDBACK LOOP

Não existe feedback loop real. O scorecard editorial é avaliação pré-publicação, não aprendizado.

Loop futuro: `publish → medir 1h/24h/7d → comparar com baseline → diagnosticar → formular uma hipótese → testar uma variável → validar em coorte → atualizar regra`. Não ajustar o motor com base em um único outlier.

## 39. CONFIG DRIFT

Drifts confirmados: TXT versus ASS; seis cenas versus sete na edit-spec; status históricos de áudio/música/GitHub; `mix_valid` falso em manifest versus docs que dizem mix final; caminhos/configuração duplicados entre manifest e scripts.

## 40. SINGLE SOURCE OF TRUTH

O manifest deve ser SSOT operacional, mas hoje não é consumido por todos os módulos. A transcrição deve ser SSOT de conteúdo; claims devem mapear sentenças; Markdown deve ser explicativo/histórico, não controlador.

## 41. TECHNICAL / OPERATIONAL DEBT

Dívidas: episódio-specific hardcoding; falta de transcript gate; falta de ASR; falta de aprovação persistente; falta de locks; falta de logs; lack de E2E/restore/batch; toolchain não fixado; documentação histórica sem archive marker.

## 42. BACKUP / RECOVERY / ROLLBACK

Arquivos locais e pacote de fonte foram persistidos, mas restore não foi testado. Não há snapshot formal por versão nem backup automatizado de media. Rollback é manual.

Plano mínimo: armazenar manifest/report e hashes por versão; manter último `APPROVED`; nunca apagar versão anterior durante rerun; testar materialização de um episódio a partir do pacote; rollback dispara quando gate/regra/modelo muda.

## 43. GAP ANALYSIS

Um especialista perceberia imediatamente: o contrato de transcript está quebrado; claims não chegam ao render; o estado técnico não representa aprovação; os scripts não aceitam um episódio genérico; não há observabilidade de run; não há feedback de audiência; a proteção contra outros motores é processual, não programática.

## 44. BREACH / BYPASS ANALYSIS

É possível editar ASS, trocar WAV mantendo nome, trocar frame, executar render direto com `-y`, editar manifest manualmente e publicar o MP4 sem registro. O validator não detecta todos esses bypasses. A solução é hash/versionamento, allowlist de paths, approval record e validator que consuma o manifest de ponta a ponta.

## 45. INTERNAL CONFLICTS

| Regra A | Regra B | Impacto | Resolução |
|---|---|---|---|
| TXT é roteiro SSOT | ASS é outra narrativa | P0 | escolher uma versão e regenerar tudo |
| `sync_valid:true` | validator só checa bounds | P0 | renomear para timing-only até ASR/transcript gate |
| manifest controla paths | render usa paths hardcoded | P1 | render manifest-driven |
| `APPROVED` é estado futuro | validator sempre falha APPROVED | P1 | validar approval hash corretamente |
| docs atuais | audit review histórica | P2 | marcar histórico/arquivar |

## 46. RED TEAM

Ataque mais provável: copiar um novo WAV para o nome antigo e rodar validator. Resultado: se duração/rate/mean volume forem aceitáveis, passa; captions e script podem ser de outra tomada. Segundo ataque: editar cena crítica mantendo dimensão; passa ffprobe. Terceiro: executar dois runs; o último sobrescreve assets. Quarto: usar aprovação de versão antiga. Quinto: quota/modelo mudar e o operador confundir fallback manual com mesma proveniência.

## 47. ADVERSARIAL TESTS

Casos obrigatórios: TXT vazio; TXT alterado depois do áudio; captions com texto diferente; captions com gap/overlap; WAV silencioso, curto, sample rate errado e tomada diferente; asset ausente; frame errado com mesmo nome; path fora da raiz; output pré-existente; execução interrompida; 429; resposta sem RIFF; dois runs concorrentes; approval hash de versão anterior.

## 48. PRE-MORTEM

1. Mismatch de transcript/captions — probabilidade alta, impacto crítico — detectar por hash/ASR — prevenir com SSOT.
2. Publicação antes de aprovação — média/alto — detectar status — prevenir com delivery gate.
3. Quota/model drift — média/alto — health/freshness — bloquear sem fallback inventado.
4. Visual genérico derruba retenção — alta/médio — retenção/coorte — testar S01/S04 depois da correção.
5. Mix mascarado no celular — média/alto — LUFS + phone QA — gate de mix.
6. Overwrite perde versão — média/alto — version dirs/lock — atomic publish.
7. Docs stale causam operação errada — alta/médio — docs CI/status — archive marker.
8. Escala manual quebra — alta/alto — batch test — só escalar após três episódios.
9. Claim sem fonte — média/crítico — claims coverage — stop-the-line.
10. Restore impossível — baixa/muito alto — restore drill — backup versionado.

## 49. EDGE CASES

Prioridade alta: roteiro editado após TTS; pronúncia de nomes/unidades; tomada manual não correspondente; caption vazando safe zone; arquivo antigo com mesmo nome; storage cheio; restart após falha; mudança de modelo; approval de v1 aplicada a v2; conteúdo externo malicioso quando pesquisa for automatizada.

## 50. COST / LATENCY / EFFICIENCY

Custo monetário efetivo não foi medido; o desenho é free-first, mas quota/tempo/armazenamento são custos operacionais. A coleta manual do TTS é o maior gargalo. Há trabalho duplicado na manutenção de TXT, ASS, edit-spec e manifest. A simplificação correta é uma transcrição canônica + claims estruturados + geração de captions a partir dela; não um dashboard ou microserviço.

## 51. SCALABILITY

10 episódios: possível com supervisão, mas drift e overwrite já ameaçam. 100: não confiável sem diretório por versão, lock, dedupe e logs. 1.000: fora do desenho atual. 10.000: fora do objetivo. Não construir escala antes de três episódios completos e um batch/recovery test.

## 52. WHAT TO REMOVE

Remover a duplicação textual não controlada; remover a escrita inicial redundante do concat em `build_mars_visual_draft.py`; remover constantes de duração que não são autoridade; retirar status históricos do caminho operacional ou marcá-los `ARCHIVED`. Não remover Charon, validator, claims, visual editorial ou voice-first mix.

## 53. WHAT TO FIX

**Agora:** unificar transcript; corrigir claims; fazer validator provar transcript/captions; corrigir caminho `APPROVED`; impedir bypass de manifest; registrar approval hash; bloquear publish sem gates.

**Antes do episódio 2:** run directories, idempotency key, lock, error classes, output temporário/atomic rename, LUFS/true peak e docs coerentes.

## 54. WHAT TO OPTIMIZE

Depois da correção: ASR word-level; cache por hash; melhores assets S01/S04; paralelismo somente por episódio; cleanup de intermediários; comparação de frames-chave. Não otimizar arte antes de resolver correção do texto.

## 55. WHAT TO ADD

Adicionar: `transcript.txt` canônico versionado; claims com `sentence_id`; `captions.source_transcript_sha256`; manifest-driven render; approval record; `run.jsonl`; lock; toolchain versions; LUFS/true-peak; golden fixtures; restore test; opcional ASR adapter; decision journal.

## 56. EVIDENCE REGISTER

| Achado | Evidência | Confiança | Ação |
|---|---|---|---|
| MP4 técnico existe | ffprobe 1080×1920, H.264/AAC, 58,366667 s | Alta | manter |
| áudio Charon local | WAV 24 kHz mono, hash `6d2c...cca3c` | Alta | manter provenance |
| CI verde | workflow e run concluído | Alta | ampliar cobertura |
| texto divergente | TXT 121 palavras normalizadas vs ASS ~186; frases exclusivas | Alta | P0 |
| validator não testa semântica | código só testa bounds | Alta | P0 |
| captions phrase-level | manifest `PHRASE_LEVEL_MANUAL` | Alta | ASR/transcript gate |
| LUFS atual | ebur128: I -18,3 LUFS, true peak -0,9 dBFS | Alta | registrar no report; phone QA |
| aprovação ausente | `approval_status: REVIEW_REQUIRED` | Alta | não publicar |
| feedback ausente | nenhuma integração/analytics | Alta | fora do piloto, planejar |

## 57. PRIORITIZED CHANGESET

| Prioridade | Ação | Classificação |
|---|---|---|
| P0 | unificar roteiro/áudio/captions/claims | CORRIGIR AGORA |
| P0 | impedir `TECH_VALIDATED` quando transcript não está comprovado | CORRIGIR AGORA |
| P1 | corrigir aprovação por hash e estado persistente | IMPLEMENTAR |
| P1 | tornar render/validator manifest-driven | IMPLEMENTAR |
| P1 | lock, version dirs, atomic output, idempotência | IMPLEMENTAR |
| P1 | registrar LUFS/true peak e phone QA | TESTAR |
| P1 | logs JSONL e toolchain/freshness | IMPLEMENTAR |
| P2 | ASR word-level, golden/E2E/recovery/batch | TESTAR |
| P2 | assets premium S01/S04 | TESTAR |
| P3 | queue, publish, dashboard, analytics | DEFERIR |
| — | Charon, visual editorial, voice-first, no CTA | MANTER |

## 58. AS-IS VS TO-BE

**AS-IS:** bancada episódica; várias cópias do texto; manifest parcialmente consumido; validator técnico de arquivo; aprovação manual não vinculada; media local; sem logs/locks/feedback.

**TO-BE mínimo:** uma transcrição canônica; claims mapeados; áudio/captions/visual com hashes; render dirigido por manifest; gates semânticos e técnicos; estado por versão; approval hash; logs; rollback.

**Delta real:** não requer reescrever o projeto. Requer corrigir o contrato de dados e a validação antes de adicionar automação.

## 59. OPTIMIZED ARCHITECTURE

1. **Content:** transcript canônico + claims/source register.
2. **Audio:** Charon/TTS ou coleta manual, provenance, hash, duração.
3. **Visual:** scene manifest + assets com hash/proveniência.
4. **Edit:** captions derivadas da transcrição, motion, mix.
5. **Validation:** schema, transcript, factualidade, audio, visual, sync, loudness, export.
6. **Approval:** revisão humana no celular vinculada ao hash.
7. **Delivery:** futura publicação bloqueada sem `APPROVED`.
8. **Observability:** JSONL, reports, versions, toolchain.

Cada camada recebe contrato explícito e não pode escrever em outro projeto.

## 60. FINAL PIPELINE

`NEW → SCRIPT_VALIDATED → FACTS_VALIDATED → AUDIO_READY → VISUAL_READY → TRANSCRIPT_SYNC_VALIDATED → RENDERED → TECH_VALIDATED → EDITORIAL_REVIEW → APPROVED → DELIVERED → MEASURED → LEARNING_REVIEW`.

Falha crítica: `FAILED/BLOCKED`. Mudança de input/modelo: nova versão. A publicação não deve ser chamada pelo render local.

## 61. CHANGESET MÍNIMO EFETIVO

1. Promover o texto efetivamente aprovado a transcript SSOT.
2. Atualizar claims para cobrir cada afirmação material.
3. Associar áudio/captions ao hash do transcript.
4. Fazer validator comparar texto/IDs e não apenas duração.
5. Corrigir approval validator e criar approval record.
6. Tornar paths do render dependentes do manifest.

Esse conjunto entrega a maior parte do ganho de correção sem criar fila, banco ou microserviços.

## 62. TEST MATRIX

| Tipo | Cobertura necessária |
|---|---|
| Unit | parser, hashes, schema, timecodes, audio gates |
| Contract | manifest, claims, provenance, ASS |
| Integration | TTS mock, FFmpeg probe, caption burn |
| E2E | transcript → assets → render → validate |
| Regression | episódio Mars golden |
| Adversarial | transcript divergente, WAV trocado, path externo, asset errado |
| Recovery | kill/restart, partial output, restore |
| Security | secrets, path allowlist, protected-target contamination |
| Manual acceptance | celular: voz, captions, safe zones, payoff |
| Batch | 3–10 episódios, dedupe, order, no state leak |

## 63. GOLDEN TEST SET

1. Mars normal com transcript/claims/captions idênticos: passa.
2. WAV silencioso: falha.
3. TXT alterado após áudio: falha.
4. ASS com texto de outra versão: falha.
5. Caption fora da duração: falha.
6. Asset ausente/errado: falha.
7. Path para outro motor: falha.
8. Rerun idêntico: reutiliza ou recusa duplicata.
9. Approval hash de versão anterior: falha.
10. Render interrompido: não promove output parcial.

## 64. REGRESSION PROTECTION

Proteger transcript hash, claims coverage, voz, duração, captions, safe zones, loudness/true peak, resolução, ausência de CTA, visual editorial, isolamento e approval hash. Toda mudança precisa de teste e rollback para o último aprovado.

## 65. ROLLBACK PLAN

**Trigger:** gate crítico; claim corrigido; troca de modelo; mudança de toolchain; output divergente; aprovação inválida.

**Método:** marcar versão `REJECTED/BLOCKED`; preservar arquivos; selecionar último manifest `APPROVED`; nunca sobrescrever; gerar nova versão a partir do transcript correto.

**Validação:** hashes, ffprobe, transcript/caption gate, loudness, revisão humana se conteúdo ou áudio mudou.

## 66. IMPLEMENTATION ROADMAP

**Fase 0 — safety/correction:** resolver transcript P0, claims, sync gate, approval bug.  
**Fase 1 — correctness:** manifest-driven paths, schema, hashes, docs atuais.  
**Fase 2 — reliability:** version dirs, locks, atomic output, error classes, idempotência.  
**Fase 3 — quality:** ASR opcional, LUFS/true peak, phone QA, golden tests.  
**Fase 4 — observability:** JSONL, toolchain/freshness, quota/latency.  
**Fase 5 — automation:** pequeno batch assistido; sem publicação automática.  
**Fase 6 — optimization:** assets premium, cache, paralelismo seguro.  
**Fase 7 — scale:** somente após três episódios completos sem regressão.

## 67. SECOND AUDIT

A proposta pode criar complexidade se ASR, logs e state machine forem implantados como serviços antes de corrigir a transcrição. O manifest continua sendo uma fonte; não criar outro banco. O approval record deve ser um JSON simples. O lock só é necessário antes de batch. A solução melhora correção com poucas mudanças e não prejudica Charon, visual ou voice-first.

## 68. SIMPLIFICATION PASS

Não adicionar microserviços, dashboard, múltiplos modelos, ranking de temas, retries infinitos, efeitos, CTA ou publicação nesta fase. Um transcript, um manifest, um validator, um relatório, diretórios por versão e um approval record são suficientes.

## 69. REMAINING RISKS

Mesmo após o changeset: prosódia e pronúncia exigirão revisão humana; AI Studio pode mudar; fontes podem ser atualizadas; visual procedural pode ter retenção menor; analytics ainda serão ausentes; quota free pode limitar cadência; backup precisa de exercício real; ASR pode introduzir erro próprio.

## 70. DEFINITION OF DONE

O episódio pode ser `APPROVED` somente quando: transcript único e hashado; claims 100% cobertos; áudio/proveniência vinculados; captions derivadas e sincronizadas; gates técnicos passam; LUFS/true peak registrados; mobile QA aprovado; output hash exato registrado; repositório/paths isolados; versão anterior preservada; rollback possível.

O motor só pode ser chamado `OPERATIONAL AND GOOD` depois de pelo menos três episódios completos, golden tests, batch pequeno, recovery test e zero P0 aberto. `READY TO SCALE` ainda está distante.

## 71. AUDIT COVERAGE CHECK

| Área | Cobertura |
|---|---|
| objetivo/escopo/spec/regras | auditado |
| implementação/estado/contratos/lineage | auditado |
| decisões/IA/grounding/injection | auditado |
| automação/falhas/retry/idempotência/concorrência | auditado |
| segurança/permissões/observabilidade/logs/alertas | auditado |
| quality/output/KPIs/feedback | auditado |
| custo/latência/escala/load | auditado conceitualmente; load real ainda UNKNOWN |
| backup/recovery/rollback/regression | auditado; restore real ainda não verificado |
| publicação/analytics | N/A no escopo atual, explicitamente ausente |

## 72. FINAL VERDICT

O motor **funciona como bancada de renderização de um episódio**, e os artefatos técnicos são reais e verificáveis. Ele **não está pronto para publicação** porque o próprio contrato de conteúdo está quebrado: o roteiro declarado não é a mesma versão textual usada nas captions/especificação, e o validator não detecta isso.

Classificação final: **OPERATIONAL WITH BLOCKERS** para Mars 001; **OPERATIONAL BUT FRAGILE** como motor de produção repetível; não é `OPERATIONAL AND ROBUST` nem `READY TO SCALE`.

Próxima ação obrigatória, nesta ordem: **(1)** escolher a versão canônica da narrativa; **(2)** regenerar/confirmar áudio e captions a partir dela; **(3)** ampliar claims; **(4)** corrigir o gate de transcript e o caminho APPROVED; **(5)** só então fazer a revisão final no celular. Charon, o visual editorial, o mix voz-primeiro, o formato vertical e o isolamento dos outros motores devem permanecer como estão.

### Evidências locais executadas nesta auditoria

- `python -m unittest discover -s tests -v`: 4/4 passaram.
- `python -m py_compile narrate.py production/*.py`: passou.
- `python production/run_episode.py --manifest production/mars-climate-orbiter-episode.json`: `TECH_VALIDATED`, mas sem gate semântico de transcript.
- MP4: H.264, 1080×1920, 30 fps, 58,366667 s; AAC mono 24 kHz, 58,360000 s.
- WAV: PCM s16le, 24 kHz mono, 58,36 s; SHA-256 `6d2c704655287e85ee7b42d4c47ad0f99cbc062b307d13760688d4b98dfcca3c`.
- Roteiro declarado: SHA-256 `87e0c2a3f7c18809362d8f6fed6374d1223fdb25ffa05b189f15fc5caa7e7fbe`.
- MP4: SHA-256 `fe6dd616f15c99de5f6250aa0d182f65d819b1ff7dcc836130ac9cebd5f2066b`.
- Mix medido nesta auditoria: integrated loudness aproximadamente `-18,3 LUFS`; true peak `-0,9 dBFS`; phone QA ainda não comprovado.
- CI do repositório privado independente: concluído com sucesso; media local não foi enviada ao GitHub.
