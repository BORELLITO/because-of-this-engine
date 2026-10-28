# BECAUSE OF THIS — Motor v2 definitivo

Este é o único motor oficial do canal Because of This. Ele é independente do
Corte Fino, Rajada 011, CaptaPronto, Publisher e de todos os outros projetos.

## Motor canônico único — HARD LOCK

A configuração abaixo é a única autorizada para novas produções:

- **Perfil:** `because-of-this-v2-locked-2026-10`
- **Versão:** `2.0`
- **Fingerprint:** `c0af39cd3962415a29ab03687dacab9c432128abc892a72f7422095e0b56bf64`
- **Fonte única da verdade:** `production/canonical_config.py`
- **Rota oficial:** branch `main` → GitHub Actions → Google Drive

Todo manifesto precisa declarar exatamente o perfil e o fingerprint acima.
Qualquer configuração ausente, antiga ou divergente é bloqueada
automaticamente pelo contrato fail-closed e pelo CI. O manifesto histórico do
episódio 002 permanece apenas para auditoria e não é uma fonte alternativa de
produção.

## Arquitetura oficial

O pipeline v2 é exclusivamente baseado em vídeo:

1. A história e a narração definem o relógio principal.
2. O Cloud Browser pesquisa Mixkit, Pixabay e Pexels e cria uma fila de
   revisão.
3. O clipe exato e a licença são aprovados.
4. O arquivo aprovado é colocado no Google Drive.
5. O GitHub Actions baixa o asset, confirma que é vídeo, verifica o SHA-256 e
   renderiza com FFmpeg.
6. Legendas, verdade visual, reutilização e mídia final passam pelos gates.
7. O resultado validado é enviado ao Drive e a mídia temporária é removida do
   runner.

Imagens narrativas estáticas não são aceitas. Se o vídeo exato não estiver
disponível, o manifest precisa declarar um fallback semântico: NEAR,
EXPLANATORY, SYMBOLIC ou ATMOSPHERE. Preenchimento aleatório e fallback para
imagem são proibidos.

## Gates de qualidade

- Episódio entre 60 e 75 segundos.
- Formato 9:16: preview 1080×1920 ou final 2160×3840.
- H.264/AAC, 25 fps, faststart e nenhuma deformação.
- Duração das cenas travada na narração.
- Legendas ASS externas geradas a partir da narração final.
- HUD travada: Arial 48px, negrito, posição inferior central, outline 3px,
  sombra 1px e margens 100/100/320.
- Karaokê travado em timestamps reais por palavra: branco → vermelho de marca
  (#FF7777) durante a palavra → branco.
- Logo superior travado no centro em 540px; encerramento travado no logo
  transparente centralizado em 820px com fade suave. Fallback textual é proibido.
- Duas linhas no máximo, safe zone mobile e limite de CPS.
- Música de suspense licenciada abaixo da voz, com ducking e controle de
  loudness/true peak.
- Nenhum asset narrativo repetido no mesmo episódio.
- Nenhum clipe reutilizado entre episódios quando estiver PERMANENTLY_RETIRED.
- URL, licença, ID do Drive, SHA-256 e aprovação são obrigatórios.
- O relatório canônico G0–G12 é gerado em fases e não permite declarar produção completa com gate bloqueado.
- A QA técnica executa blackdetect, freezedetect e silencedetect; preto contínuo inesperado bloqueia a entrega e freeze/silêncio prolongado ficam registrados como alertas.

## Arquivos principais

- narrate.py: adaptador isolado de TTS Gemini.
- production/canonical_config.py: perfil único, fingerprint e bloqueio fail-closed.
- production/video_asset_research.py: fila de pesquisa e fallback semântico.
- production/google_drive_assets.py: ponte Drive para o runner.
- production/video_asset_contract.py: contrato v2 fail-closed.
- production/render_video_episode.py: renderizador FFmpeg determinístico.
- production/validate_video_release.py: gate final independente de mídia e legendas.
- production/quality_gates.py: matriz canônica G0–G12 por fase.
- production/media_anomaly.py: detecção técnica de preto, freeze e silêncio.
- production/pipeline_state.py: identidade estável do job e máquina de estados explícita.
- production/finalize_manifest.py: manifest final reproduzível e registro de cleanup.
- production/caption_quality.py: sincronização e legibilidade das legendas.
- production/google_drive_delivery.py: entrega verificada no Drive.
- examples/video-only-episode-manifest-v2.template.json: template de episódio.
- production/VIDEO_ENGINE_V2.md: contrato detalhado de produção.

## Verificações locais

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v
    python -m py_compile production/*.py

## GitHub Actions

- Video engine v2 CI executa compilação, regressão e testes de contrato.
- Render video-only episode v2 recebe um manifest v2 preenchido e oferece
  preview ou final.

O template possui placeholders de propósito. Um episódio real precisa receber
narração, legendas word-level, música licenciada, pesquisa verificada, IDs/checksums
dos vídeos aprovados no Drive e QA editorial humano antes do modo final.
O modo final é fail-closed enquanto esses gates não existirem.

O preview é somente validação: o recibo termina em `PREVIEW_COMPLETE` e nunca é uma publicação de produção. Apenas uma execução `final` com aprovação editorial humana pode chegar a `PRODUCTION_COMPLETE`.
