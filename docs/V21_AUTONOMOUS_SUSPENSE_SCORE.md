# BECAUSE OF THIS V2.1 — trilha de suspense autônoma obrigatória

**Decisão editorial:** cada episódio final deve ter uma trilha de suspense cinematográfico escolhida pelo motor de acordo com o gênero e a progressão emocional da história. Sem sirenes, alarmes, buzinas, sustos gratuitos ou efeitos de emergência. Efeitos sonoros pontuais permanecem em canal separado e somente quando coerentes com o roteiro.

## Seleção por episódio

`production/music_direction_v21.py` recebe contexto da história e candidatos musicais, ordena estilos por gênero (mistério histórico, horror psicológico, tragédia humana, história real, sobrenatural), prefere arranjos esparsos e baixa variação dinâmica, exclui alarmes/sirenes e rejeita qualquer candidato sem evidência individual de licença, uso comercial, permissão de edição, risco de Content ID, arquivo local e unicidade acústica. A seleção editorial é automática; a verificação real dos bytes, SHA-256, Chromaprint e histórico permanece obrigatória via `audio_candidate_gate_v21.check_file`. Um rótulo 'royalty-free' **não** é garantia de ausência de direitos autorais ou reivindicações. Se nenhuma fonte for comprovada, BLOQUEAR, nunca improvisar música sem licença.

O renderizador exige contexto e catálogo de candidatos como argumentos `--story-music-context` e `--soundtrack-candidates`. A faixa fornecida em `--music-candidate` precisa ser a mesma escolhida pelo motor. A pesquisa/obtenção automática de novas músicas na internet **não** está implementada neste upgrade: o motor escolhe automaticamente entre candidatos auditados e disponibilizados. Não marcar sourcing externo como concluído.

## Mixagem, sincronismo e encerramento

A música começa no tempo 0 e percorre todo o vídeo até a tela preta do outro, não apenas até o fim da narração. `production/render_v21_final.py` utiliza a trilha em loop quando necessário, limita o áudio ao comprimento real da imagem, aplica `sidechaincompress` usando a voz como referência (ducking dinâmico) e um `afade` de 3,5 segundos encerrado exatamente no último frame. A voz termina no seu tempo próprio; a música continua durante o outro, reduzindo gradualmente até silêncio. O ganho linear inicial é 0,12, **não significa 12% de loudness percebida**. A voz permanece com alvo -16 LUFS; limite de pico do mix permanece protegido. Música e efeitos ainda são candidatos à escuta e não receberam aprovação perceptiva. Não cortar/alterar a voz ou imagens aprovadas.

Os testes reais FFmpeg do renderizador e testes de seleção devem provar a cadeia; a aprovação final também requer medição de volume/escuta do master. O status `CANDIDATE_FOR_QA_NOT_RELEASE_APPROVED` e `production_enablement=false` são mantidos.

**Pendências:** disponibilização de faixas verificadas, avaliação de Content ID, comprovação de direitos por faixa, histórico SFX e escuta da mixagem real. Não gerar novo episódio ou publicar automaticamente.
