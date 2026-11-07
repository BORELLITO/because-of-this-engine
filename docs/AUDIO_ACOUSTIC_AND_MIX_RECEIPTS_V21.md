# Because Of This — V2.1 • Detecção acústica e recibos verificáveis

**Status:** módulos técnicos implementados em branch isolada, com evidências e testes, sem liberar renderização ou publicação. O motor canônico mantém Gemini/Charon, identidade visual e `manual_only`.

## 1. Detector de músicas reutilizadas com arquivo alterado

`production/audio_acoustic_fingerprint_v21.py` utiliza FFmpeg/Chromaprint real para processar a mídia e comparar sequências de fingerprints. Suporta o mesmo fonograma com alterações usuais de volume, recodificação AAC/MP3 e cortes/deslocamentos.

No teste inicial real de mídia recuperada, um excerto de 17 segundos da trilha procedural repetida nos vídeos 002 e 004 foi recortado a partir de 19 segundos, teve volume reduzido para 30% e foi recodificado em AAC a 96 kb/s. A comparação com a faixa WAV original produziu **similaridade 0,99056**, acima do limite de reutilização `0,88`. A comparação contra a trilha procedural distinta do vídeo 001 ficou em `0,74740` — abaixo do limite de revisão `0,78`.

Critérios: `LIKELY_REUSE` (>=0,88) ou `REVIEW_REQUIRED` (>=0,78) bloqueiam o candidato para decisão automática; resultado abaixo desses limites significa apenas `NO_MATCH_IN_KNOWN_CATALOG`, não prova de originalidade mundial ou de licença. São exigidos pelo menos 64 quadros de fingerprint, com comparação de janelas de 96 quadros, tolerando deslocamento no tempo. `fingerprint()` invoca FFmpeg real com `-f chromaprint -fp_format raw -algorithm 1`.

O catálogo versionado `episodes/audio-acoustic-fingerprints-v21.json` agora contém **as cinco fontes históricas únicas conhecidas**: duas fontes V7 preservadas e três MP3 históricos recuperados do Drive. Os arquivos foram conferidos pelo SHA-256 e os fingerprints completos são reproduzíveis via FFmpeg/Chromaprint. `catalog_coverage()` compara os hashes presentes no catálogo com os dos dois registros históricos antes de aceitar uma nova música. Isso completa a **cobertura documental das cinco fontes atualmente conhecidas**, não o histórico mundial de músicas ou direitos. A verificação de identidade SHA e os bloqueios globais de áudio permanecem em vigor. O motor não anuncia detecção confiável de alterações de velocidade/pitch ou de trechos arbitrariamente curtos sem testes específicos.

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

**Próximo passo técnico:** garantir que o adaptador de recibos de mixagem seja invocado obrigatoriamente por um renderizador V2.1 autorizado e executar testes E2E do master real. O catálogo acústico de cinco fontes já está completo para os registros conhecidos, mas a auditoria de efeitos, a liberação da produção e a publicação manual permanecem separadas.

## 5. Evidência de ampliação para as cinco fontes — 07/11/2026

Os MP3s originais **Fright Night (Mixkit), Echoes (Mixkit/Andrew Ev) e Suspense Tension Trailer 2 (DELOSound/Pixabay)** foram recuperados do Google Drive. Hash SHA-256 de cada arquivo verificado contra os manifestos históricos. Todas as fontes passaram na extração completa de Chromaprint. Em trechos separados de 17s, cortados aos 17s de cada MP3 e recodificados em AAC 96 kbps com volume a 35%, a similaridade de identificação foi, respectivamente, **95,2%, 97,7% e 96,2%**.

O arquivo `reports/AUDIO_ACOUSTIC_FIVE_SOURCE_QA_20261107.json` registra os hashes, identificadores do Drive, quantidade de quadros de fingerprint e escopo de evidência. Todos os cinco áudios decodificam seu próprio fingerprint; os dez pares de fontes distintas ficaram abaixo do limiar de reutilização de 0,88. A maior similaridade cruzada foi **0,77995**, muito próxima do limiar conservador de revisão 0,78. Isso justifica preservar o estado de revisão em casos ambíguos.

O contrato `catalog_coverage(repo_root)` compara as fontes conhecidas presentes em `episodes/audio-memory-registry.json` e `episodes/audio-rendered-master-registry.json` às assinaturas cadastradas; qualquer fonte histórica ausente bloqueia `audio_candidate_gate_v21.py`, mesmo que um novo arquivo pareça original. O contrato **não presume que fontes de manifestos antigos entraram nos masters posteriores V7**. Nenhuma mídia de terceiros foi copiada para o GitHub, apenas seus fingerprints técnicos. Publicação e renderização final continuam bloqueadas por controles independentes.
