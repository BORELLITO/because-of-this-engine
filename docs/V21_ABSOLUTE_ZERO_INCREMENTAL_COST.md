# BECAUSE OF THIS — Política ZERO gasto adicional (V2.1)

**Aprovação do usuário:** produzir e auditar somente por meios gratuitos, sem cobrança, assinatura, compra de créditos ou habilitação silenciosa de contas pagas.

## O que está efetivamente protegido

- `production/active_engine_policy.json` agora contém `zero_additional_cost_policy`: orçamento incremental máximo **US$ 0**, APIs pagas proibidas, novos TTS externos sem comprovação proibidos, ações com custo desconhecido BLOQUEADAS por padrão.
- `production/zero_cost_v21.py` é o guardião canônico: permite **reutilização offline do áudio Charon já aprovado**, FFmpeg local, testes e auditorias sem custos adicionais; bloqueia Gemini TTS externo, compra de bancos, renderização paga e serviços externos não identificados.
- A única requisição HTTP implementada para gerar voz (`production/gemini_tts._request_json`) invoca o gate **antes de criar/abrir a requisição**. Um API key, a menção à faixa gratuita, ou uma variável de ambiente não liberam chamadas cobradas.
- Os workflows de narração 005 e 006 fazem o mesmo pré-voo antes da etapa de geração. A opção manual RUN_ONCE continua visível por compatibilidade, mas **falha de propósito** sem acessar o provedor. CACHE_ONLY não gera voz nova.
- `production/v21_singleton_guard.py` e a CI impedem remoção silenciosa da trava.

## Verificação de custo: fonte versus conta

- O modelo `gemini-3.8-flash-tts` está listado com preço gratuito **na modalidade Free Tier** e preço por tokens na modalidade paga: https://ai.google.dev/gemini-api/docs/pricing . Isso NÃO prova que a chave usada pelo projeto esteja em um plano obrigatoriamente gratuito, nem que conta/billing estejam protegidos por teto de US$0.
- O repositório `BORELLITO/because-of-this-engine` é público no momento da auditoria. GitHub documenta que os runners padrão de Actions em repositórios públicos são gratuitos: https://docs.github.com/en/actions/concepts/billing-and-usage . Essa condição pode mudar se a visibilidade, tipo de runner ou política do provedor forem alterados. O código não consegue garantir sozinho que toda cobrança futura de um serviço externo seja impossível.
- O Mixkit permite usar as faixas sob a licença gratuita adequada em vídeos comerciais: https://mixkit.co/license/modal/musicFree/ . Isso não elimina direitos autorais, reclamações de Content ID nem obrigações de documentação de cada faixa.

## Como retomar uma narração realmente gratuita no futuro

Não autorizar novas requisições apenas com um campo booleano ou confirmação informal. Precisaremos de um mecanismo **externamente verificável, tecnicamente não contornável e com teto de cobrança zero** para a credencial e modalidade de execução usadas. Na ausência desse mecanismo, continuar com cache de voz Charon já aprovada e bloquear novas requisições. Não mudar a voz como atalho, nem gastar para desbloquear.

## Não houve promoção nem custo intencional

Esta alteração é de política e validação; não realiza TTS, download pago, render final, upload Drive nem publicação. A produção e o envio final seguem desabilitados; a publicação permanece manual. Os testes usam mocks que demonstram que `urllib.request.urlopen` **nunca é chamado** sob configuração proibida.

**Próximo trabalho útil:** solucionar os gates já conhecidos (histórico SFX, direitos de fonte e checagem de Content ID da música candidata) com pesquisa e arquivos recuperados, sem novas chamadas pagas.
