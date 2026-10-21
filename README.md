# BECAUSE OF THIS — Independent Engine

Motor independente para gerar Shorts narrativos de ciência e suspense, com prioridade em ferramentas gratuitas.

## Estrutura

- narrate.py: geração opcional de narração via Gemini.
- production/: renderização, validação fail-closed, manifestos e documentação.
- tests/: testes unitários.
- .github/workflows/validate.yml: compilação, testes e validação de metadados no GitHub Actions.

## Execução local

1. Crie um ambiente Python 3.12.
2. Instale requirements.txt.
3. Copie .env.example para .env e configure sua chave apenas localmente.
4. Use python production/run_episode.py --manifest production/mars-climate-orbiter-episode.json.

Arquivos WAV/MP4 e frames gerados não são versionados; o repositório guarda o código, os metadados e a trilha de auditoria.
