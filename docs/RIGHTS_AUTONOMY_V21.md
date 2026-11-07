# Because Of This — Rights Autonomy V2.1

**Authority:** `production/active_engine_policy.json`. Factual documentary; Gemini TTS/Charon locked; production off, publication manual.

## Motor de decisões sem depender do usuário

`production/rights_autonomy_v21.py` determina autonomamente elegibilidade de cada clipe para o pré-voo de renderização editorial. Saídas: `AUTO_APPROVED_FOR_SCOPED_RENDER` ou `BLOCKED_PENDING_SAFEGUARDS`.

Para aprovar, exige todas as evidências:
- A mídia está presente no plano, manifesto e rights ledger com o mesmo ID, URL oficial e hash SHA-256/fingerprint perceptual.
- O vídeo real foi recuperado de um artefato registrado e o arquivo e pelo menos cinco amostras, incluindo recorte vertical, foram inspecionados.
- Licença oficial Pexels/Pixabay/NASA aplicável ao tipo de material; não aceita domínios falsos nem inferência de permissões a partir de vídeo semelhante.
- Sem marca/logotipo identificável. Pessoas reconhecíveis só podem aparecer se houver licença/contexto válido **e** advertência expressa de dramatização no quadro e nos metadados, vinculada a prova real de amostra. Nenhum ator pode ser apresentado como personagem histórico verdadeiro.
- Representação não documental não deve ser apresentada como arquivo autêntico de 1983; áudio de fontes externas é removido.
- Sinalização de reuso global não pode conter colisão conhecida.
- Modelos NASA modernos exigem a etiqueta factual de 2020 dentro da cena e créditos oficiais nos textos de plataforma; testar o aviso em amostras do arquivo exato. Não considerar o vídeo final certificado antes de inspeção posterior.

O motor não emite parecer jurídico, não garante inexistência de direitos de terceiros além da inspeção, não prova ineditismo fora do catálogo conhecido e não dispensa QA do vídeo codificado. Quando não há evidência suficiente, ele BLOQUEIA e descreve qual condição faltou. Não pede aprovação editorial do usuário por padrão.

## Prova operacional — Episode 005, 07/11/2026

Os sete arquivos originais foram recuperados de arquivos oficiais do GitHub Actions; os sete SHA-256 foram rechecados localmente contra os respectivos manifestos. Páginas específicas dos fornecedores e as políticas Pexels, Pixabay e NASA foram confrontadas. A decisão e a prova versionada constam de `reports/EP005_AUTONOMOUS_RIGHTS_VISUAL_EVIDENCE_20261107.json`.

| Shot | Asset | Decisão |
|---|---|---|
| S03 | `pixabay-radio-vintage-old-171435` | APPROVE scoped — rádio simbólico, sem pessoa/marca observável |
| S05 | `pixabay-radar-black-green-target-symbol-57670` | APPROVE scoped — gráfico abstrato, não tela real de Petrov |
| S06 | `pexels-5523892` | APPROVE scoped — LED abstrato, não evento documentado |
| S09 | `pexels-8888977` | APPROVE scoped — mãos em teclado retrô, sem rosto; não atribuir a Petrov |
| S11 | `pexels-12590338` | APPROVE scoped — céu atmosférico genérico; não é arquivo do incidente |
| S01 | `pexels-11764431` | APPROVE scoped — ator reconhecível mantido, com aviso obrigatório **DRAMATIZATION - NOT ARCHIVAL FOOTAGE** já testado sobre o vídeo original e cláusula de não identificação como Petrov |
| S12 | `nasa-svs-geos5-clouds-no-labels-4819` | APPROVE scoped — fonte GEOS-5 de 2020 etiquetada na própria imagem e créditos NASA SVS / Greg Shirah / Trent L. Schindler / Ryan Fitzgibbons preparados e verificados em amostra real |

**Significado de APPROVE:** licença da mídia e contexto amostrado permitem **uso como material para render editorial privado daquela cena/episódio**. Não significa preview final aprovado, obra completa validada, ausência garantida de todos os direitos de terceiros, nem autorização de postagem. `used_by` nos novos registros quer dizer *uso pretendido/autorizado para episódio*, não prova de vídeo entregue.

**Significado de BLOCK:** o motor deve procurar correção ou substituto automaticamente e deixar a mídia bloqueada caso a prova de licença ou identificação histórica falhe. No episódio 005, todas as sete mídias novas estão aptas **somente para render editorial controlado**, desde que os avisos S01/S12 sejam aplicados pelo renderizador. A saída final não foi auditada.

### Correções comprovadas no episódio 005

A trilha real de montagem coloca o ator no **S01**, não no S03, apesar de o campo antigo `source_role` dizer S03. A cena S03 é o rádio vintage, não um rosto. Cinco alternativas de substituição foram baixadas e rejeitadas após inspeção de 9:16: luzes modernas, mãos fora do recorte ou carta romântica legível quebravam a narrativa. O motor preferiu preservar a foto-fonte e aplicar aviso verdadeiro, conservando a composição já aprovada.

Os previews reais foram executados sem voz nova ou edição do vídeo principal: **S01** 4s 1080×1920/60fps, SHA `c7a4a30bf8f108363759534598b9a4cddb79a5cc024a0caa3eab86721e47bbf7`; **S12** 5s 1080×1920/60fps, SHA `6ca0255fa7a447052a84d9cad403d351de2f815e88e715f68b4a68804ba0d4bc`. Os créditos preparados são do NASA Scientific Visualization Studio e dos profissionais listados na página https://svs.gsfc.nasa.gov/4819/. Detalhes em `reports/EP005_S01_S12_TRUTH_LABEL_QA_20261107.json` e `episodes/episode-005/visual/scene-disclosures-v21.json`.

Os novos rótulos são **hard gates** em `production/scene_disclosures_v21.py` e `production/render_v21_preview.py`. Alterar ID, SHA, local de cena, texto, prova da amostra ou crédito torna o contrato inválido. O validador exige que o S01 e o S12 tenham conteúdo avisando expressamente que não são registros autênticos dos sensores de 1983, sem encobrir o locutor ou reutilizar a licença de outro clipe.

## Contratos e segurança

- `RIGHTS_AUTONOMY_V21` executa em `production/canonical_entrypoint.py` e `production/render_v21_manual.py`, aplicando o motor ao rights ledger real.
- Alterar somente `rights_status`/boolean sem evidência não libera o clipe.
- O audit `PASS` significa que **sete decisões por fonte** estão coerentes com as evidências de mídia e com o contrato `SCENE_DISCLOSURES_V21`. Não significa vídeo final renderizado, obra certificada ou publicação liberada. `AUDIO_HISTORY_COVERAGE` permanece bloqueando a produção do episódio.
- Não gerar novas vozes ou vídeos sem escopo/autorização de custo e preview; publicação permanece manual.
- Rastreabilidade/rollback: PR e branch `backup/main-before-rights-auto-decision-20261107`.

## Fontes oficiais consultadas

- Pexels licença: https://www.pexels.com/license/
- Pexels uso comercial: https://help.pexels.com/hc/en-us/articles/360042295214-Can-I-use-the-photos-and-videos-for-a-commercial-project
- Pixabay termos: https://pixabay.com/service/terms/
- NASA guia de mídia: https://www.nasa.gov/nasa-brand-center/images-and-media/
- NASA GEOS-5 2020, créditos: https://svs.gsfc.nasa.gov/4819/

**Limitação estrutural a melhorar:** as evidências visuais deste lote foram auditadas e registradas; para novos clipes, é necessária uma rotina upstream que produza automaticamente QA verificável de vídeo real (amostragem, detecção de rosto/marca e validação semântica). O motor atual é automático na **decisão** sobre evidência estruturada, mas não substitui um serviço de visão que analise cada frame de novos arquivos. Nunca alegar que faz inspeção visual automática integral sem esse componente.
