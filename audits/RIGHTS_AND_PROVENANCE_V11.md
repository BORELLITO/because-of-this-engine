# BECAUSE OF THIS — Revisão de direitos e procedência | V1.1

Data da revisão: 2026-11-04. **Somente evidências, sem liberação de produção.**

## Hierarquia obrigatória de prova

- **E1 — Manifesto declara:** `license`, `rights_status`, fonte, autor. *Autodeclaração, não verificação.*
- **E2 — Arquivo existe:** Google Drive responde metadados `video/mp4`. *Não comprova checksum, origem nem licença.*
- **E3 — Fonte pública consultada:** a página original e seu regime de licença foram abertos. *Não comprova que o MP4 do Drive é idêntico ao original.*
- **E4 — Integridade e imagem:** verificar bytes SHA-256, frames e direitos de terceiros, pessoas, marcas e elementos editoriais.
- **E5 — Produção:** autorização documentada do usuário, prova visual final, aprovação de áudio/legendas e publicação manual.

## Evidências verificadas nesta sessão

| Fonte específica | Registro oficial observado | Estado |
|---|---|---|
| Mixkit, bay landscape aerial 1940 | A página do clipe indica explicitamente **Mixkit Stock Video Free License**, apta a vídeos comerciais | Fonte pública conferida (E3), derivado ainda E2 |
| Mixkit, aerial mountain top 43129 | A página do clipe indica **Mixkit Stock Video Free License** | E3 apenas |
| USGS, Lituya Bay 1958 | Página identifica autor Don J. Miller e **Public Domain** | E3 apenas |
| Wikimedia Commons, Lituya Bay spit.jpg | A página específica atribui obra do servidor federal D. J. Miller e indica **domínio público nos EUA** | E3 apenas |
| Wikimedia Commons, Lituya-Bay-overview-with-arrows.png | Página identifica origem USGS e **domínio público nos EUA** | E3 apenas |

URLs:
- https://mixkit.co/free-stock-video/bay-landscape-aerial-shot-1940/
- https://mixkit.co/free-stock-video/aerial-view-of-a-mountain-top-43129/
- https://www.usgs.gov/media/images/lituya-bay-1958
- https://commons.wikimedia.org/wiki/File:Lituya_Bay_spit.jpg
- https://commons.wikimedia.org/wiki/File:Lituya-Bay-overview-with-arrows.png

## Licenças gerais e suas restrições

- **Pexels:** uso comercial de vídeos é permitido em geral. Não retratar pessoas identificáveis de maneira ofensiva ou degradante, nem implicar endosso; direitos de marca, privacidade e outros de terceiros podem exigir consentimento. Isso importa especialmente em terror que dramatize crimes ou traumas. https://www.pexels.com/legal-pages/license/ e https://www.pexels.com/terms-of-service/
- **Mixkit:** existem licenças **Free** e **Restricted** para clipes; **Restricted** não é aprovação para publicação comercial. Verificar a página *do clipe específico*, não apenas a licença geral. https://mixkit.co/license/ e https://mixkit.co/license/modal/videoFree/
- **Pixabay:** licença permite usos em obras criativas, mas proíbe usos independentes sem trabalho criativo e determinados usos com marcas ou pessoas identificáveis; direitos de terceiros continuam relevantes. https://pixabay.com/service/license-summary/
- **USGS / Wikimedia Commons:** boa parte das obras USGS é pública, porém o próprio USGS ressalva que alguns materiais de terceiros em seu site são protegidos. Licença precisa ser conferida por item. https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs

## Drive — resultado de metadados

- IDs de vídeo de episódios de estado `FINAL_APPROVED` presentes nos manifestos atuais: **32 / 32** localizados via metadados Google Drive, tipo `video/mp4`, com tamanho conhecido.
- IDs históricos da prévia V7.2 verificados com **maiúsculas/minúsculas originais**: **6 / 6** localizados, todos nomeados `PREVIEW_ONLY`.
- Nenhum desses resultados verifica bytes SHA-256, o conteúdo real de todos os frames, autoria ou publicação. **Não promover E2 a E4.**
- Outros diretórios do Drive contêm prévias e versões antigas; o acervo inteiro ainda não foi enumerado.

## Git — escopo histórico

- Varredura executada sobre **74 branches** remotas, **251 ocorrências de manifestos**, **47 blobs de manifesto distintos**, sem erro de parsing.
- **95 fontes distintas normalizadas** por origem (79 no catálogo atual + 16 vistas somente em branches antigos). A contagem anterior de 100 foi corrigida após identificar cinco aliases da mesma origem Pexels.
- As **16** fontes adicionais foram documentadas em `audits/git_history_review_queue_v11.json` com status `PENDING_REVIEW_NOT_RETIRED`.
- Uma fonte registrada apenas em um rascunho **não é automaticamente consumida nem aposentada**. Se um episódio novo tentar utilizá-la, o motor responde `HISTORY_REVIEW_REQUIRED` para análise humana.

## Bloqueios remanescentes

1. Integridade real dos derivados do Drive (checksum e conteúdo visual) não comprovada para o acervo completo.
2. Licenças individualizadas, eventuais consentimentos de terceiros e flags de `preview_only` não revisados item a item para as 95 fontes.
3. Prova de publicação real por episódio e listas de músicas consumidas em outras branches ainda não auditadas integralmente.
4. Segurança de legenda sobre as interfaces reais do TikTok e Shorts e validação ponta a ponta de vídeo novo pendentes.

**Status:** RIGHTS_PARTIAL / NEW_PRODUCTION_BLOCKED. **Gemini TTS Charon** preservado; `main` e *One Extra Minute* intocados.

