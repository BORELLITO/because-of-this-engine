# BECAUSE OF THIS — Change Transparency Protocol

Status: mandatory.

## Objetivo

Borelli deve entender o estado do projeto, o que está sendo feito, o que permanece protegido e qual evidência confirma o resultado. O motor não pode operar como uma caixa-preta.

## Comunicação antes da ação

Toda ação relevante começa com um resumo curto contendo:

1. estado atual;
2. objetivo da ação;
3. escopo autorizado;
4. itens preservados;
5. riscos, dependências ou bloqueios;
6. evidência esperada;
7. se a ação é reversível e como fazer rollback.

## Estados oficiais

- PLANEJADO: definido, ainda não executado;
- EM EXECUÇÃO: ação em andamento;
- IMPLEMENTADO: alteração aplicada;
- TESTADO: validações executadas com resultado conhecido;
- APROVADO: Borelli autorizou ou aprovou o resultado;
- BLOQUEADO: a ação parou por falha, drift, falta de autorização ou dependência.

## Comunicação depois da ação

O encerramento deve informar separadamente:

- implementado;
- não implementado;
- testes e evidências;
- riscos remanescentes;
- rollback;
- próximo passo.

Não usar “concluído”, “perfeito” ou “100%” sem evidência. Quando algo falhar, declarar a falha e manter o sistema em estado seguro.

## Regra de PR

Mudanças do núcleo devem conter no corpo do Pull Request todas as seções abaixo:

- ## Transparência da mudança
- ### Estado antes
- ### Escopo autorizado
- ### O que foi preservado
- ### Impacto e riscos
- ### Testes e evidências
- ### Rollback
- ### Próximo passo

O workflow immutable-core bloqueia PRs que não apresentem esse relatório. A documentação melhora a comunicação; a autorização explícita e as travas técnicas continuam obrigatórias.
