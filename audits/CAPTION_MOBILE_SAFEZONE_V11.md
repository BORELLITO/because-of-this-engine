# BECAUSE OF THIS — Verificação de legendas e interfaces | Auditoria V1.1

Data: 2026-11-04. Branch candidata: `audit/v74-v11-hardening-20261104`. **Nenhuma alteração visual aprovada.**

## Controle visual preservado

O posicionamento já aprovado do canal permanece no perfil canônico: formato **1080 × 1920**, legendas `ASS` `alignment=2`, estilo `margin_l=90`, `margin_r=140`, `margin_v=408`, fonte Arial 48, karaoke `timestamp_color_transform` com vermelho-claro `#FF7777`. Não alteramos essas medidas nem a logo.

A margem registrada no manifesto sob `mobile_safe_zone.status=LOCKED_FROM_APPROVED_MASTER` prova apenas um compromisso de configuração, **não** que todas as interfaces de celular exibem a legenda sem sobreposição.

## Risco concreto e correção

Antes desta auditoria, `production/caption_quality.py` verificava somente a margem do estilo `Default` no arquivo ASS. Cada `Dialogue` podia especificar margens próprias, outro estilo, efeitos ou etiquetas como `\\pos`, `\\move`, `\\an`, `\\fs` e `\\clip` — capazes de escapar da área segura.

Correção implementada: o parser rejeita todas essas alternativas de geometria sem bloquear as transformações `\\t(...,\\1c...)` usadas pelo karaoke sincronizado. As legendas continuam exigindo transcrição exata e timestamps reais de Vosk para liberação final.

## Regra final G6 — TikTok e YouTube Shorts

O novo módulo `audits/mobile_caption_ui_v11.py` exige uma evidência humana de **cada plataforma** somente na fase de release final. Sem render e arquivos de legendas disponíveis, não pode retornar aprovação.

Contrato `rendered/caption-platform-ui-review-v11.json` (gerado somente quando a revisão real acontecer):
- video_id do episódio e SHA-256 dos bytes do vídeo final;
- SHA-256 dos bytes do ASS revisado;
- dois registros separados, `tiktok` e `youtube_shorts`, com status, responsável, dispositivo e data;
- duas capturas distintas do aplicativo real, com hash individual e imagem decodificável em resolução de smartphone.

O gate G6 bloqueia documentos ausentes, vídeos ou legendas alterados após a aprovação, provas de um único aplicativo, capturas reaproveitadas e arquivos inválidos. O parser de ASS também bloqueia comandos capazes de deslocar o texto.

**Importante:** esta é uma **atestação de revisão humana vinculada a arquivos**; ela não demonstra compatibilidade universal entre aparelhos, idiomas, configurações de acessibilidade ou atualizações das interfaces. Os testes usam imagens artificiais exclusivamente como fixtures e não substituem uma captura verdadeira.

## Fontes públicas consultadas

- TikTok for Business, informações sobre zonas seguras: https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads
- TikTok, guia de criativos verticais: https://ads.tiktok.com/business/pt-BR/guides/video-advertising-guide
- YouTube, edição e timeline de Shorts: https://support.google.com/youtube/answer/13380879?hl=pt-BR

Essas referências são indicativas, sobretudo quando descrevem interfaces de **anúncios**; não constituem coordenadas oficiais universais para publicações orgânicas do TikTok ou YouTube Shorts. O texto do vídeo também pode ser afetado pela legenda descritiva e botões de interação.

## Auditoria de execução

As mudanças ficam isoladas na PR #66: `production/caption_quality.py`, `production/quality_gates.py`, `audits/mobile_caption_ui_v11.py`, e testes sintéticos. Não houve render, postagem, mudança de estética, consumo de TTS, edição de MP4 histórico ou alteração da `main`.

**Status: G6 sintático e de integração testado; prova real no app para uma produção nova = PENDENTE.** Uma futura entrega final continua bloqueada até passar a verificação E5 e aprovação humana.
