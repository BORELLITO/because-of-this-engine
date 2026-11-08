# V2.1 — Proteção da trilha musical e SFX (após PR #140)

**Estado:** endurecimento do ÚNICO seletor canônico production/music_direction_v21.py. O PR #141 foi fechado sem merge para evitar a duplicação de motores. A direção musical do PR #140 continua intacta: suspense psicológico adequado à história, voz Gemini/Charon prioritária, volume candidato 0,12, sidechain, música contínua durante o encerramento e fade-out final.

## Direitos e identidade do áudio

Antes de classificar uma faixa, o seletor exige o arquivo de áudio original local com SHA-256 confirmado e um dossiê individual cuja integridade também é conferida por SHA-256. O dossiê precisa vincular o mesmo episódio, fonte, autor/revisão pelo motor, URL oficial do item Mixkit/Pixabay, licença oficial do provedor, autorização documentada para vídeo comercial em YouTube Shorts e TikTok, restrição a distribuição da faixa isolada, análise de terceiros e situação conhecida de Content ID. URL HTTPS arbitrária ou checkbox "license_verified" NÃO basta.

Fontes oficiais: https://mixkit.co/license/modal/musicFree/ e https://pixabay.com/service/terms/ e https://pixabay.com/service/faq/. Uma faixa gratuita sob licença continua protegida por direitos autorais e pode sofrer reivindicação de Content ID. O dossiê é prova arquivada de revisão, não imunidade jurídica universal. A busca/download e criação desses dossiês precisam de uma etapa upstream confiável; não alegar ingestão online autônoma completa neste estágio.

## Música que acompanha toda a história e o encerramento

O seletor recusa músicas com duração insuficiente para cobrir todo o master, e o renderizador confere a duração original por FFprobe. A opção de repetir automaticamente um áudio curtinho em loop foi retirada. O motor confere que a faixa realmente escolhida corresponde a título/ID, SHA-256, URL de origem e hash do dossiê que passaram na pontuação. A escolha e as rejeições ficam registradas no relatório do episódio.

O PR #140 já implementou a música desde o início, sidechain controlado pela voz Charon, ganho máximo candidato 0,12 e fade-out de 3,5 segundos que termina com o cartão visual totalmente preto. Este upgrade PRESERVA esses valores e a duração visual de 5,5 segundos. A mixagem precisa de escuta de QA para comprovar o equilíbrio real.

## Efeitos — nenhuma sirene

Sirenes, alarmes, buzinas e klaxon são proibidos também nos SFX separados. Sons ambientes contextuais continuam possíveis com fonte, licença e timing comprovados. Se a história funcionar melhor somente com a trilha de suspense, o manifesto de QA pode autorizar ausência de SFX sob o estado QA_VERIFIED_NO_SFX_REQUIRED com story_sound_design AMBIENT_MUSIC_ONLY. Isso não ignora o gate de histórico SFX nem habilita produção.

## Validação e limites

Testes garantem recusa de domínios falsos, arquivo de licença adulterado, Content ID incerto, arquivo original diferente, QA insuficiente, vocal/sirene, música curta e seleção não correspondente à fonte usada. A mixagem FFmpeg sintética comprova música audível durante o cartão final e queda de intensidade até o preto. O estado canônico de produção, upload Drive e publicação permanece bloqueado/manual. A entrada de novas candidatas ainda depende de aquisição e inspeção com evidência real.
