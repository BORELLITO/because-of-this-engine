# BECAUSE OF THIS — Motor oficial V7.1 Piper + melhorias V7.2 Reuse First

Este é o **único motor oficial** de produção do canal. O núcleo canônico V7.1 permanece com o modelo de voz **Piper TTS local**, em inglês. A **V7.2 Reuse First** foi aprovada e ativada como uma camada de economia, segurança, memória de mídias e validação incremental, sem substituir a voz, o roteiro ou a estética validados.

## Estado e autoridade

- Branch oficial: `main`. Apenas o código desta branch pode executar produção canônica.
- Política ativa: `production/active_engine_policy.json`: `active_engine_version=7.1`, `active_addon_version=7.2`.
- Perfil de voz: `because-of-this-v7-piper-tts-2026-10`, `en_US-ryan-high`, local, mono 24 kHz PCM. **Sem Google Cloud TTS, Edge TTS ou fallback automático.**
- Publicação **sempre manual**. Nenhum preview técnico, relatório ou cache autoriza postagem.
- Material histórico de outros projetos (Corte Fino, Rajada, CaptaPronto) não tem rota de execução para este motor.

## Vídeo 001 — preview já entregue e preservado

Título: **The Elevator That Stopped on a Floor That Didn't Exist**.

- Execução bem-sucedida do núcleo Piper: https://github.com/BORELLITO/because-of-this-engine/actions/runs/40986385249
- MP4 existente: https://drive.google.com/file/d/1C3mkxkKy1uZh8pBKlDOmaaRr4Gk_DDVR/view
- WAV de narração existente: https://drive.google.com/file/d/1fFI8b5RzDq3qu_T44lEh-BHCqIHl4ttH/view
- Pasta completa com relatórios e manifesto: https://drive.google.com/drive/folders/1HkjYfLf4vXJuJ1XjE-pQWVdjPGho6NDh

A V7.2 **não criou outro MP4 nem regravou a voz**. Ela compara a assinatura exata do roteiro, manifesto e código produtor de mídia com o registro da entrega. Também compara os 9 recibos de Drive (nome, tamanho, MD5) antes de indicar reutilização. Esses metadados não substituem a conferência dos bytes e a revisão editorial para o lançamento.

## Arquitetura vigente

1. **Roteiro e intenção visual.** O motor organiza cenas, âncoras narrativas e material licenciado antes do processamento.
2. **Piper TTS / cache inteligente.** O cache reconhece roteiro, trechos narrados, pronúncia, parâmetros de voz, configuração e SHA-256 do modelo real. WAV fora de 60–75 segundos, com checksum ou perfil divergente, não pode ser reutilizado.
3. **Legenda a partir do áudio final.** Vosk gera timestamps reais. Legendas karaoke ficam sincronizadas com a voz; não aceitar estimativas inventadas.
4. **Materiais de Drive.** Cada clipe tem ID, origem, direitos, SHA-256 e identidade visual. Fonte inteira consumida **não pode aparecer em outros episódios**, mesmo se foi usada numa história arquivada ou recortada de outra forma.
5. **Músicas e efeitos.** Trilhas completas não podem ser repetidas entre histórias; histórico antigo conta. A semelhança acústica e o intervalo mínimo de reutilização dos efeitos ainda exigem verificações específicas e não são presumidos a partir da igualdade do nome.
6. **FFmpeg e gates.** Saída 1080×1920, 60 fps, 60–75 segundos; narrativa, suspense, logo, transições e legenda conforme o perfil canônico. Validação de reutilização e proveniência agora depende de auditorias reais, não de marcadores estáticos.
7. **Reutilizar antes de produzir.** Ao iniciar o episódio 001 com roteiro, manifesto e código idênticos, o preview original pode ser reconhecido e sua produção é pulada. Para episódios diferentes, a política de não repetir clipes prevalece.
8. **Entrega e publicação.** O Drive guarda os resultados; previews são candidatos e nunca equivalem à aprovação editorial. Publicação somente após aprovação humana e validação de licença.

## Controles operacionais

- `.github/workflows/draft-preview.yml`: preview manual e verificação do episódio 001 antes de qualquer síntese/re-render; não publicar.
- `.github/workflows/because-of-this-v7.yml`: produção manual canônica; restaura cache Piper válido ou gera apenas áudio ausente e arquiva a narração resultante para futuros reinícios.
- Ambos usam **uma trava de concorrência compartilhada** para evitar execução de mídia simultânea.
- `.github/workflows/video-engine-ci.yml`: valida a V7.1 e os novos componentes V7.2 automaticamente, **sem renderização ou voz gerada**.
- `experimental/v72/`: inclui verificações auxiliares, incluindo avaliador opcional do WhisperX. **A instalação do WhisperX não é obrigatória** e não troca o Vosk aprovado.

## Limitações explicitamente mantidas

- O modelo de voz `en_US-ryan-high` requer avaliação documental de licença adequada a conteúdo monetizado antes de divulgação comercial. A existência do modelo não prova autorização de qualquer uso.
- O primeiro MP4 foi entregue como `DRAFT_PREVIEW_ONLY`: sua finalização/publicação depende de revisão e aprovação editorial.
- Restauração e retomada do fluxo novo foram cobertas por testes de unidade/contrato, mas **ainda não houve uma segunda produção audiovisual ponta a ponta** com a V7.2. Não acionar processamento pesado só para provar economia.
- Os arquivos ASS/alinhamento **não** estavam no pacote anterior; os workflows atualizados passam a entregá-los nas produções futuras.
- Sem regras de proteção de branch garantidas por API: permissões do GitHub devem ser configuradas na plataforma caso se deseje obrigatoriedade de PR.

## Diagnóstico sem gastar créditos

```bash
PYTHONPATH=. python -m unittest discover -s tests -p 'test_v7*.py' -v
PYTHONPATH=. python -m unittest -v tests.test_reuse_first_v72 tests.test_asset_reuse_brain tests.test_audio_reuse_v72 tests.test_narration_cache
PYTHONPATH=. python experimental/v72/reuse_first.py \
  --manifest episodes/video-001/preview-manifest.json \
  --script episodes/video-001/script.txt \
  --catalog experimental/v72/verified_preview_001.json \
  --report /tmp/reuse-plan-001.json
```

**Princípio permanente:** evitar retrabalho, mas nunca reutilizar um arquivo de outra história, com direitos desconhecidos, alterado ou incompatível.
