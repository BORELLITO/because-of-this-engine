# BECAUSE OF THIS — QA técnico de loudness/true peak no master V2.1

**Auditoria:** 07/11/2026. **Estado:** motor canônico preservado; produção, upload Drive e publicação seguem desabilitados.

## Causa-raiz identificada no FFmpeg

O filtro FFmpeg alimiter aceita limit=0.95, mas a opção level (autoelevação de nível) é true por padrão. Portanto, usar apenas limit=0.95 NÃO garante margem final de pico, já que o filtro pode elevar automaticamente o resultado. Essa configuração estava presente duas vezes no grafo de mixagem V2.1.

Na primeira amostra de áudio de teste com o checkpoint Gemini TTS/Charon já aprovado para o episódio 005, os picos reconstruídos do MP3 chegaram a aproximadamente 0 dBFS, apesar da intenção de limitar. A amostra foi corrigida para usar level=0 explicitamente, preservando o ganho de música em 0,12 e os tempos do cartão.

## Correção

- production/render_v21_final.py passa a utilizar alimiter=limit=0.90:level=0 tanto no caminho da narração quanto no limite após amix. O perfil registra explicitamente esse headroom, sem trocar a identidade Charon, a seleção musical, o sidechain, os efeitos nem o outro/fade de 3,5 segundos.
- Após a montagem do MP4 com AAC, o renderizador executa FFmpeg EBU R128 com peak=true, extrai I (LUFS) e Peak (dBTP) do **arquivo do master terminado**, antes da promoção do candidato.
- O áudio final precisa ficar entre -20 e -13 LUFS integrados e pico verdadeiro no máximo -1 dBTP. Ausência de medição, silêncio, resultado fora da faixa ou saída suspeita resultam em BLOCKED.
- Os dados ficam no relatório da renderização sob finished_master_audio_qa. Isso é avaliação técnica, não certificação artística nem comprovação de ausência de conflito de direitos.

## Evidência real isolada

Um ensaio com o áudio Gemini/Charon 73,84 segundos do episódio 005, recuperado de artefato aprovado, foi mixado com uma textura sombria original gerada APENAS para teste, música a 0,12, sidechain controlado pela voz e fade-out durante o encerramento 5,5s. Resultado técnico no arquivo de teste:
- Duração ~79,3 segundos.
- EBU R128: -16,7 LUFS integrados, LRA 3,7 LU, true peak -3,9 dBFS.
- Música permanece na tela de créditos após o fim da narração e desaparece em fade de 3,5 segundos.
- Nenhuma sirene, alarme ou SFX de emergência foi acrescentado.

**Importante:** essa faixa é uma COMPOSIÇÃO SINTÉTICA TESTE, não a trilha original escolhida de Mixkit/Pixabay para liberação. O teste não resolve automaticamente licenciamento, histórico de SFX, direitos visuais, calibração perceptiva nem autorização de render.

## Regressões

tests/test_v21_final_render.py valida que o grafo desativa autoelevação do alimiter, recusa perfil adulterado, mede LUFS e pico verdadeiro no master de vídeo real sintético e continua validando presença de música no cartão final, fade, integridade do vídeo e ausência de sirenes.

**Próximo passo necessário:** obter e inspecionar mídia original licenciada de novas fontes, com dossiê verificável e avaliação auditiva, depois executar primeiro E2E canônico com fontes reais sob autorização separada. Não habilitar produção por causa de teste sintético verde.
