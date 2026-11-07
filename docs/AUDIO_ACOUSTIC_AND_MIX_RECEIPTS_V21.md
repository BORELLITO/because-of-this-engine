# Because Of This — V2.1 • Detecção acústica e recibos verificáveis

**Status:** módulos técnicos implementados em branch isolada, com evidências e testes, sem liberar renderização ou publicação. O motor canônico mantém Gemini/Charon, identidade visual e `manual_only`.

## 1. Detector de músicas reutilizadas com arquivo alterado

`production/audio_acoustic_fingerprint_v21.py` utiliza FFmpeg/Chromaprint real para processar a mídia e comparar sequências de fingerprints. Suporta o mesmo fonograma com alterações usuais de volume, recodificação AAC/MP3 e cortes/deslocamentos.

No teste inicial real de mídia recuperada, um excerto de 17 segundos da trilha procedural repetida nos vídeos 002 e 004 foi recortado a partir de 19 segundos, teve volume reduzido para 30% e foi recodificado em AAC a 96 kb/s. A comparação com a faixa WAV original produziu **similaridade 0,99056**, acima do limite de reutilização `0,88`. A comparação contra a trilha procedural distinta do vídeo 001 ficou em `0,74740` — abaixo do limite de revisão `0,78`.

Critérios: `LIKELY_REUSE` (>=0,88) ou `REVIEW_REQUIRED` (>=0,78) bloqueiam o candidato para decisão automática; resultado abaixo desses limites significa apenas `NO_MATCH_IN_KNOWN_CATALOG`, não prova de originalidade mundial ou de licença. São exigidos pelo menos 64 quadros de fingerprint, com comparação de janelas de 96 quadros, tolerando deslocamento no tempo. `fingerprint()` invoca FFmpeg real com `-f chromaprint -fp_format raw -algorithm 1`.

O catálogo versionado `episodes/audio-acoustic-fingerprints-v21.json` começa com **duas fontes V7 de bytes verificados**, incluindo a trilha repetida SHA-256 `4a84629bdd611489b49f28187c70f2fc6d4a48b11347ef5c05cf301e1cd1fa24`. Os outros três fonogramas históricos conhecidos precisam ser incorporados com seus fingerprints reais antes de afirmar cobertura completa. Esta lacuna não vira PASS de direitos; a verificação de identidade SHA e os bloqueios globais de áudio permanecem em vigor. O motor nunca deve anunciar detecção de alterações de velocidade/pitch ou detecção de trechos arbitrariamente muito curtos sem testes específicos.

`production/audio_candidate_gate_v21.py` consulta esse detector para novos music beds e bloqueia sem o catálogo ou com resultado acústico ambíguo. Um PASS de fingerprint não libera renderização: `ready_for_render=false` permanece explícito.

## 2. Recibos de mixagem executada, sem reconfigurar o som

`production/audio_mix_receipt_v21.py` funciona como **adaptador da linha de comando FFmpeg já decidida pelo renderizador**, sem escolher um novo perfil de compressão/ducking/ganho. O wrapper:

1. Verifica a existência e os hashes SHA-256 dos stems declarados, com papéis `narration`, `music` e `sfx:<identidade>`.
2. Exige correspondência exata entre os `-i` reais no comando FFmpeg e os arquivos identificados. Não usa rede, pipes ou URLs como fontes de auditoria.
3. Executa o FFmpeg de verdade em diretório temporário, verifica a saída e a integridade dos arquivos de origem, registra o comando, hashes dos stems, stderr e hash da mixagem/PCM decodificado.
4. Uma verificação **independente** repete a execução dos mesmos stems/filtros e exige PCM idêntico.
5. Realiza uma **prova contrafactual por stem**: silencia cada fonte por vez, repete a mixagem e exige que o PCM final mude. Um SFX apenas declarado, mas que não participa do resultado, provoca bloqueio.
6. `verify_master_binding()` compara o áudio mixado comprovado ao áudio de um MP4 real via Chromaprint, calcula o SHA-256 do master e preserva `publication_authorized=false`.

Esse procedimento não é atestado jurídico nem prova de que um arquivo foi publicado. Recibos e resultados só são válidos para os bytes específicos e o perfil FFmpeg efetivamente executado. Um resultado de `verify_receipt(replay=False)` **não pode passar** por prova de mixagem reproduzida.

## 3. Integração preservando o motor canônico

O `production/render_v21_manual.py` expõe `validate_completed_audio_mix(record, receipt_path, master_video)` para a **fase pós-render de uma futura produção autorizada**. A função exige o mesmo episódio, recibo verificável, contribuição das fontes e correspondência com o master; um PASS nela não altera o `preview_enablement`, `production_enablement`, TTS ou publicação manual.

Importante: o motor V2.1 atual possui apenas **pré-voo de renderização, não um renderizador final ativo**. Portanto, o adaptador está disponível/testado, mas **não** é correto alegar que as próximas publicações já executarão os recibos automaticamente até que o renderizador de produção efetivamente o invoque e seus testes E2E passem. Não reativar pipelines V7 para isso.

## 4. Testes e próximos controles

As suítes exercitam FFmpeg e AAC reais em diretórios isolados, sem Gemini, TTS, Drive write, cobrança ou publicação. Casos críticos: trilha cortada/recodificada, fingerprint corrompido, arquivo faltante, mistura com e sem SFX, SFX declarado que não entra na mixagem, adulteração do arquivo, alteração do recibo, bloqueio de replay omitido, master MP4 não correspondente e recibo de episódio errado.

**Próximo passo técnico:** completar fingerprints dos três fonogramas históricos faltantes e, quando existir o novo renderizador ativo autorizado, tornar o wrapper pós-mix obrigatório antes de qualquer entrega externa, mantendo modo de publicação manual.
