# BECAUSE OF THIS V2.1 — EP005: Selpan ativa, triagem sonora e rastreabilidade

**Data:** 08/11/2026. **Custo adicional:** zero. **Travas:** produção e Drive final desabilitados; publicação manual, Gemini/Charon original intacto.

## Decisão editorial sem criar segundo motor

O comparativo real já existente entre **Selpan** e **Delirium** (Mixkit, Eugenio Mininni) registrou Selpan como a melhor opção *pelos metadados de investigação/documentário*. A execução GitHub Actions 42494029735 utilizou os MP3s originais e a voz Charon aprovada, sem nova chamada TTS. Selpan: SHA-256 **3d46ec4a1572e00a7da4b3e697067c7cbb07331bc5837758985ff95eda858267**, 193,646s, sem match acima do limite contra as cinco músicas históricas conhecidas; mixagem MP3 79,32s, −17 LUFS, −1,2 dBTP, música no cartão com fade 3,5s. O relatório é `reports/EP005_MIXKIT_INVESTIGATIVE_HEAD_TO_HEAD_QA_20261108.json`.

A seleção atual em `episodes/episode-005/music-clearance-v21.json` foi atualizada de Silent Descent para Selpan **somente como candidata de QA**, com a fonte original e vínculo ao relatório de teste. O histórico documental de Silent Descent foi preservado *literalmente* no arquivo `episodes/episode-005/music-clearance-silent-descent-archive-v21.json`.

A licença oficial <https://mixkit.co/license/modal/musicFree/> autoriza uso em vídeo comercial e redes sociais sem pagamento, porém prevê possibilidade de reivindicação. Não garante imunidade de Content ID; nenhuma comprovação de resultado no YouTube/TikTok foi obtida.

## Auditoria adicional de conteúdo real

O novo script `production/music_content_screen_v21.py` realiza triagem **somente leitura** do arquivo original via FFmpeg e STFT (NumPy/SciPy instalados gratuitamente no runner público), calcula envelopes de energia, identifica **candidatos** a variações tonais semelhantes a sirenes e transientes bruscos, e fornece estimativa conservadora de competição música/voz com o Charon original.

A detecção de variações tonais pode marcar instrumentos musicais como falso positivo. **Um resultado negativo jamais equivale a ausência comprovada de sirenes, vozes, alarmes ou mascaramento após compressão e mixagem.** O resultado não aprova direitos, Content ID, escuta artística nem publicação. O workflow `.github/workflows/episode005-selpan-source-screen-v21.yml` baixa temporariamente o MP3 exato SHA e reutiliza o artefato de voz aprovada, apaga ambos antes de enviar apenas um JSON de medições, com retenção limitada a sete dias.

## Controles e estado

O gate de release existente `production/soundtrack_release_evidence_v21.py` passou a comparar a fonte selecionada com o **relatório head-to-head real** e exige verificação de conteúdo independente; mantém compatibilidade histórica com o formato antigo de relatório de uma só música. O singleton denuncia remoção da auditoria de fonte. Regressões verificam oscilação sintética semelhante a sirene (sinalizada), drone uniforme (não sinalizado, mas não certificado), manipulação de Content ID e áudio trocado.

**Status pretendido após CI:** Selpan é a candidata técnica mais alinhada e possui licença para vídeo comercial; **NOT_APPROVED_FOR_RELEASE** até conclusão real de escuta, avaliação de conteúdo da fonte e voz, situação Content ID e direitos de imagens/SFX. O bloqueio não é contornado pelo resultado da triagem. Nenhuma trilha original de terceiros é incorporada ao GitHub.

**Única próxima tarefa de desbloqueio:** analisar os intervalos sinalizados pelo detector com escuta independente, conferir correspondência emocional com o episódio e obter evidência de reivindicações no destino; manter custo adicional zero e evitar publicar por engano.
