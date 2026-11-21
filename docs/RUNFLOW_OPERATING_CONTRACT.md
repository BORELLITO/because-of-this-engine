# BECAUSE OF THIS — Runflow Mestre

## Objetivo

O Runflow mestre é a única rota operacional para transformar um checkpoint
Gemini/Charon já validado em um vídeo V2.1 com visuais, legendas, logo, outro e
QA técnico. A chamada operacional passa a ser:

1. informar `episode_id`, `source_run_id` e `source_artifact_name`;
2. executar `BECAUSE OF THIS — Runflow Mestre`;
3. receber um único bundle de artefatos com o MP4 e seus relatórios.

## Agentes integrados

- pacote canônico e isolamento de escopo;
- intake e verificação SHA-256 dos clipes;
- lock de legendas karaoke a partir do áudio real;
- montagem V2.1 com logo, safe zone e tela final;
- QA técnico de geometria, FPS, duração e áudio;
- entrega como artefato único do GitHub Actions.

O Runflow não cria um segundo motor. Ele chama os módulos canônicos existentes
e mantém os gates especializados dentro deles.

## Limites permanentes

- somente `BORELLITO/because-of-this-engine`;
- nenhum acesso ao `verbo-no-chao-engine` ou a qualquer outro projeto;
- nenhum motor Edge, Piper, Creative Claw ou V7;
- nenhuma nova chamada TTS nesta rota;
- nenhuma publicação automática;
- modo `final` só pode ser liberado quando os gates de produção, direitos,
  histórico de áudio e entrega estiverem realmente aprovados.

O modo `preview` entrega um vídeo tecnicamente pronto para revisão como
artefato do Runflow. Isso não é publicação nem autorização para contornar os
gates finais.

O modo `final` já está representado no contrato para evitar a criação de uma
segunda rota no futuro, mas permanece fail-closed enquanto a política canônica
mantiver `production_enablement=false`. Ele não finge entregar um master final
nem permite que um usuário contorne direitos, histórico de áudio ou a auditoria
independente.
