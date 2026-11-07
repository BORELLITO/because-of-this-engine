# BECAUSE OF THIS — Renderizador final canônico V2.1

**Status em 07/11/2026:** rota de código implementada, produção e publicação DESABILITADAS. Não houve geração de voz, render de episódio ou upload externo. O perfil musical é **CANDIDATO**, não aprovado perceptivamente.

## Por que reaproveitar a prévia

O renderizador de prévia V2.1 já monta 16 cenas, avisos de representação histórica, enquadramentos, correções visuais, logo, legendas karaoke e encerramento. Recriar essa montagem arriscaria as regras aprovadas. A nova rota em production/render_v21_final.py utiliza o STREAM DE VÍDEO do arquivo de prévia com FFmpeg -c:v copy, sem reprocessar cenas/HUD/captions, e troca apenas o áudio após a mixagem real.

## Pipeline obrigatório, em ordem

1. Executar production/render_v21_manual.validate_request(mode="final") ANTES de acessar qualquer mídia. Hoje bloqueado pelo production_enablement=false e histórico de SFX incompleto.
2. Validar relatório e SHA-256 do MP4 prévio, 16 cenas, continuidade, identidade cinematográfica cinematic_dread_v73, posição das legendas, marca e tela final silenciosa. Validar original Gemini/Charon por voz, modelo e hash WAV.
3. Validar música inédita com SHA-256 real e Chromaprint contra as cinco fontes conhecidas. Prova de licença e aprovação editorial por episódio são necessárias independentemente.
4. Receber efeitos nomeados sfx:<id> pré-temporizados e com direitos e sincronização comprovados em manifesto do episódio; não improvisar timing.
5. Gerar mix.wav e recibo via production/audio_mix_receipt_v21.execute_with_receipt. Reproduzir comando FFmpeg, conferir hashes, PCM resultante e contrafactuais por fonte para garantir participação da narração, música e efeitos.
6. Remuxar o STREAM VISUAL original para master H264/AAC, sem alteração estética. Comparar hash do stream de vídeo da prévia e do final. Comparar áudio do master com mix verificado via postflight; só então promover o arquivo final local.
7. Transferência ao Drive continua separada, com final_drive_delivery_enablement=false e gate próprio. Publicação sempre manual. Sem qualquer chamada de TTS.

## Perfil de áudio — não inventar aprovação

production/audio_mix_profile_v21.json é PROPOSTA para calibração e escuta independente: preserva Charon, loudnorm -16 LUFS, pico -1 dBTP, música a 0.12, SFX a 0.08, limiter 0.95 e outro silencioso de 5.5 s. Os ganhos de música/efeitos AINDA NÃO FORAM aprovados auditivamente. O código exige INDEPENDENT_AUDIO_QA_PASS antes do render real. Se narração + outro exceder 80s, o motor BLOQUEIA em vez de cortar ou acelerar a fala.

## Testes e limites

tests/test_v21_final_render.py: contrato de perfil, preflight real ainda bloqueado, SFX e relatório adulterado, execução FFmpeg REAL com vídeo sintético e stems sintéticos, replay, contrafactuais, master AAC e identidade de bitstream visual. Na simulação curta (14s + 5.5s), só o limite temporal é substituído isoladamente para economizar CI; não equivale a um master real 1080x1920 60fps nem a julgamento artístico. A trava de entrega real continua exigindo 60–80s, 1080x1920, H264 60 fps e AAC 48 kHz.

O áudio histórico ainda contém reutilização 002/004 e cobertura SFX incompleta, por isso AUDIO_HISTORY_COVERAGE segue BLOQUEADO. O report da prévia amarra seu SHA, mas não é assinatura criptográfica externa independente; arquivos deverão vir de execução CI rastreável. Esta rota não utiliza motor V7, não mexe em vídeos aprovados, não ativa publicação, não faz upload nem consome Gemini.

**Próxima prioridade:** calibrar o áudio com preview real em ambiente isolado, validar o histórico dos efeitos e o perfil perceptivo, depois habilitar autorização específica do render final canônico com testes 1080x1920/60fps e entrega somente manual.
