# Narrador independente para Shorts — Gemini TTS

Este é um módulo independente de geração de narração para o novo projeto faceless Shorts. Ele não acessa, modifica nem depende dos motores do CaptaPronto, Corte Fino, Publisher ou Creator.

## Escolha inicial

- Provedor: Google Gemini API, conexão direta.
- Modelo padrão: `gemini-3.8-flash-lite-tts`.
- Voz inicial: `Charon` (perfil informativo da biblioteca pré-criada do Gemini).
- Estilo: narração documental em inglês americano, natural e contida.
- Saída: WAV, com arquivo JSON de proveniência.

A API oficial mostra faixa gratuita para os modelos TTS Gemini 3.8. A cota efetiva varia por projeto e deve ser conferida no AI Studio. Para manter o teste sem cobrança, use o projeto sem faturamento ativo e pare quando a cota gratuita acabar; não habilite faturamento para contornar limite. O nível gratuito também informa que dados podem ser usados para melhorar produtos do Google. Não envie material sensível. O script faz uma única solicitação por execução e não tenta novamente automaticamente.

## Requisitos

- Python 3.10 ou superior.
- Chave da Gemini API criada no Google AI Studio.
- Acesso ao modelo TTS e cota disponível no projeto Google.

## Instalação

No terminal, dentro desta pasta:

```bash
python -m venv .venv
```

Ative o ambiente virtual e instale:

```bash
python -m pip install -r requirements.txt
```

Configure `GEMINI_API_KEY` como variável de ambiente. Não salve a chave no código, no Git ou em prints.

Linux/macOS:

```bash
export GEMINI_API_KEY="SUA_CHAVE_AQUI"
```

PowerShell:

```powershell
$env:GEMINI_API_KEY="SUA_CHAVE_AQUI"
```

## Gerar a locução

O pacote inclui o roteiro da Mars Climate Orbiter usado nesta etapa. Para gerar a primeira amostra, rode:

```bash
python narrate.py --input examples/mars_climate_orbiter.txt --output output/mars-climate-orbiter.wav
```

O programa gera:

- `output/narracao.wav` — áudio para revisão e edição;
- `output/narracao.wav.json` — provedor, modelo, voz, duração, data e hash do roteiro (não grava o texto do roteiro).

Para escolher outra voz pré-criada ou orientar a entrega:

```bash
python narrate.py --input roteiro.txt --output output/narracao.wav --voice Kore --style "Neutral American English documentary narration; measured, clear, natural, with restrained emphasis."
```

O script não sobrescreve saídas por padrão. Use `--overwrite` conscientemente quando quiser substituir o áudio e o sidecar. Cada execução faz no máximo uma chamada de geração. Se ocorrer erro de rede, cota ou autenticação, corrija a causa antes de executar novamente.

## Verificações locais

Para rodar os testes sem chave e sem chamar a API:

```bash
python -m unittest discover -s tests -v
```

Os testes usam uma resposta simulada apenas para verificar formato WAV, registro de proveniência, proteção contra sobrescrita e rejeição de saídas inválidas. Eles não comprovam a qualidade da voz nem consomem créditos.

## Estado deste pacote

O adaptador CLI está implementado e validado com testes simulados. A primeira
narração real do episódio Mars Climate Orbiter foi coletada no AI Studio e está
em `production/mars-climate-orbiter-charon.wav`, com provenance sidecar. O CLI
de API continua separado: ele exige uma chave própria e não foi usado para
inventar ou substituir o áudio já aprovado.

Para validar o episódio completo localmente:

```bash
python production/validate_episode.py \
  --manifest production/mars-climate-orbiter-episode.json \
  --report production/mars-climate-orbiter-validation.json
```

O validator é fail-closed: verifica hash do roteiro, vínculo do transcript com
as captions, claims, provenance do WAV 24 kHz mono, áudio não silencioso,
streams, resolução, codecs, duração, loudness, true peak e hash do MP4.
`TECH_VALIDATED` não significa `APPROVED`; a aprovação humana no celular ainda
é um estado separado.

Para renderizar e validar com lock, atualização de hashes e relatório de
execução:

```bash
python production/run_episode.py \
  --manifest production/mars-climate-orbiter-episode.json \
  --render
```

O render lê os caminhos do manifest, escreve primeiro em arquivos temporários,
usa um bed determinístico e o orchestrator registra eventos em
`production/run-log.jsonl` (arquivo local ignorado pelo Git).

A camada visual atual é a revisão v4 do rascunho editorial: cada cena foi
reconstruída para corresponder a um beat narrativo específico, sem textos
decorativos duplicando as captions. O visual continua sendo uma reconstrução
editorial original, não uma alegação de telemetria ou imagem de arquivo da NASA.

## Integração futura no motor novo

Este CLI funciona como primeiro teste isolado. Quando o repositório **do novo motor independente** estiver disponível, a função `generate_narration()` pode ser chamada pela etapa de áudio desse motor. Antes disso, precisamos validar uma amostra real, conferir pronúncia/duração e decidir se essa voz será a identidade recorrente do canal.

