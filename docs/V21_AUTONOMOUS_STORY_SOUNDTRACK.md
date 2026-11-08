# BECAUSE OF THIS — Trilha sonora autônoma permanente (V2.1)

**Data:** 07/11/2026 · **Autoridade:** production/active_engine_policy.json,
production/audio_mix_profile_v21.json e production/render_v21_final.py.

## Regra artística permanente

**Todo vídeo terá uma trilha de fundo selecionada pelo próprio motor.** Cada
história tem seu tema, ritmo, mistério e carga emocional: a trilha NÃO será
fixa, reciclada nem escolhida manualmente pelo proprietário em cada vídeo.
A estética-base é suspense psicológico, dark ambient, drones graves e tensão
cinematográfica discreta. Seleção por adequação real à história e cobertura
legal por fonte, não por nome da faixa ou tendência.

**Proibido:** sirenes, alarmes, buzinas, jumpscares sonoros gratuitos, temas
com letra/voz que competem com Charon e mudanças abruptas que distorçam a
narrativa. SFX de ambiente são opcionais quando relevantes; a trilha é
obrigatória. Se não houver música elegível, o motor BLOQUEIA e procura novas
opções. Nunca substitui automaticamente a música por silêncio ou reutiliza
a trilha de outro episódio.

## Seleção verificável em dois estágios

1. **Aquisição/curadoria de candidatos:** um estágio anterior traz arquivos
originais, metadados reais e relatórios individuais de licença e conteúdo.
Fonte, criador, título, duração, uso em YouTube/TikTok, uso comercial e
possíveis direitos de terceiros/Content ID devem estar documentados. Mixkit
e Pixabay podem permitir uso em vídeo comercial sob termos próprios, mas
"royalty-free" não significa isento de direitos nem proteção contra
reivindicações automatizadas. Não inventar autorizações. Fontes oficiais:
https://mixkit.co/license/modal/musicFree/
e https://pixabay.com/service/terms/.
2. **Motor de escolha automática:** production/music_autoselect_v21.py
avalia todos os candidatos, confrontando fonte exata, SHA-256 do arquivo,
licença arquivada com hash, escopo do episódio e plataformas, QA por amostras
de áudio, ausência de sirenes/vocais, duração suficiente SEM LOOP, Chromaprint
contra as cinco trilhas históricas e compatibilidade com os tags de humor e
arco emocional da história. Apenas opções elegíveis são pontuadas;
empates são determinísticos. A escolha e alternativas rejeitadas são
registradas no relatório do episódio. A aprovação editorial individual
do usuário não é exigida.

**Limite real:** a capacidade de selecionar automaticamente **dentre mídias
já adquiridas e revisadas** está implementada; busca/ingestão autônoma dos
provedores e reconhecimento automático fim a fim de sons proibidos ainda não
fazem parte dessa rota. Evidências de licença/escuta precisam ser geradas por
uma etapa upstream confiável; um campo "license_verified=true" sozinho não
libera o arquivo. Sem essas evidências, bloquear corretamente.

## Sincronização com a narração e tela final

- A trilha entra em t=0 com fade-in de **0,4 s**.
- Ganho máximo inicial configurado: **0,12** (12% de multiplicador linear,
  não 12 dB nem garantia de loudness percetivo).
- Narração: **Gemini/Charon**, loudnorm alvo -16 LUFS. Música reduzida
  dinamicamente via **sidechaincompress** (threshold 0,02, ratio 3,
  ataque 12 ms, release 280 ms) durante a fala. Exigir posterior QA
  auditivo/métrico para confirmar inteligibilidade e equilíbrio.
- A música continua quando a voz acaba, cobrindo os **5,5 segundos do
  cartão final**. A fonte precisa ser suficientemente longa para todo o
  vídeo: não fazer loops perceptíveis, esticar ou acelerar a trilha.
- O cartão visual existente já faz fade-to-black nos **últimos 1,2 s**.
  O volume da música faz o mesmo fade nesses mesmos 1,2 s até a tela preta.
  A narração permanece silenciada na tela final; o vídeo visual é preservado.
- O caminho de prévia visual continua usando um cartão com áudio silencioso
  como **matéria-prima**. O master FINAL recebe a música contínua pela
  rota única production/render_v21_final.py; isso substitui a antiga regra
  da faixa musical terminar antes do outro, sem alterar os 16 clipes,
  HUD, legendas ou animação original.
- A música não é "acertada" apenas por valor numérico: os ganhos atuais
  são candidatos; o perfil mantém
  status=CANDIDATE_FOR_QA_NOT_RELEASE_APPROVED até escuta/QC independente.

## Travas, testes e limites de produção

production/active_engine_policy.json mantém production_enablement=false,
final_drive_delivery_enablement=false, publication_policy=manual_only e a
identidade Gemini/Charon aprovada.

Testes V2.1 verificam decisão por narrativa, recusa de sirenes e licença
insuficiente, SHA/Content ID e histórico repetido; validam gráfico FFmpeg
com sidechain, música durante tela final e fade medido de fato no WAV
sintético. Se a faixa não cobrir o vídeo até o fim, a execução falha.

O histórico audiovisual do projeto não muda automaticamente. A ingestão
de candidatas ainda precisa de evidências reais, e os gates de áudio/SFX e
direitos permanecem em vigor. A CI verde significa módulos e regressões
testados, **não um episódio já renderizado ou publicado**.
