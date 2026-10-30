# Cinematic Dread — camada de atmosfera por cena (V7.3 visual)

## Compatibilidade
O motor principal atual **já é V7.3 Charon/Gemini TTS**. Este pacote é
**um recurso visual opcional** (`cinematic_dread_v1`), não outra engine,
nem troca de voz, esquema, hash, HUD, legendas, direitos ou master prompt.

Até existir preview editorial aprovado, manter `director_review=PENDING` e
não modificar `production/active_engine_policy.json` nem `episodes/video-001/manifest.json`.

## Função
- O roteiro determina as batidas de suspense; as cenas recebem níveis de 1 a 4.
- Presets graduais: inquietação, suspeita, ameaça, impacto.
- A gradação é realizada **no clipe** antes das legendas e da HUD: frio,
  dessaturação contida, sombras densas, vinheta e granulação mínima.
- Nada de inventar portas, neblina, silhuetas, reflexos ou luzes vermelhas.
- A trilha licenciada atual continua intacta; só o nível do **mix de fundo**
  acompanha cada segmento da história, sob o sidechain da voz.
- QA mede luminosidade na área central da imagem e exige aprovação editorial.
- Clipes usados em um episódio **nunca** são reciclados em outro, mesmo com
  novas cores ou textura; Reuse First reutiliza cache apenas no MESMO episódio.

## Manifesto opt-in
Adicione somente quando houver autorização de teste:

```json
"atmosphere": {
  "enabled": true,
  "profile": "cinematic_dread_v1",
  "director_review": "PENDING",
  "scene_overrides": {
    "S04": {"intensity": 3, "reason": "A chegada ao andar impossível muda a ameaça"}
  }
}
```

A intensidade não é uma luminância absoluta e não controla publicação.
Valores inválidos bloqueiam. Níveis não informados derivam de story_beat;
batidas desconhecidas recebem progressão temporal sinalizada para revisão.

## Gates e testes
1. Contrato da cena (IDs únicos, preset aprovado, override documentado).
2. Preservação da narração/legenda/logo; sem texto adicional.
3. Limites técnicos de exposição/contraste, duração e sincronização.
4. Comparação lado a lado aprovada por pessoa; QA automático não valida
   emoção, direção de fotografia nem direitos dos clipes.
5. Produção comercial permanece condicionada aos gates V7 existentes.

**Rollback:** ausência de `atmosphere` = filtro e mix originais inalterados,
sem fallback silencioso. Rejeitar publicação se a estética nova não tiver
aprovação.
