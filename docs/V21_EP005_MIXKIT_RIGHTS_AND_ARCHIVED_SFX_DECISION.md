# BECAUSE OF THIS V2.1 — EP005: Mixkit, Content ID e áudio histórico

**Auditoria:** 08/11/2026 · **Custo adicional:** R$ 0 · **Ação:** auditoria somente leitura; sem TTS, upload, render final, publicação ou compra.

## Evidências confirmadas

1. O Mixkit lista **Silent Descent, de Eugenio Mininni**, duração aproximada 2:40, com tags *Film Score, Reflective, Melancholic, Piano, Strings, Cinematic, Melodic*. Fonte oficial: https://mixkit.co/free-stock-music/ e https://mixkit.co/free-stock-music/film-score/ .
2. A licença **Mixkit Stock Music Free License** permite incorporar a música em vídeos comerciais e publicações em redes sociais, sem pagamento; proíbe redistribuí-la como música isolada, entre outros usos restritos. Fonte oficial: https://mixkit.co/license/modal/musicFree/ . O Mixkit admite que podem ocorrer reivindicações de direitos e informa um canal de assistência.
3. O CI privado de 07/11/2026 utilizou o MP3 original do CDN Mixkit, SHA-256 **601955cacab6c38417687b144754c914f392f6508c35c241372695ad3987ec2b**, 160,418s. Comparou com as cinco trilhas históricas conhecidas: similaridade máxima 0,61751, sem coincidência pelo critério adotado. O teste misturou Charon pré-aprovado com a música (0,12), comprovou replay FFmpeg, contribuição da fonte, -17,0 LUFS, -1,2 dBTP e fade-out no cartão final. Fonte interna: reports/EP005_STOCK_MUSIC_SILENT_DESCENT_PRIVATE_QA_20261107.json ; workflow: https://github.com/BORELLITO/because-of-this-engine/actions/runs/42430775156 .

## O que NÃO está comprovado

- **Content ID:** a licença é uma autorização de uso, mas não garante que YouTube/TikTok não façam reivindicações. Não temos consulta ao estado de Content ID do nosso vídeo, certificado da plataforma ou histórico de resolução de alguma reivindicação. Estado: UNKNOWN_NOT_CHECKED_ON_DESTINATION_PLATFORM. Não inventar status CLEARED nem assegurar monetização.
- **Adaptação narrativa:** os metadados oficiais indicam música melancólica/reflexiva; a história de Stanislav Petrov requer suspense histórico/investigativo. O bom resultado técnico do mix não comprova que a faixa seja a melhor escolha. Estado: PENDING_INDEPENDENT_STORY_FIT. O motor continua responsável pela decisão, mas precisa de evidência de escuta/editorial, não de aprovação manual repetida pelo proprietário.
- **SFX históricos:** os quatro registros de masters V7/V2 antigos possuem vídeo e fonte musical identificados, mas sfx_tracks_verified=0 e historical_sfx_coverage=UNKNOWN. Nenhum registro é prova de que os vídeos não tinham efeitos; apenas não existe verificação por stem. Além disso, a fonte musical procedural SHA 4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24 foi reutilizada entre dois masters históricos (002 e 004), comprovado por hashes. Essas mídias permanecem em quarentena para futuros reusos e nenhuma declaração retroativa é feita.
- A própria produção V2.1 continua desabilitada; a trilha não é um áudio final publicado.

## Correção operacional incorporada

O arquivo episodes/episode-005/music-clearance-v21.json registra individualmente fonte, licença, SHA, CI, histórico, tags oficiais, risco Content ID e aprovação criativa PENDENTE. O módulo production/soundtrack_release_evidence_v21.py cruza esse dossiê com o relatório do Mixkit e com o registro INDEPENDENTE dos quatro masters antigos, produzindo vereditos distintos; não baixa nada e nunca afirma aprovação na ausência de prova.

O pré-voo FINAL em production/render_v21_manual.py agora exige esse gate adicional. Prévia de áudio e visual permanece separada, com a possibilidade de análise sem liberação. O singleton e a suíte CI denunciam a exclusão dessa proteção. Testes adversariais: URL de licença falsa, fonte SHA adulterada, inventar Content ID resolvido sem artefato, credenciais/outro episódio e fingir SFX históricos completos.

**Resultado esperado agora:** licença Mixkit para vídeo = CONFIRMADA; original e QA técnico = CONFIRMADOS; Content ID = PENDENTE; adequação narrativa = PENDENTE; histórico SFX = NÃO COMPROVADO; release = BLOCKED. Não iniciar gastos, TTS, render final, upload ou publicação.

**Próximo passo responsável:** o motor pesquisar uma alternativa musical verdadeiramente investigativa, obter original gratuito com licença rastreável, escutar/comparar com Charon e montar dossiê de direitos; em paralelo, recuperar recibos reais dos masters antigos se existirem. Sem prova de Content ID, reconhecer risco em vez de inventar imunidade.
