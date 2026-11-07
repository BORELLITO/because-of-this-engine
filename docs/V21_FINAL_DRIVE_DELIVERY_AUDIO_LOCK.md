# BECAUSE OF THIS • V2.1 — Trava de entrega final com recibo de áudio

**Status inicial (07/11/2026):** contrato integrado ao adaptador de Drive com produção e envio final DESABILITADOS. Não houve qualquer renderização do canal, chamada Gemini TTS ou publicação nesta alteração.

## Problema detectado
O módulo `production/audio_mix_receipt_v21.py` já reproduzia a mixagem e verificava contribuição de narração, música e SFX, mas `production/google_drive_delivery.py` **não exigia essa prova** antes de enviar MP4s.

Um fluxo futuro poderia entregar um vídeo com som incorreto mesmo que o mecanismo de recibos existisse no repositório.

## Correção executada
`production/final_delivery_v21.py` passa a ser a barreira **obrigatória** para envio de qualquer vídeo MP4/MOV/MKV/WEBM/M4V/AVI via `google_drive_delivery.deliver()`. A checagem acontece **antes de abrir uma conexão Drive** e também vale para vídeos aninhados em pastas. A chamada direta `deliver()` não ignora a regra. Arquivos sem vídeo, como relatórios e backups de áudio, mantêm comportamento anterior.

Para uma entrega final, o motor exige conjuntamente:
- Um único MP4 real vinculado ao exato caminho do master submetido (nada de um arquivo diferente).
- Política V2.1 com `production_enablement=true` e `final_drive_delivery_enablement=true`; ambos permanecem **false** agora.
- `publication_policy=manual_only`, narração Gemini/Charon, record do mesmo episódio, `render_authorization=APPROVED`, `render_contract.render_executed=true`.
- Master verificável via FFprobe: **1080×1920, 60 fps, H.264, AAC 48kHz e 60–80s**.
- Quatro gates de segurança independentes em PASS: `AUDIO_HISTORY_COVERAGE`, `VISUAL_RIGHTS_CONSISTENCY`, `SCENE_DISCLOSURES_V21`, `RIGHTS_AUTONOMY_V21`.
- Recibo do áudio final reproduzido realmente por FFmpeg, com comparação contra o master, pelo menos stems `narration` e `music`, contribuição real medida e correspondência de episódio. SFX declarados são testados individualmente pelo mecanismo de recibos já implementado.

Esse controle **não faz** publicação no YouTube ou TikTok. O projeto V2.1 ainda não tem um renderizador final ativo: este upgrade fecha uma saída de entrega existente e prepara o handoff seguro de futuras renderizações autorizadas, sem invocar nenhum motor V7 arquivado.

## Testes
`tests/test_v21_final_delivery_gate.py` usa simulações controladas e não faz chamadas Drive. Inclui: ausência de recibo, política e registro inconsistentes, documento master errado, áudio sem música, falhas independentes de histórico/verdade, tipo de vídeo impróprio, pasta com MP4 escondido, upload direto de `deliver()` e caso positivo sintético com subsistemas isolados. A suíte `test_v21_audio_mix_receipt.py` já contém os testes reais de FFmpeg, replay e comparação com master AAC.

O CI principal executa uma prova negativa adicional: um MP4 não autorizado deve ser **rejeitado antes de `service()`**. O singleton `v21_singleton_guard.py` detecta remoção da conexão entre o adaptador Drive e a barreira.

## Limitações
- O gate impede **vídeos enviados pelo adaptador canônico `google_drive_delivery.deliver()`**. Ele não pode, sozinho, impedir upload por scripts externos, cliente Drive independente ou GitHub Actions `upload-artifact`. A rota de preview isolado é propositalmente separada e não é uma entrega final/publicação.
- O PASS da barreira pode autorizar uma transferência **somente quando a política de produção futura também estiver habilitada e as evidências reais estiverem completas**. A política atual é false.
- Master verificado por fingerprint acústico é uma evidência forte, não garantia ilimitada de ausência de toda falha perceptiva ou de direitos autorais.
- O histórico de SFX dos vídeos antigos permanece incompleto. A entrega final segue bloqueada por esse gate, além de `final_drive_delivery_enablement=false`.
- A publicação permanece manual. Qualquer mudança futura de política necessita auditoria e aprovação explícita para a nova fase operacional.

**Próximo passo:** criar o renderizador canônico V2.1 sob uma arquitetura única e autorizada, que execute a mixagem aprovada via `execute_with_receipt()` e entregue apenas após `validate_completed_audio_mix()` e o novo gate de entrega, sem trocar Charon, HUD, captions, clipes ou efeitos.
