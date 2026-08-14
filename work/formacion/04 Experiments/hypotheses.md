# Hipótesis

## Hipótesis activas

### H1 — Mejor señal no implica mejor PnL

Una mejora en `IC` o `Rank IC` puede no traducirse en mejor rendimiento neto de portfolio.

**Estado:** apoyada por la evidencia actual.

**Evidencia:** la variante tuned mejora señal pero empeora `IR` y drawdown frente al baseline.

### H2 — La capa de portfolio puede desbloquear edge latente

Una señal que parece inferior en PnL bajo una cartera dada puede monetizarse mejor con otra política de construcción de cartera.

**Estado:** apoyada parcialmente.

**Evidencia:** `tuned + top30` y `tuned + top20` recuperan parte del rendimiento perdido.

### H3 — Más concentración compra retorno a costa de fragilidad

Al concentrar más la cartera, puede subir el retorno anualizado pero empeorar el perfil de riesgo.

**Estado:** apoyada por la evidencia actual.

**Evidencia:** `top20/n_drop2` supera al baseline en retorno anualizado con costes, pero empeora claramente drawdown e `IR`.

## Hipótesis siguientes razonables

### H4 — El sizing puede encontrar un punto medio mejor que solo tocar `topk`

Ajustar pesos o tamaño de posición podría preservar más retorno que la cartera baseline, sin asumir tanto drawdown como `top20`.

**Estado:** no probada.

**Cómo falsarla:**

- ejecutar variantes de sizing sobre la señal tuned manteniendo universo, features y modelo fijos
- comparar al menos retorno con costes, `IR`, drawdown y turnover

**Criterio de apoyo inicial:**

- alguna variante mejora claramente a `tuned + top30` o `tuned + top20` en equilibrio riesgo-retorno
- o reduce drawdown/materialmente sin destruir toda la mejora de retorno

**Evidencia nueva (2026-05-10):** la variante `tuned_softtopk20` ya pudo ejecutarse completa (`run 3b121593ab2b45cea2bd85467a6302fc`) tras corregir fallos de strategy/backtest, pero el resultado fue flojo: `Ann. Return with cost 0.0329`, `IR 0.2635`, `Max Drawdown -0.2433` con `IC 0.0589` y `Rank IC 0.0495`.

### H5 — Otra familia de features puede mejorar robustez sin forzar concentración

Un cambio de features podría dar una mejora de señal más compatible con buen comportamiento de portfolio.

**Estado:** no probada.

**Cómo falsarla:**

- sustituir la familia de features manteniendo `csi300` y una política de portfolio comparable
- contrastar si la mejora, si existe, aparece tanto en señal como en monetización

### H6 — Parte del deterioro observado en variantes agresivas viene de fricción operativa, no solo de mala señal

Una parte relevante de la caída en robustez de variantes más activas o concentradas puede venir de costes efectivos y rotación, no únicamente de menor calidad predictiva.

**Estado:** no probada.

**Origen:** materiales de `formacion/` sobre `min_cost`, coste por orden y turnover.

**Cómo falsarla:**

- comparar baseline y variantes agresivas bajo varios supuestos razonables de costes
- medir el turnover junto a retorno, `IR` y drawdown

**Criterio de apoyo inicial:**

- si una parte no trivial de la degradación desaparece o se reduce mucho al variar el modelo de costes

### H7 — Una label menos ruidosa puede mejorar la transferibilidad de señal a PnL

Ampliar el horizonte de la label, por ejemplo de 1 día a 5 días, puede producir una señal menos ruidosa y más fácil de monetizar en portfolio.

**Estado:** apoyada por la evidencia actual.

**Origen:** `Temas Pendientes Qlib` y materiales de estrategias sobre horizonte de predicción.

**Cómo falsarla:**

- entrenar una variante con horizonte más largo manteniendo lo demás fijo en la medida de lo posible
- comparar no solo `IC` y `Rank IC`, sino también el resultado neto con una política de cartera equivalente

**Criterio de apoyo inicial:**

- mejora conjunta de estabilidad de señal y comportamiento de portfolio
- o al menos mejor alineación entre señal y monetización que en la tuned actual

**Evidencia nueva (2026-05-10):** `label5d` (`run 942aed50889d44f493a0d98ebda0c38f`) logró `IC 0.0760`, `Rank IC 0.0793`, `Ann. Return with cost 0.1620`, `IR 2.1507` y `Max Drawdown -0.0780`, superando tanto al baseline anterior como a la familia tuned conocida.

### H8 — Hace falta un criterio explícito de promoción de modelos que combine señal y monetización

Seleccionar modelos solo por `IC`, `Rank IC` o `ICIR` puede promover variantes peores en uso real; hace falta un criterio compuesto que incorpore monetización y fricción.

**Estado:** parcialmente apoyada por la evidencia actual.

**Cómo falsarla:**

- definir un criterio compuesto y verificar si ordena mejor los runs conocidos que una métrica de señal aislada
- comprobar si ese criterio reduce promociones erróneas en nuevas variantes

**Criterio de apoyo inicial:**

- el criterio compuesto reproduce mejor la preferencia actual por el baseline que `IC` aislado
- y sigue siendo útil al añadir nuevas variantes
