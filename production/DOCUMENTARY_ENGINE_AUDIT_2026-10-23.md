# Auditoria do motor documental — 2026-10-23

Escopo: somente `BORELLITO/because-of-this-engine`. Capta Pronto, Corte Fino,
Publisher e Creator não foram modificados nem são dependências deste motor.

## 1. Diagnóstico geral do motor

O motor já possui uma fundação correta: roteiro, narração, imagens autorais,
legendas externas, manifest, provenance, preview, aprovação humana, render e
validação. O problema principal não era falta de ferramentas; era a passagem
entre intenção editorial e montagem. A implementação antiga aplicava o mesmo
zoom central linear e a mesma transição em todas as cenas. Isso atendia ao
contrato mínimo, mas não ao padrão documental natural exigido pelo projeto.

Veredito inicial: arquitetura aproveitável, camada de movimento subespecificada,
gates de qualidade incompletos e exemplo Mars com timeline incompatível com a
narracão.

## 2. Como o motor funciona hoje

`tema → roteiro → narração → plano visual → imagens autorais → manifest →
renderer → captions → mux de áudio → preview/final → validator → aprovação`

Entradas: WAV 24 kHz mono, imagens verticais com sidecars, roteiro, ASS,
manifest e aprovação humana. Decisões: duração, imagem por beat, zoom,
transição e captions. Saídas: MP4 vertical H.264/AAC e relatório JSON.

## 3. O que está funcionando muito bem

- isolamento do motor e caminhos protegidos contra escape;
- render temporário com promoção atômica, sem substituir saída boa por falha;
- narração como base temporal;
- captions externas, sincronizadas ao roteiro canônico;
- provenance obrigatório para imagens;
- preview antes de final e aprovação vinculada ao hash das entradas;
- estilo autoral com proibição de texto, logos, marcas d’água e “evidência” falsa;
- validação de streams, resolução, codecs, duração e arquivos legíveis.

## 4. Problemas críticos

| ID | Problema | Severidade | Estado |
|---|---|---:|---|
| P0-01 | Timeline do manifesto Mars usava 6×4,6 s e não cobria a narração de ~58 s | Crítico | Corrigido no manifesto |
| P0-02 | Zoom central linear via `zoompan` produzia sensação de tremor/robotização | Crítico | Corrigido no renderer |
| P0-03 | Movimento não era escolhido pelo beat narrativo | Crítico | Corrigido com `motion_engine` |
| P0-04 | Validator não verificava variedade, easing ou contrato visual | Crítico | Corrigido |
| P0-05 | Mesma transição em todas as cenas | Alto | Corrigido no contrato; default conservador mantido |
| P0-06 | Não havia gate explícito de música/licença/disclosure | Alto | Gate adicionado quando ativado |

## 5. Gargalos

- geração/revisão de imagens continua sendo a etapa mais cara em tempo humano;
- render final 2160×3840 é deliberadamente mais lento por usar frames estáveis;
- aprovação no celular continua necessária, pois safe zones e legibilidade são
  propriedades perceptuais;
- áudio de fundo ainda depende de seleção/licença por episódio.

## 6. Conflitos e redundâncias

O conflito antigo era declarar “movimento autoral” enquanto o renderer aceitava
apenas `zoom_end`. Também havia duplicidade entre a promessa editorial de
variedade e a implementação de um único `xfade=fade`. A nova regra é única:
manifesto → `motion_engine` → renderer e validator usam o mesmo contrato.

## 7. Falhas silenciosas

- timeline curta podia ser esticada/truncada pelo mux sem denunciar a causa;
- imagem ilegível só aparecia no render, não no plano visual;
- repetição de movimento não era detectada;
- música poderia entrar sem licença registrada;
- uma imagem ilustrativa podia ser interpretada como evidência se o contexto não
  estivesse marcado.

Os quatro primeiros itens agora falham antes do release quando os gates estão
ativados. A interpretação humana de cada imagem continua sendo um gate manual.

## 8. O que estávamos deixando passar

- seleção de movimento por posição do sujeito;
- diferença entre fato documentado e reconstrução visual;
- registro de licença por faixa;
- disclosure de conteúdo sintético realista;
- medição de variação de movimento e transição;
- comparação entre retenção por beat e troca de imagem.

## 9. O que não deve ser alterado

Não alterar a narração Charon sem motivo editorial comprovado; não remover
captions externas; não relaxar provenance; não introduzir shake/glitch; não
misturar este motor com os quatro motores protegidos; não chamar NASA ou outra
fonte como gerador silencioso de imagem.

## 10. O que deve ser removido

- dependência prática do `zoompan` linear para o render oficial;
- ideia de que seis durações idênticas são um plano visual;
- transição universal aplicada sem contexto;
- qualquer fallback silencioso para outro provedor de imagem.

## 11. O que deve ser corrigido

- usar o renderer subpixel estável;
- manter timeline compatível com o áudio;
- registrar beat, intenção, tipo de imagem e emoção em cada cena;
- aplicar motion/transition gates no validator;
- manter preview e final como estados distintos.

## 12. O que pode ser otimizado

- cache de frames de cenas repetidas;
- relatório de auditoria por episódio;
- mixagem de música/SFX após a narração estar bloqueada;
- geração de captions a partir dos mesmos timestamps do áudio;
- amostragem automática de frames para revisão rápida.

## 13. O que deve ser adicionado

- music license register por episódio;
- gate de disclosure na ficha de upload;
- score de alinhamento imagem–beat revisado por humano;
- métricas de retenção por troca de cena;
- teste de regressão com vídeo curto, imagem corrompida, caption sobreposta e
  motion inválido.

## 14. Upgrades prioritários

| Prioridade | Upgrade | Problema raiz | Validação |
|---|---|---|---|
| P0 | Renderer subpixel sem shake | arredondamento/crop central repetido | teste de render + inspeção mobile |
| P0 | Motion engine determinístico | movimento não dependia da narrativa | unit tests + report do manifest |
| P0 | Timeline audio-first | cenas não cobriam a narração | gate de duração |
| P1 | Motion variety gate | repetição silenciosa | três movimentos iguais falham |
| P1 | Music/license gate opt-in | direitos não rastreados | `require_music=true` |
| P1 | Visual-plan gate opt-in | imagem genérica | campos obrigatórios por cena |
| P2 | Retention map | ainda não há dados pós-publicação | implementar após primeiros uploads |

## 15. Arquitetura recomendada

`narration → timestamps/beats → visual_plan → authorial_assets + provenance →
motion_engine → renderer → captions/audio mix → validator → mobile approval →
final package → analytics feedback`

Cada camada possui um contrato. O renderer não decide fatos; o validator não
“conserta” dados; o approval não é substituído por CI.

## 16. Fluxo operacional final

1. fechar roteiro e fatos;
2. gerar/revisar narração;
3. extrair beats, pausas e payoff;
4. preencher plano visual;
5. gerar imagens autorais e sidecars;
6. calcular durações para cobrir a narração;
7. escolher movimento contextual e transição discreta;
8. gerar preview;
9. validar gates automáticos;
10. revisar no celular;
11. criar aprovação hash-bound;
12. renderizar final;
13. validar novamente;
14. registrar assets, licença, disclosure e resultado pós-publicação.

## 17. Métricas e KPIs

- cobertura de narração: diferença timeline–áudio ≤ 0,75 s;
- zero imagens ilegíveis ou sem provenance;
- zero captions sobrepostas ou fora do áudio;
- zero motion gate failures;
- % de cenas com intenção visual explícita;
- retenção no primeiro beat, primeiro reveal e payoff;
- queda de retenção após cada troca de imagem;
- taxa de renders reprovados por causa técnica;
- claims de copyright por episódio: alvo zero;
- disclosure aplicado quando o conteúdo realista sintético exigir.

## 18. Feedback loop

`execução → preview → revisão humana → final → publicação → retenção/claims →
diagnóstico por beat → ajuste de roteiro, plano ou motion → próxima execução`.

Antes de haver dados de canal, não se deve fingir que existe aprendizado
estatístico. Os primeiros uploads formarão o baseline; retenção média isolada é
insuficiente para atribuir causalidade.

## 19. Tratamento de falhas

- caminho inválido: aborta antes do FFmpeg;
- WAV inválido: aborta;
- imagem corrompida/pequena: validator aborta;
- timeline incompatível: aborta;
- motion/easing inválido: aborta;
- repetição de movimento: aborta;
- captions fora do áudio: aborta;
- saída parcial: nunca promove o arquivo;
- final sem aprovação: workflow bloqueia;
- música sem licença quando requerida: aborta;
- falha de provider: não troca provider silenciosamente.

## 20. Checklist operacional

- [ ] roteiro factual revisado;
- [ ] narração final e duração conhecida;
- [ ] beats e payoff marcados;
- [ ] uma imagem autoral por beat;
- [ ] sidecar de cada imagem;
- [ ] sem falso documento/evidência;
- [ ] motion explícito ou selecionado pelo engine;
- [ ] sem shake;
- [ ] captions externas e legíveis;
- [ ] timeline compatível;
- [ ] preview validado;
- [ ] revisão em celular;
- [ ] aprovação hash-bound;
- [ ] licença/disclosure verificados;
- [ ] final validado;
- [ ] métricas pós-publicação registradas.

## 21. Riscos que ainda permanecem

O motor não pode garantir monetização; decisão de plataforma é externa. Imagens
autorais ainda podem parecer genéricas se o plano visual for fraco. A licença de
uma fonte externa continua exigindo leitura humana dos termos. Retenção só pode
ser otimizada depois de dados reais. O renderer estável reduz jitter, mas não
substitui revisão estética.

## 22. Veredito final

O motor não deve ser reconstruído do zero. A fundação está correta e deve ser
preservada. O upgrade necessário é concentrado na camada de montagem: motion
determinístico, subpixel, contextual e auditável, junto com timeline audio-first
e gates de qualidade. Depois deste commit, o motor está apto para um novo
preview técnico; ainda não se deve declarar um episódio final aprovado sem
renderizar e assistir esse preview no celular.

## Classificação final

- **Corrigir agora:** renderer/motion/timeline/gates (implementado nesta etapa).
- **Implementar:** registro de licença, disclosure e relatório de retenção.
- **Testar:** preview Mars com assets completos e S03 válido.
- **Monitorar:** tempo de render final, retenção, claims, legibilidade.
- **Manter como está:** isolamento, provenance, captions externas, approval gate.
- **Remover:** shake, randomização não auditável e fallback silencioso.
