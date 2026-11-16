# LoreMotion — intake control V2.1

## Estado

LoreMotion está registrado como fonte opcional e manual-only. O teste browser validou um clipe LTX 2.5 em 9:16, 720p e 5 segundos, mas isso não autoriza renderização, publicação ou alteração do manifesto ativo.

## O que permanece preservado

- engine canônico V2.1;
- voz Charon;
- trilha e mix atuais;
- legendas karaoke com no máximo duas linhas;
- posição inferior das legendas;
- logo PNG original na geometria vigente;
- clipes e cortes aprovados;
- travas de não reutilização, direitos, fingerprint e render fail-closed.

## Fluxo permitido

1. Gerar manualmente o clipe no LoreMotion, usando apenas LTX 2.5 ou MiniMax H3.
2. Baixar o MP4 e manter o arquivo como candidato isolado.
3. Registrar prompt, modelo, formato, resolução, duração, status da marca d'água e data.
4. Registrar o recibo de direitos com os Termos e Uso aceitável do LoreMotion.
5. Confirmar que temos direitos sobre qualquer entrada usada.
6. Executar QA visual: fotorealismo, coerência narrativa, ausência de HUD, relógio, texto, logo e gráficos, além do crop 9:16.
7. Executar SHA-256 e fingerprint perceptual contra o catálogo global.
8. Solicitar aprovação humana para entrar no manifesto do episódio.
9. Somente após essa aprovação, reconciliar direitos e considerar o clipe para uma prévia autorizada.

## Bloqueios explícitos

- nenhum download automático do LoreMotion pelo GitHub Actions;
- nenhuma chamada direta ao site como se fosse API de produção;
- nenhum clipe entra no manifesto ativo automaticamente;
- nenhum clipe recebe approved_for_render=true por causa do site;
- nenhum render ou publicação é disparado por esta integração;
- nenhum engine antigo ou workflow alternativo pode assumir o clipe.

## Por que é assim

A página validada oferece uma ferramenta browser gratuita, mas não foi encontrada uma API pública documentada para uso estável no pipeline. O LoreMotion também tem regras próprias de uso, direitos sobre entradas e retenção limitada. Portanto, a arquitetura segura é gerar manualmente, registrar evidências, validar, aprovar e reconciliar, mantendo o engine V2.1 como autoridade final.


## Controle administrativo

Toda alteração em arquivos de autoridade exige revisão humana e o marcador explícito
`AUTHORIZED-IMMUTABLE-CORE-UPDATE` no título da mudança. O marcador autoriza a revisão
da alteração; ele não libera renderização, publicação, promoção automática ou bypass de
qualquer trava do V2.1.
