# BECAUSE OF THIS — Integração E2E de segurança da V7.4 | 04/11/2026

**Ambiente:** branch experimental `audit/v74-v11-hardening-20261104`, PR #66 draft. **NÃO** é teste de renderização de um episódio completo, nem prova de publicação, licença, TTS ou compatibilidade de todos os aparelhos. Todos os ataques usam arquivos descartáveis e identidades inventadas.

## O que foi efetivamente executado

- **19 cenários de ataque integrados** no arquivo `audits/tests/test_e2e_fail_closed_v11.py`.
- Exercita o avaliador real `production/quality_gates.evaluate`, a memória real de **clipes** e **trilhas**, e os contratos reais de procedência, aprovação humana e fechamento.
- Somente as fronteiras externas caras e sem objeto real (perfil canônico completo, auditoria editorial, inspeção de codec no fixture não-vídeo, alinhamento de palavras, empacotamento e revisão da interface real) são substituídas por mocks **declarados**. Portanto o teste **não é E2E físico de geração e distribuição**.
- Nenhum Drive write, Gemini call, FFmpeg render de episódio, upload ou publicação.

## Brechas encontradas e corrigidas

1. **G2 sempre bloqueava mesmo em caso válido:** `_provenance` emitia `PASS: ...`, mas o controlador comparava `== "PASS"`. Foi normalizado para status e explicação separados.
2. **G2 aceitava afirmação unilateral de licença como se fosse verificação:** no modo final agora exige registro humano vinculando `source_page_url`, SHA-256 de mídia, `evidence_url`, revisor, data e autorização declarada para **YouTube e TikTok**. Isto é somente **atestação estrutural**; a validade da licença ainda precisa ser verificada de fato na produção nova.
3. **G8/G9 confiavam em JSON de release sem MP4 correspondente:** agora conferem MP4 existente, SHA-256 dos bytes reais, vídeo 1080×1920 60fps 60–80 s com áudio e a coerência dos dados do relatório via `ffprobe`. G8 também exige identificação, data e hash de aprovação da prévia exatamente para o vídeo final.
4. **G11 aceitava recibo autodeclarado como publicação concluída:** agora um JSON `PASS` é no máximo `DEFERRED`; a comprovação da URL e do vídeo publicado requer verificação externa posterior. Não marca `publication_verified=True` nem `COMPLETE` apenas por recibo.
5. **`next_action` ignorava gates bloqueados:** agora lista os códigos ainda bloqueados antes de orientar publicação ou encerramento. Reporta `release_readiness` separadamente.

## Matriz de tentativas controladas

| Ataque/situação | Resultado exigido |
|---|---|
| Fixture tecnicamente íntegro com aprovação estrutural simulada | Só `READY_FOR_MANUAL_PUBLICATION`, jamais `publication_verified` |
| Direitos sem revisão; só YouTube; digest da prova divergente | G2 BLOCKED |
| Clipe que já apareceu em outro episódio | G3 BLOCKED |
| Música com o mesmo SHA sob outro `track_id`; ausência de registro; hash falso | G5 BLOCKED |
| Sem prova real de interface TikTok/Shorts | G6 BLOCKED |
| Render final ausente ou alterado após validação; métricas reais inválidas | G8/G9 BLOCKED |
| Aprovação de prévia com SHA diferente | G8 BLOCKED |
| Revisão editorial humana ausente | G10 BLOCKED |
| Recibo fictício autoaprovado | G11 DEFERRED, sem conclusão |
| Recibo de postagem incompleto | G11 BLOCKED |
| Várias falhas simultâneas | `RESOLVE_GATES` com todos os códigos pendentes |
| Somente leitura | Nenhum arquivo de fixture modificado |

## Evidências verificáveis

- **CI integrada:** https://github.com/BORELLITO/because-of-this-engine/actions/runs/41930008415
- **Resultado da CI:** 113 testes de auditoria `PASS`; 19 dos 113 repetidos em step E2E separado `PASS`; 9 testes legados ativos `PASS`. **122 casos distintos**, não 141.
- **Histórico/rememória de mídia:** https://github.com/BORELLITO/because-of-this-engine/actions/runs/41930008357
- **Controle reuse-first:** https://github.com/BORELLITO/because-of-this-engine/actions/runs/41930008183
- Não confundir o **`REUSE_AUDIT=ASSET_REUSE_PASS`** do episódio histórico específico conferido pelo CI com certificação de todas as mídias já usadas.

## Resultado e limites

**Integração testada = PASS para cenários sintéticos de gates G2, G3, G5, G6, G8, G9, G10 e G11.** A V7.4 de produção real continua **NÃO LIBERADA**. Não foi demonstrada correspondência multimodal do novo episódio, seleção de materiais novos licenciados, verificação individual de direitos de terceiros, validação acústica de TTS, render real de 60–80 s nem exibição real no TikTok/Shorts.

**Próximo passo único:** produzir **apenas proposta editorial original** (roteiro, mapa emocional e storyboard 12–18 cenas), em inglês para público americano; apresentar para aprovação antes de qualquer TTS, busca/download de clipes para publicação, render ou merge. Nenhuma modificação em One Extra Minute.
