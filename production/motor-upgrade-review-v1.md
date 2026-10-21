# Revisão pós-upgrade — BECAUSE OF THIS

Data: 2026-10-20 (horário do projeto)  
Escopo: somente o motor independente do BECAUSE OF THIS.

## O que foi executado

1. Criado `mars-climate-orbiter-episode.json` como fonte operacional do episódio.
2. Criado `mars-climate-orbiter-claims.json` com quatro claims e fontes oficiais NASA/JPL.
3. Criado sidecar de provenance para o WAV Charon sem inventar o modelo usado na coleta manual.
4. Atualizado `render_mars_final.py` para derivar a duração diretamente do WAV.
5. Criado `validate_episode.py` com comportamento fail-closed.
6. Criado `run_episode.py` para executar e validar o episódio localmente.
7. Atualizados README e documento de produção para remover o estado histórico contraditório.

## Testes executados

- `py_compile`: passou para todos os scripts alterados.
- testes existentes do TTS: 4/4 passaram.
- render completo com duração derivada do áudio: passou.
- validator: `TECH_VALIDATED`.
- claims: 4/4 com fontes e status `VERIFIED`.
- WAV: 24 kHz, mono, 58,36 s, mean volume -18,6 dB.
- captions: 14 eventos, 0,30–58,34 s.
- MP4: 1080×1920, 30 fps, H.264/AAC, 58,366667 s.
- diferença entre vídeo e áudio: 0,006667 s.
- hash do output conferido contra o manifest.

## Resultado da segunda auditoria

### Melhorias reais

- A duração deixou de ser uma constante manual no render.
- O roteiro agora está ligado a um hash e a uma lista de claims/fontes.
- O áudio agora tem provenance verificável e hash próprio.
- O output não é considerado aprovado automaticamente.
- Um arquivo aprovado não pode ser sobrescrito pelo orchestrator.
- Um MP4 com codec, dimensão, duração, áudio ou captions inválidos falha no validator.
- O sistema consegue explicar por que um run foi aceito tecnicamente.

### Problemas que permanecem

1. A coleta do AI Studio ainda é manual; a automação completa depende da sessão autorizada e da forma de download disponível.
2. O model ID do áudio coletado manualmente permanece desconhecido; isso foi marcado explicitamente, sem inventar informação.
3. Captions continuam phrase-level; word-level ASR ainda não foi implementado.
4. O loudness foi medido por mean volume, mas a revisão em alto-falante de celular continua pendente.
5. O visual continua um draft procedural; a versão premium de S01/S04 é melhoria de qualidade, não blocker técnico.
6. O repositório GitHub independente ainda não foi criado porque a sessão GitHub está desconectada.
7. Não existe publicação, analytics ou feedback loop real.

## Classificação atual

### Para o episódio Mars

`OPERATIONAL WITH BLOCKERS`

O arquivo pode ser produzido e tecnicamente validado, mas ainda exige revisão móvel humana antes de `APPROVED`.

### Para o motor como produto repetível

`OPERATIONAL BUT FRAGILE`

O pacote melhorou bastante em correção e diagnóstico, mas ainda não possui ingestão geral, fila, estado persistente de produção, ASR, publicação, analytics ou escala.

## Revisão crítica das próprias melhorias

- O manifest aumentou controle, mas adicionou uma fonte que precisa permanecer única. Markdown não deve voltar a controlar parâmetros.
- O validator é útil porque bloqueia falso sucesso; ele não substitui a revisão editorial e não deve ser tratado como aprovação final.
- O orchestrator é pequeno e local; não deve ser transformado em sistema distribuído agora.
- A atualização automática do hash após render é segura enquanto o episódio não está aprovado; depois de aprovado, o orchestrator recusa overwrite.
- Claims/fontes aumentam confiabilidade, mas exigem manutenção quando o roteiro mudar. O hash impede que uma voz antiga seja confundida com script novo.

## Veredito

O changeset entregou o maior ganho com pouca complexidade e sem tocar nos motores protegidos. O próximo upgrade técnico correto é ASR word-level + phone QA. A criação do repositório privado `because-of-this-engine` continua pendente apenas por autenticação do GitHub.
