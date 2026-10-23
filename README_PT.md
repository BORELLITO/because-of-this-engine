# BECAUSE OF THIS — Motor independente de documentários verticais

Este repositório reúne o motor faceless independente para documentários verticais do canal. Ele mantém o fluxo isolado de roteiro, narração, visuais autorais, montagem, captions, controle de licença e validação; não depende dos motores CaptaPronto, Corte Fino, Publisher ou Creator.

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

## Pipeline oficial do episódio — schema 1.1

A narração Charon aprovada do episódio Mars Climate Orbiter está em
`examples/assets/mars-climate-orbiter-charon.wav`. O fluxo oficial é
`run_episode.py`: preflight, render, validação e registro de execução.

Rodar a suíte sem chave de API:

```bash
python -m unittest discover -s tests -v
```

Gerar e validar o preview:

```bash
python production/run_episode.py \
  --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
  --mode preview --render
```

Depois de assistir ao preview no celular e criar a aprovação vinculada aos
hashes exatos de entrada e saída, o final pode ser solicitado com
`--mode final --render`. Sem aprovação válida, o render final é bloqueado.

### Música e licença

O renderer aceita uma faixa licenciada declarada no manifest. A voz permanece
em primeiro plano; a trilha recebe ganho baixo, ducking automático durante a
narração e limitação de pico. O ganho configurável é limitado a 0,25 e o padrão
é 0,08.

O manifest de exemplo já exige música no final (`require_music: true`), mas
não inclui uma faixa. Por isso, o preview pode ser renderizado sem trilha e o
final permanece bloqueado até uma faixa ser selecionada e documentada. Registre
arquivo, fonte, licença, permissão comercial, atribuição quando exigida e risco
de Content ID em `examples/music-license-register.template.json`. Não presuma
que uma faixa é segura só por ser chamada de royalty-free.

O pipeline verifica codec, resolução, duração, sincronismo de captions,
proveniência e movimento. A aprovação perceptual no celular continua sendo
necessária; validação técnica não garante qualidade editorial nem monetização.

## Gerador visual gratuito e profissional

O motor independente possui três adaptadores. O padrão gratuito e sem cadastro
é a NASA Image and Video Library: ele busca uma imagem factual relacionada à
cena, recorta para 9:16 e grava a origem no sidecar. Cloudflare Workers AI e
Gemini continuam disponíveis como opções explícitas, sem fallback automático
entre provedores.

- padrão gratuito sem chave: `nasa`;
- alternativa generativa opcional: `@cf/stabilityai/stable-diffusion-xl-base-1.0`;
- premium opcional: `gemini-3-pro-image` (Nano Banana Pro), bloqueado por padrão;
- saída: PNG vertical, sem texto embutido, com sidecar de proveniência;
- captions e rótulos factuais continuam na camada de edição;
- limite local de chamadas e ledger diário impedem geração acidental em loop.

Para gerar os frames sem criar conta adicional:

```bash
python production/generate_mars_images.py --provider nasa --scene S01
```

O provedor usa a busca pública da NASA, sem API key. As cenas S01 e S03 usam
o identificador do Mars Climate Orbiter quando disponível; as demais usam
consultas temáticas controladas. Isso reduz imagens sem relação com o roteiro,
mas cada PNG ainda precisa de aprovação humana. A licença não deve ser inferida
apenas pelo domínio: confirme créditos, terceiros e restrições do item antes de
monetizar.

A Cloudflare informa uma alocação gratuita diária de 10.000 neurons. Para usar
esse caminho, é necessário criar uma conta Cloudflare, habilitar Workers AI e
gerar um token de execução de modelos. Configure `CLOUDFLARE_ACCOUNT_ID` e
`CLOUDFLARE_API_TOKEN` fora do GitHub e rode:

```bash
python production/generate_mars_images.py --provider cloudflare --scene S01
```

Para gerar todas as seis cenas, use `--scene ALL`. O script para se já houver
saída, se o limite diário local for atingido ou se a API falhar; ele não tenta
novamente sozinho. A geração premium exige a confirmação explícita:

```bash
GEMINI_ALLOW_PREMIUM_IMAGE=1 \
GEMINI_ALLOW_IMAGE_BILLING=1 \
python production/generate_mars_images.py --provider gemini --model gemini-3-pro-image --scene S01 --image-size 2K
```

Antes de monetizar, confirme a licença do modelo escolhido. A integração não substitui
automaticamente o visual atual: os assets precisam passar pela revisão humana
antes de entrarem no MP4 final.

Depois da revisão dos seis PNGs, o motion source pode ser montado sem alterar o
renderizador dos outros motores:

```bash
python production/build_mars_visual_ai.py
```

Esse comando falha se faltar qualquer cena ou sidecar. Só depois de aprovar os
frames no celular o arquivo deve ser apontado no manifest do episódio como uma
nova versão visual.

O renderer autoral aplica movimento individual por cena, easing suave, zoom
conservador e transições discretas. Ele não usa shake, glitch ou randomização
não auditável. Quando a faixa licenciada é declarada, a mixagem voice-first e os gates de licença são aplicados no release final.

Também existe um workflow manual em GitHub Actions. No celular: abra o
repositório, entre em **Actions**, escolha **Generate free Mars visuals**, toque
em **Run workflow** e selecione uma cena. O workflow usa o provedor NASA e não
exige secrets. Os arquivos aparecem como artefato para download. Cloudflare só
é necessário se você optar conscientemente por executar o provedor generativo
alternativo fora desse fluxo padrão.
