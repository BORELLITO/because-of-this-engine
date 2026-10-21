# Revisão pós-upgrades — BECAUSE OF THIS

Data: 2026-10-21  
Escopo: somente o motor independente e o episódio Mars Climate Orbiter 001.

## Alterações implementadas

1. Unificada a narrativa longa, já presente nas captions, como transcript canônico em `examples/mars_climate_orbiter.txt`.
2. Recalculados os hashes do transcript, provenance e manifest.
3. Claims ampliados para cinco fatos verificados e uma inferência editorial explicitamente classificada.
4. Validator v2 criado com:
   - identidade textual transcript→captions;
   - vínculo por hash entre script, captions e provenance;
   - validação de WAV 24 kHz mono 16-bit;
   - hash do visual, bed e output;
   - validação de visual 1080×1920;
   - overlap de captions;
   - integrated LUFS e true peak;
   - path boundary do projeto independente;
   - aprovação por hash sem bloquear incorretamente o estado `APPROVED`.
5. Render tornado manifest-driven, em vez de depender de todos os nomes hardcoded.
6. Render usa arquivos temporários e `os.replace`, evitando promover output parcial.
7. Bed procedural recebeu seed fixo para re-render reproduzível.
8. Orchestrator ganhou lock por episódio, atualização atômica do manifest, estados `FAILED`/`TECH_VALIDATED` e `run-log.jsonl` local.
9. Removida a escrita redundante do concat no gerador visual.
10. Documentação de produção atualizada para seis cenas, estado real do áudio/mix e revisão humana pendente.
11. Adicionados testes unitários de normalização de transcript, overlap de captions e bloqueio de path externo.

## Verificação executada

- `py_compile`: passou.
- Testes: **7/7 passaram**.
- Render completo com manifest: passou.
- Validator v2: `TECH_VALIDATED`.
- Transcript: 156 palavras normalizadas no TXT e 156 na ASS; `exact_normalized_match=true`.
- Claims: 5 fatos `VERIFIED` + 1 `EDITORIAL_INFERENCE`.
- WAV: 24 kHz, mono, 16-bit, 58,36 s, não silencioso.
- Visual: 1080×1920.
- MP4: H.264/AAC, 1080×1920, 30 fps, 58,367 s.
- Mix: -18,3 LUFS integrado; true peak -1,0 dBFS.
- Hash output atual: `c54fc2bd9db68aa1a6b223a0c29fa3a23384904d872f54ca80fccf45178cfb25`.

## O que continua deliberadamente pendente

- revisão humana em alto-falante de celular;
- prova ASR word-level da coleta manual do AI Studio;
- model ID exato da sessão manual;
- publicação, analytics e feedback loop;
- restore test e batch test com múltiplos episódios;
- assets premium para S01/S04.

Esses itens não foram mascarados como concluídos. O episódio continua `REVIEW_REQUIRED` e não pode ser publicado automaticamente.

## Classificação pós-upgrade

Para este episódio: **TECHNICALLY VALIDATED / EDITORIAL REVIEW REQUIRED**.  
Para o motor: **OPERATIONAL BUT FRAGILE**, agora com o P0 de identidade textual corrigido e com uma base mais segura para o próximo episódio. Ainda não é robusto nem pronto para escala.
