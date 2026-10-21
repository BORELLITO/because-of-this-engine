
# BECAUSE OF THIS — Auditoria Pente-Fino do Motor Operacional

Data: 2026-10-21  
Escopo: somente o motor independente do BECAUSE OF THIS e a produção do Short “Mars Climate Orbiter”.  
Fora do escopo: Capta Pronto, Corte Fino, Publisher, Creator e qualquer outro motor/repositório do GitHub. Nenhum foi alterado.

## 1. EXECUTIVE VERDICT

Classificação: OPERATIONAL BUT FRAGILE para um único Short; NON-OPERATIONAL como motor escalável/autônomo.

Há evidência de uma execução real: MP4 vertical H.264/AAC, 1080x1920, 30 fps, 58,37 s, narração Charon, captions queimadas e mix voz-primeiro. Isso prova que a bancada produz um episódio. Não prova que o motor é repetível, observável ou seguro em lote.

O sistema atual é uma cadeia manual e específica de Mars. Tem scripts úteis, mas não tem ainda uma unidade de trabalho genérica, estado persistente, gates fail-closed, claims/fontes rastreáveis, retries classificados, logs estruturados, publicação, métricas de resultado ou feedback loop. A recomendação é EVOLVE > REBUILD: manter render, voz e linguagem editorial; corrigir correção, lineage, estado e observabilidade antes de escala.

## 2. REAL OBJECTIVE

Produzir repetidamente Shorts faceless em inglês americano para o canal BECAUSE OF THIS, com fatos verificáveis, suspense documental, visual editorial claramente ilustrativo, narração consistente, captions sincronizadas e entrega pronta para aprovação/publicação.

O objetivo não é apenas gerar um MP4. O output válido deve ser factual, inteligível, sincronizado, diagnosticável, versionado e não pode tocar nos quatro motores protegidos.

## 3. SCOPE / OUT OF SCOPE

Dentro: roteiro aprovado; geração/coleta de Charon; frames PIL; motion FFmpeg; captions ASS; bed procedural; mix/export; validação técnica pontual; documentação.

Fora: descoberta automática de temas; pesquisa factual automatizada; banco de episódios; fila/schedule; ingestão automática do AI Studio; ASR word-level; publishing/analytics; monitoramento contínuo; feedback estatístico; backup/restore formal; CI/CD; escala para centenas de runs.

## 4. AS-IS ARCHITECTURE

Roteiro TXT/manual
-> especificação editorial Markdown/manual
-> áudio Charon coletado do AI Studio
-> seis frames PIL
-> seis segmentos FFmpeg
-> captions ASS com timecodes manuais
-> ambient bed + mix
-> MP4 final
-> ffprobe/volumedetect + inspeção humana recomendada.

É uma bancada de produção episódica, não um pipeline de jobs. O Markdown contém mais contexto que os scripts; o render recebe caminhos, não claims, fontes, beats, asset IDs ou aprovação.

## 5. SYSTEM INVENTORY

| Componente | Estado real | Entrada/saída | Risco principal |
|---|---|---|---|
| examples/mars_climate_orbiter.txt | IMPLEMENTED/VERIFIED | roteiro -> TXT | sem fontes/claim IDs |
| narrate.py | IMPLEMENTED/UNIT TESTED | TXT/chave -> WAV + JSON | chamada real desta amostra não foi pelo CLI |
| WAV Charon local | VERIFIED neste episódio | AI Studio -> PCM 24 kHz mono | provenance incompleta |
| build_mars_visual_draft.py | IMPLEMENTED/EXECUTED | parâmetros -> 6 PNG + draft | configuração hardcoded |
| build_mars_visual_motion.py | IMPLEMENTED/VERIFIED | PNG + durações -> segments + MP4 | sem gate de continuidade |
| captions ASS | RENDERED/PARTIALLY VERIFIED | timecodes manuais -> pixels | phrase-level, não word-level |
| render_mars_final.py | IMPLEMENTED/VERIFIED | visual/WAV/ASS -> MP4 | duração hardcoded; poucos gates |
| ambient bed | IMPLEMENTED/VERIFIED | lavfi -> WAV | qualidade subjetiva sem teste automatizado |
| edit-spec Markdown | IMPLEMENTED | decisões -> documentação | pode divergir do código |
| production Markdown/README | IMPLEMENTED | estado -> documentação | há estado histórico conflitante |
| unittest test_narrate.py | VERIFIED | mocks -> 4 testes verdes | não testa audiovisual/E2E |
| Library artifacts | VERIFIED | MP4/WAV/spec persistidos | restore test não realizado |

Não existe hoje owner formal para claims, aprovação, delivery, analytics ou recovery. Esses são gaps de responsabilidade.

## 6. CURRENT SYSTEM SPEC — FONTE DA VERDADE

| Regra | Valor atual | Estado | Implementação/validação |
|---|---|---|---|
| isolamento | não alterar Capta Pronto, Corte Fino, Publisher ou Creator | HARD LOCK | escopo independente; mantido |
| canal | BECAUSE OF THIS, faceless, inglês americano | DECLARED/episódio executado | roteiro/produção |
| tom | factual, sombrio, suspense documental, contido | IMPLEMENTED neste episódio | script/style/visual |
| voz | Charon | VERIFIED neste episódio | WAV e decisão aprovada |
| formato | 9:16, 1080x1920, 30 fps | VERIFIED | ffprobe |
| duração | este áudio: 58,36 s | VERIFIED episódio | WAV/MP4 |
| captions | inglês, lower third seguro, branco + âmbar | PARTIALLY VERIFIED | ASS + render |
| visual | reconstrução editorial, sem falsa telemetria | IMPLEMENTED | código/spec |
| música | voz-primeiro, bed original discreto | VERIFIED tecnicamente | mix/peak |
| CTA/bumper | não usar | VERIFIED | ausente no render |
| publicação | só após revisão humana | DECLARED | não é estado bloqueante |

Divergências encontradas: a asset manifest ainda diz que voz não está local e música não executada; o README diz que geração real não foi testada; a spec descreve sete cenas, o render atual usa seis. A tabela de status do topo está mais atual. Isso é configuration/documentation drift.

## 7. RULE PRECEDENCE

1. isolamento e segurança;
2. hard locks explicitamente aprovados;
3. regra específica do episódio;
4. instrução mais recente;
5. regra geral do canal;
6. default do script.

Ambiguidade: faixa de projeto “60–70 s” versus episódio aprovado com 58,36 s. Este episódio foi aceito; para próximos, formalizar se é faixa editorial ou hard limit.

## 8. HARD LOCKS

Não negociáveis: não tocar os quatro motores; não publicar sem aprovação; não tratar arte gerada como arquivo/evidência; não inventar fatos; não expor chaves; Charon como voz até nova autorização; vertical 9:16; gates críticos fail-closed.

Adaptáveis: duração exata, número de cenas, asset procedural versus premium, intensidade de movimento e bed.

Experimentais: ASR word-level, troca de modelo, arte externa, automação de coleta/publicação.

## 9. DECLARED vs IMPLEMENTED vs VERIFIED

- MP4 específico: VERIFIED.
- TTS CLI: IMPLEMENTED/UNIT TESTED, chamada real não evidenciada.
- coleta AI Studio: VERIFIED somente neste run.
- Charon: VERIFIED neste episódio.
- captions: PARTIALLY VERIFIED.
- word-level sync: PROPOSED, não implementado.
- visual procedural editorial: VERIFIED como draft.
- qualidade cinematográfica premium: UNKNOWN/NOT VERIFIED.
- mix técnico: PARTIALLY VERIFIED; pico medido, loudness integrado não registrado.
- factualidade: DECLARED/revisão humana; sem fontes no pacote.
- quality gates automáticos: PARTIAL.
- retry, recovery, idempotência, monitoramento e feedback: NOT IMPLEMENTED.
- escala: UNKNOWN/não suportada.

Nunca tratar DECLARED como VERIFIED.

## 10. REQUIREMENTS TRACEABILITY MATRIX

| Requisito | Implementação | Teste/evidência | Status |
|---|---|---|---|
| isolamento | pasta/escopo independente | inspeção de paths | VERIFIED neste run |
| Charon | WAV + render | hash/duração/escuta | VERIFIED; provenance parcial |
| vertical | motion/render | ffprobe | VERIFIED |
| roteiro aprovado | TXT/spec | revisão humana/hash | PARTIAL; fontes ausentes |
| captions legíveis | ASS | render/frame | PARTIAL |
| streams alinhados | render | ffprobe: diferença 0,0067 s | VERIFIED técnico |
| voz inteligível | mix | peak; phone QA pendente | PARTIAL |
| não declarar sucesso falso | processo | não há state/gate runner | GAP |
| reexecução segura | scripts | overwrite/config manual | FRÁGIL |
| publicação aprovada | processo humano | sem approval record | DECLARED |
| aprender com resultados | analytics | inexistente | GAP |

## 11. WHAT IS EXCELLENT — DO NOT TOUCH

Preservar: isolamento; Charon; narrativa que inclui unidade + comunicação/systems engineering; reconstrução editorial sem falsa NASA; voice-first mix; ausência de CTA/bumper; efeitos contidos; atomic write do TTS; proteção contra overwrite no CLI; documentação que admite ausência de word-level sync.

## 12. P0 FINDINGS

P0-01 — Não há contrato de sucesso real. FFmpeg sair zero pode virar “pronto” mesmo com captions erradas, áudio silencioso ou claim não verificado. Causa: completion confundida com quality. Corrigir com validator fail-closed e status separado RENDERED/TECH_VALIDATED/APPROVED.

P0-02 — Proveniência factual não chega ao output. O TXT não traz claim IDs, fontes, data de checagem ou revisão. Causa: spec editorial não é input estruturado. Bloquear release se claims críticos não têm fonte.

P0-03 — Aprovação humana não é estado verificável. O pedido de “assistir no celular” não está vinculado ao hash do MP4. Bloquear delivery/publicação até APPROVED ligado à versão.

## 13. P1 FINDINGS

1. captions não derivadas do áudio por ASR; drift pode passar;
2. DURATION=58.36 está hardcoded;
3. paths/cenas são hardcoded; não existe episódio genérico;
4. erros não têm classe, retry policy, checkpoint ou recovery;
5. README/spec/manifest divergem;
6. não há run_id/JSONL/log de parâmetros/hashes;
7. não há E2E, golden, batch ou recovery test;
8. visual draft não tem gate automático de arte;
9. mix não registra LUFS integrado/true peak de release;
10. coleta AI Studio não tem sidecar equivalente ao CLI.

## 14. P2 / P3 FINDINGS

P2: config fora do código; episode_id; manifest JSON; hashes; cleanup/retention; frames golden; decision journal.

P3: assets premium para S01/S04; qualquer polish visual. Não adicionar CTA, glitch, logo intro ou efeitos para “parecer melhor”.

## 15. DATA / CONTEXT FLOW

O contexto passa por roteiro -> decisões humanas -> cenas hardcoded -> timecodes estimados -> render. Informações importantes ficam presas no Markdown: beats, claims, intenção visual, fontes e gate. A duração é duplicada no WAV, ASS, motion e Python. O manifest de assets não é consumido. S07 aparece na spec, mas a execução consolidou o final em seis cenas sem um schema que registre essa decisão.

## 16. DATA LINEAGE / PROVENANCE

Lineage técnico parcial: WAV -> render -> AAC; PNG -> motion -> H.264; ASS -> subtitles -> pixels. Hashes foram medidos, mas não reunidos em um manifest de episódio.

Lineage factual insuficiente: conversa/roteiro -> TXT -> voz/captions, sem fonte/data/claim transform. Isso é risco P0 para um canal factual.

## 17. STATE MACHINE

Hoje o estado é implícito: IDEA -> SCRIPT_APPROVED -> AUDIO_AVAILABLE -> VISUAL_DRAFT -> RENDERED -> HUMAN_REVIEW?. Não há FAILED, RETRYING, BLOCKED, REJECTED, APPROVED, PUBLISHED ou ROLLED_BACK persistidos.

Estado recomendado: NEW -> SCRIPT_VALIDATED -> FACTS_VALIDATED -> AUDIO_READY -> VISUAL_READY -> SYNC_VALIDATED -> RENDERED -> TECH_VALIDATED -> EDITORIAL_REVIEW -> APPROVED -> DELIVERED/PUBLISHED -> MEASURED -> LEARNING_REVIEW. Qualquer gate crítico leva a FAILED/BLOCKED.

## 18. DECISION QUALITY

Não há score/ranking runtime. As decisões são heurísticas editoriais válidas para Mars: hook imediato, unidade como mistério, consequência física, nuance sistêmica, voz contida, movimento limitado. Não inventar score só para parecer científico.

Falso positivo: MP4 passa FFmpeg, mas captions/claim/mix podem estar errados. Falso negativo: uma peça boa pode ser descartada por “visual procedural” sem teste de audiência.

## 19. ARBITRARY RULES / THRESHOLDS

1080x1920/30 fps = requisito razoável; 58,36 s = dado deste áudio, não regra global; music volume 0,22, limiter 0,93 e caption 48 px = heurísticos; seis cenas = decisão do episódio; retries zero no CLI = escolha segura contra duplicação, mas sem recuperação. Nenhum desses números deve virar score sem evidência.

## 20. FALSE POSITIVES / NEGATIVES

Aprovado indevidamente: arquivo com áudio silencioso; captions presentes porém fora da fala; claim sem fonte; frame errado com mesmo nome; aprovação antiga aplicada a novo WAV.

Rejeitado indevidamente: 58 s quando a narrativa está completa; arte procedural coerente descartada sem teste; voz boa rejeitada por preferência sem comparação controlada.

## 21. AI / MODEL AUDIT

TTS é probabilístico. O adaptador fixa modelo/voz/style, mas não seed nem parâmetros completos do AI Studio. O visual atual é determinístico/procedural. Script e factualidade são humanos.

A documentação oficial consultada em 2026-10-21 confirma Gemini 3.8 Flash-Lite TTS como modelo de alta vazão/custo-eficiência e WAV padrão; ainda assim quota, preço, UI e disponibilidade são dependências externas e precisam de freshness check por release.

## 22. HALLUCINATION / GROUNDING / INPUT NÃO CONFIÁVEL

Risco factual alto porque claims não têm fontes anexadas. Risco de falsa telemetria foi bem mitigado pela política visual. O CLI usa speech_metadata.style, reduzindo risco de instrução ser falada. Não existe ingestão web automatizada atual; se existir depois, conteúdo externo deve ser dados, nunca autoridade de sistema.

## 23. AUTOMATION AUDIT

Não há trigger, cron, fila, dependency ordering, schedule, missed-run alert ou disable switch. Scripts locais exigem execução manual na ordem correta. Isso é aceitável para o piloto, não para operação semanal.

## 24. IDEMPOTENCY / DUPLICATION

narrate.py protege saída sem --overwrite e faz escrita atômica. Renderizadores usam -y, paths fixos e substituem intermediários. Não existe episode_id/idempotency key. Reexecução pode gastar quota e substituir a versão anterior.

Chave recomendada: episode_id + script_sha256 + model + voice + style + render_config_sha256. Reutilizar output validado; gerar variação só com force_new explícito.

## 25. CONCURRENCY / RACE CONDITIONS

Não há workers hoje. Em escala, dois runs podem sobrescrever segments, MUSIC e OUT. Usar diretório por run e lock por episode_id antes de paralelizar.

## 26. FAILURE MATRIX

| Falha | Classe | Detecção atual | Resposta correta |
|---|---|---|---|
| script vazio/ausente | DATA | CLI | abort + motivo |
| key ausente | AUTH/CONFIG | CLI | abort sem segredo |
| 429/quota | TRANSIENT/RESOURCE | exceção genérica | backoff limitado e registro |
| resposta sem WAV | DEPENDENCY/DATA | RIFF check | abort fail-closed |
| FFmpeg falha | LOGIC/RESOURCE | exit code | estado FAILED |
| frame ausente | DATA | runtime | INPUT_VALID fail |
| captions erradas | QUALITY | não detectado | stop-the-line |
| áudio silencioso | QUALITY | não detectado | loudness gate |
| overwrite | OPERATIONAL | não detectado | versionar/recusar |
| storage perdido | STORAGE | não monitorado | restore test |

## 27. SILENT FAILURES

Mais perigosas: captions fora da fala; mix mascarado/baixo; claim sem fonte; frame errado; output parcial marcado como sucesso; retry manual duplicado; README stale levando a decisão errada.

Para cada uma, o sinal deve ser explícito: ASR/diff, LUFS/true peak/phone QA, claims coverage 100%, manifest/hash, status gate e idempotency key.

## 28. STOP-THE-LINE CONDITIONS

Parar se: script sem hash; claim crítico sem fonte; voz não aprovada; WAV corrompido/silencioso; asset obrigatório ausente; captions não cobrem o transcript; streams divergem além da tolerância; resolução/fps errados; outro motor aparece no target; output aprovado seria sobrescrito; aprovação mobile ausente.

## 29. DEPENDENCY REGISTER

Google AI Studio: coleta manual, alta criticidade, fallback CLI. Gemini API/SDK: TTS, alta, sujeito a quota/model drift. Pillow: frames, média. FFmpeg/libass: motion/caption/mix, crítica. Python: scripts, média. Library: persistência, alta. YouTube/analytics: futuro, ainda N/A. Para todas: registrar versão, auth, quota, custo, fallback e health check.

## 30. VERSION / FRESHNESS RISKS

O model ID atual foi conferido oficialmente, mas a documentação do pacote não registra data. Antes de cada mudança de API/modelo/preço/limite, repetir verificação oficial e salvar data/model ID. Não assumir que UI, voz ou quota permanecem estáveis.

## 31. RESOURCE / QUOTA RISKS

Não há consumo acumulado, token count, duração diária, espaço, tempo de render ou API quota monitorados. Quota zero produz erro/espera humana, o que é preferível a fallback inventado, mas deve virar estado observável.

## 32. SECURITY / PERMISSIONS

Bom: chave fora do código, .env ignorado, nenhum segredo exposto. Gap: sem rotação, account/project check ou least privilege formal. O isolamento dos outros motores é boundary de escopo; reforçar por paths permitidos e manifest de targets.

## 33. OBSERVABILITY

Há ffprobe, volumedetect e hashes pontuais. Faltam run_id, stage, timestamps, input/output hashes juntos, config version, error class, dependency status e correlation IDs. Hoje não se reconstrói um run futuro com precisão suficiente.

## 34. LOGGING / ALERTING

Adicionar JSONL por etapa: run_id, episode_id, stage, status, input_hashes, output_hashes, config_hash, duration_ms, error_class, retry_count e reason.

CRITICAL: claim/gate/security/overwrite. WARNING: quota/drift/manual review. INFO: render concluído. Evitar alerta decorativo por frame.

## 35. QUALITY GATES

Gates reais: SCRIPT_VALID; FACTS_VALID; AUDIO_VALID (RIFF, rate, duration, non-silence, provenance); VISUAL_VALID (assets, dimensions, continuity); SYNC_VALID; MIX_VALID (loudness/peak/intelligibility); EXPORT_VALID; EDITORIAL_APPROVED.

RENDERED nunca significa APPROVED.

## 36. OUTPUT CONTRACT

Um episódio deve entregar: episode_id, paths, version, status, hashes, duration, width, height, fps, audio rate, voice, model, claims status, gate results, approval status e timestamps. MP4 aprovado é imutável; mudança cria nova versão.

## 37. METRICS / KPIs

North Star: valid Shorts aprovados por episódio.

Leading: gate pass rate, manual intervention rate, caption correction rate, script-to-audio time, audio-to-render time, cost/time per valid output.

Lagging: retenção em 1–3 s, average percentage viewed, completion, replay, share/comment e inscritos por mil views.

Guardrails: factual error, asset/copyright incident, silent failure, duplicate publication, quota failure e queixas de inteligibilidade. Views isoladas são vanity.

## 38. FEEDBACK LOOP

Não existe feedback real. O scorecard é avaliação pré-publicação.

Loop recomendado: publish -> métricas em 1h/24h/7d -> baseline -> diagnóstico -> hipótese -> testar uma mudança -> validar em coorte -> atualizar regra. Não reagir a um único outlier.

## 39. CONFIG DRIFT / 40. SINGLE SOURCE OF TRUTH

A maior drift é duração duplicada, status stale e seis versus sete cenas. Criar episode.json como SSOT para script hash, claims, voice/model/style, duration, scenes, assets, captions, mix, render config, status e hashes. Markdown fica explicativo.

## 41. TECHNICAL / OPERATIONAL DEBT

Dívidas: duration hardcoded; scripts episódicos; ausência de manifest JSON; sem ASR; sem golden/E2E; documentação stale. Corrigir duration/manifest/gates antes do episódio 2; ASR antes de produção regular; scale só depois de vários episódios.

## 42. BACKUP / RECOVERY / ROLLBACK

MP4, WAV e spec foram persistidos, mas restore não foi testado. Não há snapshot formal de frames/scripts. Rollback é manual. Recomendação: manifest imutável por versão, preservação do último APPROVED e teste de materialização/reprodução periódico.

## 43. GAP ANALYSIS

Especialista perceberia rapidamente: claims/fontes não estão no pipeline; sucesso não é estado; output correto não é diferenciado de output concluído; não existe job genérico; learning ainda é intenção. Esses gaps têm prioridade sobre melhoria estética.

## 44. BREACH / BYPASS ANALYSIS

Qualquer operador pode executar FFmpeg direto, editar ASS, trocar WAV mantendo nome, usar -y, ou publicar sem registro. A solução é enforcement por manifest/validator/approval hash, não mais texto na spec.

## 45. INTERNAL CONFLICTS

- 60–70 s versus 58,36 s: resolver por regra específica do episódio, formalizar futuro.
- 7 cenas na spec versus 6 no código: registrar 6 como versão atual.
- “music not selected” versus bed executado: atualizar manifest.
- “audio not local” versus WAV local: atualizar status.
- “QC” versus revisão humana pendente: renomear para TECH_VALIDATED.

## 46. RED TEAM

Trocar o WAV mantendo o nome quebra captions e approval. Substituir scene-04 por frame errado passa ffprobe. Pronúncia errada de “newton” passa gate técnico. Conta/projeto errado pode consumir quota. Um processo interrompido pode deixar segmentos parciais e parecer válido se alguém abrir o arquivo anterior.

## 47. ADVERSARIAL TESTS

Testar: script vazio/enorme/alterado; WAV silencioso, curto, longo ou sample-rate errado; caption gap; frame ausente/errado; path de outro motor; output duplicado; FFmpeg interrompido; concorrência; 429; conta errada; input externo com instrução maliciosa; restart no meio do run.

## 48. PRE-MORTEM

As dez causas mais plausíveis: caption drift (alta/alto); claim sem fonte (média/crítico); publicação sem approval (média/alto); docs divergem (alta/médio); quota acaba (média/alto); visual genérico (alta/médio-alto); áudio mascarado (média/alto); overwrite perde versão (média/alto); API muda (média/alto); escala manual colapsa (alta/alto). Alertas e prevenção são os gates, SSOT, versioning e métricas acima.

## 49. EDGE CASES

Priorizar: nomes difíceis; retake de pronúncia; novo roteiro fora da duração; audio/visual mismatch; frame crítico com artefato; execução interrompida; storage cheio; arquivo com mesmo nome; approval de versão anterior; conteúdo web malicioso quando a pesquisa for adicionada.

## 50. COST / LATENCY / EFFICIENCY

Custo monetário efetivo não foi medido; AI Studio/Free Tier, compute e Library podem ser zero direto, mas quota/tempo são custo operacional. TTS/coleta manual é a etapa mais lenta. Frames independentes podem ser paralelizados depois de manifest/lock. Não paralelizar stages semanticamente dependentes.

## 51. SCALABILITY

10 runs: possível manualmente, já com drift. 100: não confiável sem fila/dedupe/storage. 1.000: impossível no desenho atual. 10.000: fora do objetivo. Não construir scale antes de três episódios estáveis.

## 52. WHAT TO REMOVE

Remover duplicidade de status e a construção de concat redundante/semântica em draft, mantendo apenas a parte canônica. Remover duration como fonte manual. Não adicionar dashboard, microservices, score cosmético, CTA, glitch ou abstrações sem uso.

## 53. WHAT TO FIX / 54. WHAT TO OPTIMIZE

Corrigir agora: claims/fontes; validator; approval hash; episode.json; duração derivada; docs coerentes; loudness/intelligibility.

Otimizar depois: ASR word-level; S01/S04 premium; cache por hash; paralelismo seguro; cleanup de intermediários.

## 55. WHAT TO ADD

episode.json; validate_episode.py; run_episode.py simples; claims/source manifest; JSONL log; state/approval record; golden tests; ASR adapter opcional; restore test; decision journal.

## 56. EVIDENCE REGISTER

| Achado | Evidência | Confiança | Impacto |
|---|---|---:|---:|
| MP4 válido | ffprobe: 1080x1920, 30 fps, 58,366667 s, H.264/AAC | Alta | positivo |
| WAV disponível | PCM 24 kHz mono, 58,36 s, hash | Alta | positivo |
| CLI testado | 4 unittest verdes | Alta | médio |
| captions não word-level | ASS/spec admitem limitação | Alta | alto |
| duration hardcoded | render_mars_final.py | Alta | alto |
| sem state/logs | inventory local | Alta | alto |
| docs stale | manifest/README versus execução | Alta | médio |
| claims sem lineage | TXT sem fontes/IDs | Alta | crítico |
| model ID atual | docs oficiais consultadas 2026-10-21 | Alta | médio |

## 57. PRIORITIZED CHANGESET

P0/CORRIGIR AGORA: claims/source gate; approval hash; validator técnico; boundary de paths.

P1/IMPLEMENTAR: episode.json; duração derivada; provenance do AI Studio; JSONL logs; idempotency; error classes.

P1/TESTAR: ASR word-level; phone QA; golden/regression/E2E.

P2/MONITORAR: assets premium e retenção.

P3/DEFERIR: queue, schedule, publishing/analytics automáticos.

## 58. AS-IS vs TO-BE

AS-IS: arquivos soltos, execução manual, duração duplicada, sucesso = FFmpeg terminou, revisão não vinculada.

TO-BE: episódio versionado, manifest único, claims rastreáveis, gates fail-closed, status persistente, logs, aprovação por hash, reexecução segura e feedback por coorte.

Delta mínimo: manifest + validator + approval + claims + duration derivada. Não exige reescrever renderizadores.

## 59. OPTIMIZED ARCHITECTURE

Content layer: script, claims, sources. Audio layer: Charon/TTS, provenance, idempotency. Visual layer: scene manifest/assets. Edit layer: captions, motion, mix. Validation layer: gates. Delivery layer: approval/publish futuro. Observability layer: run report/logs. Nenhuma camada escreve nos motores protegidos.

## 60. FINAL PIPELINE

NEW -> SCRIPT_VALIDATED -> FACTS_VALIDATED -> AUDIO_READY -> VISUAL_READY -> SYNC_VALIDATED -> RENDERED -> TECH_VALIDATED -> HUMAN_REVIEW -> APPROVED -> DELIVERED/PUBLISHED -> MEASURED -> LEARNING_REVIEW.

Falha em gate crítico = FAILED/BLOCKED, nunca SUCCESS.

## 61. CHANGESET MÍNIMO EFETIVO

1. episode.json para Mars;
2. validator fail-closed com streams, duração, não-silêncio, captions e scope;
3. claims/fontes + approval hash;
4. derivar duração do WAV/manifest;
5. alinhar README/spec/asset manifest.

## 62. TEST MATRIX

Unit: parser/validator. Contract: WAV/MP4/caption schema. Integration: TTS mock. E2E: script -> MP4. Regression: golden Mars. Acceptance: phone review. Adversarial: missing/silent/wrong file. Recovery: interrupted/restart. Security: key/path boundary. Load: 10 runs após estabilidade.

## 63. GOLDEN TEST SET

Normal Mars passa; WAV silencioso falha; script alterado após áudio falha hash; caption com gap falha sync; asset ausente falha visual; path de outro motor falha scope; rerun idêntico reutiliza/recusa duplicata.

## 64. REGRESSION PROTECTION

Proteger voz, duração, captions, safe zone, mix, resolução, ausência de CTA, isolamento e hash do output. Cada mudança precisa de teste, comparação de frames-chave e rollback para último APPROVED.

## 65. ROLLBACK PLAN

Trigger: qualquer gate crítico, claim corrigido ou mudança de modelo sem revalidação. Método: marcar versão REJECTED, preservar arquivos, selecionar último manifest APPROVED. Validação: ffprobe + gates + hash + revisão humana quando conteúdo mudou.

## 66. IMPLEMENTATION ROADMAP

Fase 0: claims, approval, validator, path boundary.  
Fase 1: SSOT, duração derivada, naming/docs.  
Fase 2: run dirs, idempotency, errors, checkpoint.  
Fase 3: ASR, loudness/phone QA, golden set.  
Fase 4: JSONL logs e freshness record.  
Fase 5: orchestrator/batch pequeno.  
Fase 6: cache/paralelismo/assets.  
Fase 7: scale/publishing apenas depois de estabilidade.

## 67. SECOND AUDIT

O TO-BE cria risco de overengineering se antecipar queue, dashboard, cloud DB ou publishing. Manifest e validator são necessários; queue não. ASR deve ser opcional até provar ganho. JSON deve ser operacional e Markdown explicativo; não manter duas fontes de verdade.

## 68. SIMPLIFICATION PASS

Não adicionar microserviços, banco externo, feature flags, múltiplos modelos, retries infinitos ou ranking de temas. Um diretório por episódio, um manifest, um validator e um relatório bastam agora.

## 69. REMAINING RISKS

Factualidade ainda depende de revisão humana; prosódia pode variar; AI Studio pode mudar; visual procedural pode ter retenção menor; word-level não foi provado; phone approval não foi evidenciada nesta auditoria; analytics inexistem; scratch não é produção permanente sem persistência.

## 70. DEFINITION OF DONE

APPROVED somente com claims/fontes; hashes ligados; WAV não silencioso; assets válidos; captions cobrindo transcript; loudness/peak/intelligibility; MP4 válido; scope protegido; report JSONL; revisão móvel registrada; approval hash exato; rollback disponível.

Motor só pode ser chamado OPERATIONAL AND GOOD após pelo menos três episódios completos e batch/recovery test. Hoje não chegou lá.

## 71. AUDIT COVERAGE CHECK

Objetivo, escopo, spec, implementação, regras, lineage, estado, decisões, IA, automação, dependências, falhas, segurança, observabilidade, qualidade, métricas, feedback, custo, performance, escala, testes, recovery, regression e change management foram cobertos. Quotas reais do projeto e analytics são UNKNOWN; ingestão web automatizada é N/A no desenho atual.

## 72. FINAL VERDICT

O motor funciona como bancada de produção de episódio e o primeiro Short está tecnicamente renderizado. Ainda não é motor robusto: faltam unidade versionada, gates que bloqueiem, rastreabilidade factual, estado, logs, recovery e aprendizado.

O próximo passo correto não é trocar Charon, adicionar efeitos ou tocar nos motores do GitHub. É aplicar o changeset mínimo: episode.json + claims/fontes + validator fail-closed + approval hash + duração derivada + documentação coerente. Implementar P1 antes do episódio 2; testar ASR/arte premium; só depois considerar escala.

### Evidência local principal

- MP4: H.264 1080x1920, 30 fps, 58,366667 s; AAC mono 24 kHz, 58,360000 s.
- WAV Charon: PCM s16le, 24 kHz mono, 58,36 s; SHA-256 6d2c704655287e85ee7b42d4c47ad0f99cbc062b307d13760688d4b98dfcca3c.
- Roteiro SHA-256: 87e0c2a3f7c18809362d8f6fed6374d1223fdb25ffa05b189f15fc5caa7e7fbe.
- Captions SHA-256: e856fe8c10bed0be320be0c65d2303aa99628384926ad31893e68bf745dbb3a4.
- Quatro testes unitários do CLI passaram.
- MP4 final, WAV e edit spec foram persistidos.

