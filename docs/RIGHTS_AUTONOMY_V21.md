# Because Of This — Rights Autonomy V2.1

**Authority:** `production/active_engine_policy.json`. Factual documentary; Gemini TTS/Charon locked; production off, publication manual.

## Motor de decisões sem depender do usuário

`production/rights_autonomy_v21.py` determina autonomamente elegibilidade de cada clipe para o pré-voo de renderização editorial. Saídas: `AUTO_APPROVED_FOR_SCOPED_RENDER` ou `BLOCKED_PENDING_SAFEGUARDS`.

Para aprovar, exige todas as evidências:
- A mídia está presente no plano, manifesto e rights ledger com o mesmo ID, URL oficial e hash SHA-256/fingerprint perceptual.
- O vídeo real foi recuperado de um artefato registrado e o arquivo e pelo menos cinco amostras, incluindo recorte vertical, foram inspecionados.
- Licença oficial Pexels/Pixabay/NASA aplicável ao tipo de material; não aceita domínios falsos nem inferência de permissões a partir de vídeo semelhante.
- Sem pessoa identificável nem marca/logotipo identificável no recorte que será usado.
- Representação não documental não deve ser apresentada como arquivo autêntico de 1983; áudio de fontes externas é removido.
- Sinalização de reuso global não pode conter colisão conhecida.
- Modelos NASA modernos devem ter **créditos e esclarecimento factual verificados no pacote de entrega**; não basta promessa de inserir depois.

O motor não emite parecer jurídico, não garante inexistência de direitos de terceiros além da inspeção, não prova ineditismo fora do catálogo conhecido e não dispensa QA do vídeo codificado. Quando não há evidência suficiente, ele BLOQUEIA e descreve qual condição faltou. Não pede aprovação editorial do usuário por padrão.

## Prova operacional — Episode 005, 07/11/2026

Os sete arquivos originais foram recuperados de arquivos oficiais do GitHub Actions; os sete SHA-256 foram rechecados localmente contra os respectivos manifestos. Páginas específicas dos fornecedores e as políticas Pexels, Pixabay e NASA foram confrontadas. A decisão e a prova versionada constam de `reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json`.

| Shot | Asset | Decisão |
|---|---|---|
| S04 | `pixabay-radio-vintage-old-171435` | APPROVE scoped — rádio simbólico, sem pessoa/marca observável |
| S05 | `pixabay-radar-black-green-target-symbol-57670` | APPROVE scoped — gráfico abstrato, não tela real de Petrov |
| S06 | `pexels-5523892` | APPROVE scoped — LED abstrato, não evento documentado |
| S09 | `pexels-8888977` | APPROVE scoped — mãos em teclado retrô, sem rosto; não atribuir a Petrov |
| S11 | `pexels-12590338` | APPROVE scoped — céu atmosférico genérico; não é arquivo do incidente |
| S03 | `pexels-11764431` | BLOCK — rosto de ator reconhecível em recriação com figura histórica real |
| S12 | `nasa-svs-geos5-clouds-no-labels-4819` | BLOCK — falta prova de créditos + aviso de que são nuvens modeladas em 2020 |

**Significado de APPROVE:** licença da mídia e contexto amostrado permitem **uso como material para render editorial privado daquela cena/episódio**. Não significa preview final aprovado, obra completa validada, ausência garantida de todos os direitos de terceiros, nem autorização de postagem. `used_by` nos novos registros quer dizer *uso pretendido/autorizado para episódio*, não prova de vídeo entregue.

**Significado de BLOCK:** motor deve procurar automaticamente correção ou substituto com risco menor. Não é requisito de “usuário aprovar novamente”. Para S03, preferir mãos, rádio/caderno ou silhueta não identificável e verificar a cena real. Para NASA S12, registrar crédito e esclarecer no pacote que o modelo GEOS-5 é de 2020 antes de autorizar seu uso, ou usar uma representação meteorológica original de baixo risco.

## Contratos e segurança

- `RIGHTS_AUTONOMY_V21` executa em `production/canonical_entrypoint.py` e `production/render_v21_manual.py`, aplicando o motor ao rights ledger real.
- Alterar somente `rights_status`/boolean sem evidência não libera o clipe.
- O audit `PASS` significa que **as cinco autorizações e os dois bloqueios** estão coerentes com a evidência, não que o vídeo final possa ser renderizado. `rights_ledger`, `VISUAL_RIGHTS_CONSISTENCY`, `AUDIO_HISTORY_COVERAGE` ainda podem bloquear.
- Não gerar novas vozes ou vídeos sem escopo/autorização de custo e preview; publicação permanece manual.
- Rastreabilidade/rollback: PR e branch `backup/main-before-rights-auto-decision-20261107`.

## Fontes oficiais consultadas

- Pexels licença: https://www.pexels.com/license/
- Pexels uso comercial: https://help.pexels.com/hc/en-us/articles/360042295214-Can-I-use-the-photos-and-videos-for-a-commercial-project
- Pixabay termos: https://pixabay.com/service/terms/
- NASA guia de mídia: https://www.nasa.gov/nasa-brand-center/images-and-media/
- NASA GEOS-5 2020, créditos: https://svs.gsfc.nasa.gov/4819/

**Limitação estrutural a melhorar:** as evidências visuais deste lote foram auditadas e registradas; para novos clipes, é necessária uma rotina upstream que produza automaticamente QA verificável de vídeo real (amostragem, detecção de rosto/marca e validação semântica). O motor atual é automático na **decisão** sobre evidência estruturada, mas não substitui um serviço de visão que analise cada frame de novos arquivos. Nunca alegar que faz inspeção visual automática integral sem esse componente.
