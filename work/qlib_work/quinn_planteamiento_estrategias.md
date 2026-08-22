# 🧭 Quinn — Veredicto sobre el planteamiento de paper-trading en paralelo (Momentum puro vs Momentum + filtro PEAD)

> **Autor:** Quinn (Investment Research senior, buy-side)
> **Para:** Toni
> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Scope:** evaluación del planteamiento de dos estrategias en paper + cronjobs semanales. Respuestas A–E.

---

## 1. Veredicto general

**El planteamiento es conceptualmente correcto pero está metodológicamente adelantado a su propia evidencia.** Correr dos estrategias en paralelo (misma señal de ranking, mismo topk, mismo rebalanceo, única diferencia = filtro PEAD negativo) es un diseño de comparación *controlada* limpio — de hecho es la forma correcta de aislar el efecto del filtro frente a la alternativa de z-score sumado (Sharpe 0.57 vs 1.0) que ya descartaste bien.

**El problema no es el diseño, es el estado de madurez de la Estrategia 2.** A día de hoy la estrategia 2 **no tiene backtest out-of-sample propio**: su único "rendimiento" (−1.78%) proviene de *reconstruirla retroactivamente sobre los mismos 2 rebalanceos* que luego la muestran "ganando" a la 1 (−2.45%). Ese resultado es, en el mejor de los casos, ruido compartido de factor; en el peor, un artefacto de *selección sobre el resultado* (definimos la estrategia después de ver que "funcionaba"). Con ~8 días de datos y holdings casi idénticos, la brecha de 67 bps **no significa nada** y, además, en agosto la "última sorpresa" es de Q2 (julio), es decir vieja y estática, por lo que el filtro casi no debería disparar — las dos carteras convergen.

**Prioridad:** (1) validar la estrategia 2 con un backtest OOS real antes de confiar en el paper; (2) disciplina *point-in-time* y calidad de datos en el cron; (3) medida de sorpresa adecuada (SUE, no surprise% crudo) con ventana de validez; (4) diagnóstico (cuántas names excluye el filtro), no solo P&L. Todo lo demás es sobreingeniería en esta fase.

---

## 2. Respuestas A–E

### A) ¿Es sólido correr las dos estrategias en paper paralelo? ¿Hay sesgo?

**La estructura A/B es sólida; el sesgo está en *qué* se está comparando.**

✔️ **Lo correcto:** mismo universo (sp500_liquid, 292), mismo topk 30, mismo rebalanceo semanal, misma política de costes IB. La única variable que cambia es el filtro. Eso es el control limpio que pide el rigor. Mantener las dos vivas en paralelo es **deshacer el sesgo de "elegir resultado ganador"**: si solo corrieras la 2, nunca sabrías si su comportamiento es por el filtro o por el régimen.

⚠️ **El sesgo real (y no es menor):** la estrategia 2 fue *reconstruida retroactivamente* (14→22-ago) para la comparación. Esto la convierte en **in-sample**: se definió/ajustó sobre los mismos 2 rebalanceos que ahora se usan para evaluarla. Su −1.78% no es evidencia fuera de muestra; es exactamente el tipo de dato sobre el que no se puede concluir nada. La 1, en cambio, sí tiene IC OOS +0.066 validado y Sharpe ~0.9–1.1.

⚠️ **Beta compartida:** ambas estrategias cargan el mismo factor momentum/market el mismo periodo (ambas ~−2%). No son dos observaciones independientes de alpha; son dos réplicas del mismo drawdown de factor (en su portfolio real, META −6.8% / MSFT −2.5% esa semana muestran el mismo régimen). La diferencia de 67 bps está dentro del solapamiento de holdings, no es señal de habilidad diferencial.

**Conclusión A:** el *formato* de comparación paralela merece la pena y debe mantenerse; pero **trátala como una prueba pre-registrada de una hipótesis (filtro PEAD mejora el momentum) cuyo brazo #2 todavía está sin validar**, no como dos estrategias equivalentes compitiendo con datos limpios desde el día 1.

---

### B) ¿El filtro "última sorpresa conocida" es la implementación correcta? Matices

Dirección conceptualmente correcta; tres matices importantes:

1. **Usa SUE (o sorpresa normalizada), no surprise% crudo.**
   `surprise% = (EPS_real/EPS_estimado − 1)` no está escalado por la incertidumbre de la estimación. Un ticker poco cubierto/alta vol puede sorprender −20% "normalmente"; uno mega-cubierto jamás. El umbral fijo de −5% sobre surprise% **no es comparable entre tickers**.
   `SUE = (EPS_real − EPS_consenso) / σ(error histórico de estimación)` escala por la volatilidad del error → el umbral es significativo en unidades de dispersión. Si no tienes histórico para σ, al menos estandariza por la *vol del precio* alrededor del anuncio o por el rango intercual de sorpresas del propio ticker.

2. **Ventana de validez de la sorpresa (crítico).**
   "Última sorpresa conocida" está bien como *point-in-time* **si y solo si** la tratas como información solo dentro de su ventana de drift (20–60 días tras el anuncio; el drift es más fuerte a ~20d). Una sorpresa de hace 60+ días ya está en el precio: excluir por ella es inútil o contraproducente (excluyes un nombre que ya revertió).
   **Regla propuesta:** el filtro solo aplica si `reported_date` está dentro de un horizonte fresco (p.ej. ≤ 20–40 días hábiles). Si la última sorpresa es vieja → no información → no excluir.

3. **Caso sin datos / sin sorpresa reciente.**
   Define explícitamente qué pasa si un top-30 no tiene sorpresa en ventana: por defecto *no excluir* (conservador, correcto), pero debe ser una regla explícita y registrada, no un comportamiento aleatorio.

4. **Efecto realista del filtro.**
   Que un top-30 tenga momentum alto **y** acabe de reportar sorpresa < −5% es un evento poco frecuente (la mala sorpresa suele ya haber tumbado el momentum). El filtro probablemente dispara sobre 0–3 names/semana en temporada y ~0 entre temporadas. Eso es exactamente su papel preciso — **pero significa que las dos estrategias son casi idénticas la mayor parte del año** → esto impacta la potencia de la comparación (ver D/E). Mide cuántas names excluye cada semana; si es ~0, el test no tiene poder y conviene admitirlo en vez de dejar que el ruido decida.

**Conclusión B:** implementación *direccionalmente* correcta, pero sube el estándar: → SUE/normalización, → ventana de frescura, → regla explícita de datos ausentes, → registrar cuántas names excluye. El surprise% crudo con umbral fijo es el eslabón más débil.

---

### C) Cronjob semanal de earnings: ¿sobrescribir el CSV es correcto? ¿Desalineación temporal?

**El calendario importa, y en agosto hay una desalineación real:**

📅 **En agosto la última sorpresa es de Q2 (reportado en julio).** Q3 no sale hasta oct–nov. Por tanto el campo "última sorpresa conocida" es **estático durante casi todo el verano** → el filtro no cambia de semana a semana → las dos estrategias convergen. No es un bug del cron, es la naturaleza del dato: **el dato de earnings solo es "fresco" en las 4–6 semanas posteriores a cada temporada de resultados** (en/abr, abr/may, jul/ago, oct/nov). El cron semanal es cadencia correcta, pero la *información* solo es relevante alrededor de esas ventanas.

⚠️ **Sobrescribir el CSV completo es tolerable solo si es idempotente y point-in-time-safe.** El peligro real de "sobrescribir" es:
- Si al regenerar se *retro-rellenan* o *corrigen* trimestres viejos → **look-ahead**: el filtro usará sorpresas que no estaban disponibles en la fecha de rebalanceo.
- Si el fetch falla y el cron vuelve a "sobrescribir" con datos NaN/stale → corrompe el último CSV bueno.

**Regla de oro:** el CSV debe ser un **historial apéndice-only** indexado por `(ticker, quarter, reported_ts)`:
- Las filas **nunca se borran ni editan**; cada semana se **añaden** los anuncios nuevos.
- El filtro lee solo filas con `reported_ts <= fecha_de_rebalanceo`.
- Guarda copia versionada (p.ej. `pead_v2.csv` + timestamp) para poder auditar/reproducir.
- Añade un guard: si el fetch devuelve 0 anuncios nuevos o falla → **no sobrescribir**, loggear y alertar, conservar el estado anterior.

**Mejor momento para actualizar earnings:** corre el fetch de forma consistente (sábado funciona como cadencia), pero para que el filtro sea significativo programa una **ráfaga de actualización justo después del pico de cada temporada de resultados** (la semana posterior a que el grueso de Q2/Q3/Q4/Q1 haya reportado). El orden del cron (precios → earnings → sim 1 → sim 2) es correcto; lo que hay que garantizar es *integridad temporal* del dato, no solo el orden de ejecución.

**Conclusión C:** el cron semanal está bien como cadencia; el problema no es la frecuencia sino (1) que en agosto el dato es viejo/estático (no desalineado, *vacío informativo*), y (2) que "sobrescribir" sin historia ni guard introduce riesgo de look-ahead y pérdida de datos. → Historial append-only + guard + ráfaga post-temporada.

---

### D) ¿Es significativo −2.45% vs −1.78% con 2 semanas? ¿Ruido?

**Es ruido.** Sin ambigüedad.

- **N observaciones efectivas ≈ 1–2 rebalanceos** de ~8 días hábiles. Esa es la unidad estadística real de la comparación, no "2 semanas".
- Los holdings están casi solapados (la 2 difiere de la 1 solo en las names excluidas), así que las dos series están **altamente correlacionadas** → incluso un gap de 67 bps tiene un error estándar gigantesco relativo al efecto que intentas medir. Con 1–2 rebalances no puedes rechazar "ambas son iguales".
- **Ambas caen ~2% = drawdown del factor momentum/market**, no skill. Es la misma beta que ves en tu portfolio real (META −6.8%, MSFT −2.5%). En un régimen de caída del momentum, "-1.78 vs -2.45" es simplemente dos names que te tocó no tener/no tener — suerte de cartera, no ventaja del filtro.
- **Y es peor que ruido estándar:** la 2 fue *reconstruida después* de ver el resultado, así que hasta el −1.78% está sesgado a favor (optimismo por selección sobre el outcome).

**¿Cuándo valdría la pena?** Criterio falsable razonable: cuando tengas **≥ 24–50 rebalanceos acumulados (6–12 meses) que crucen al menos una temporada de earnings completa**, y además:
- El filtro haya excluido un número no trivial de names (si excluye ~0, el test no tiene potencia).
- La diferencia supere el coste del filtro (turnover/transacción extra) y se mantenga consistente entre temporadas, no en un solo tramo.
- Idealmente significar con un t-stat sobre retornos semanales *apareados* (pues las carteras no son independientes).

**Conclusión D:** no interpretes nada de los dos primeros rebalanceos. Documenta el número de rebalances y la correlación de las series; el veredicto honesto es "aún sin poder estadístico".

---

### E) ¿Qué falta para que sea riguroso y los cron fiables? (priorizado)

1. **Backtest OOS real de la estrategia 2 (crítico, antes de confiar).** Walk-forward de la estrategia filtrada sobre el histórico completo, comparando su Sharpe/drawdown standalone contra los de la 1 (Sharpe ~0.9–1.1, maxDD −19%). Si el filtro no mejora el Sharpe standalone **y** no reduce el drawdown, el paper paralelo es puro ruido. Este es el hueco número 1.
2. **Disciplina point-in-time + calidad de datos.** Historial de earnings append-only con `reported_ts`; el filtro solo lee `reported_ts <= decisión`; guard anti-fallo en el cron; logs y alertas; copias versionadas de los CSV. Sin esto, cualquier "resultado" posterior es potencialmente un artefacto de look-ahead.
3. **Medida de sorpresa robusta + ventana de validez.** SUE (o normalización), no surprise% crudo; sorpresas > ~40 días hábiles no cuentan; regla explícita para datos ausentes.
4. **Diagnósticos, no solo P&L.** Por cada rebalanceo: cuántas names excluye el filtro, turnover de cada estrategia, IC de cada ranking vs retorno a 20d/5d, beta/exposición, max drawdown, costes aplicados. Si el filtro excluye ~0 names → el diseño pierde potencia → sácalo a la luz en vez de dejar que el ruido decida.
5. **Costes reales en ambas.** El reequilibrio de la 2 (sustituir names a veces ilíquidas) puede ser más caro que la 1. Ambas deben usar el mismo modelo de costes IB, y la 2 debe *pagar* el coste de su filtro.
6. **Decisión pre-registrada y punto de final.** Define ANTES: "tras 6 meses / 24 rebalances, promuevo la 2 si tiene mayor Sharpe y menor/igual DD que la 1 con turnover aceptable; la mato si queda dentro del ruido". Esto evita mover el post en cada drawdown.
7. **Conciencia de concentración de temporada.** Como el filtro solo "muerde" cerca de earnings seasons, programa una ráfaga de actualización post-temporada y ajusta la expectativa: la comparación no acumula poder linealmente con el tiempo, sino por temporadas.

---

## 3. Convicción y señales de alarma

**Convicción (declarada):**
- 🟢 **Alta:** el momentum 120d es un alpha genuino y validado (IC OOS +0.066). El uso del PEAD como **filtro/refuerzo** (no como señal de ranking sumada) es conceptualmente correcto y coherente con tu propia evidencia (la suma dio Sharpe 0.57 vs 1.0). La arquitectura A/B paralela es el diseño adecuado — mantenerla.
- 🟡 **Media:** que el filtro PEAD añada valor *en vivo* sobre el momentum. Es una hipótesis plausible y no contraria a la literatura, pero aún sin validación OOS propia de la variante con filtro.

**Señales de alarma (en orden de importancia):**
1. **⚠️ La estrategia 2 no tiene backtest OOS propio.** El −1.78% es un artefacto de reconstrucción retroactiva (in-sample/outcome). Es el riesgo más grande y el más fácil de corregir (un walk-forward).
2. **⚠️ −2.45% vs −1.78% en 2 semanas es ruido + beta compartida del factor momentum**, no evidencia diferencial. No dejes que 8 días decidan nada.
3. **⚠️ La "última sorpresa" en agosto es de Q2 (jul): vieja y estática.** En temporadas sin earnings el filtro casi no dispara → las dos estrategias convergen → la comparación tiene poca potencia la mayor parte del año. Si el filtro excluye ~0 names/semana, el test está infra-potenado y hay que decirlo.
4. **⚠️ Sobrescribir el CSV de earnings sin historial ni guard** = vía abierta a look-ahead y a corromper el último dato bueno si el fetch falla silenciosamente.
5. **ℹ️ Concentración de régimen en tu portfolio real** (AAPL/GOOGL/MSFT/META ~97% del valor, META −17%) — no es el paper topk-igualitario, pero ilustra que una sola "mega" puede dominar el P&L en tramos cortos: exactamente por qué 2 semanas no significan nada.

**Línea final:** el diseño es correcto y merece la pena; la *madurez de la evidencia* no justifica todavía ninguna conclusión. Primero un OOS de la estrategia filtrada, luego disciplina point-in-time en los datas y en los cron, y una decisión pre-registrada a 6 meses. El resto — hoy — es ruido que conviene no sobre-interpretar.

---

*Quinn — Investment Research senior. Documento sobre el planteamiento de paper-trading en paralelo (importante: no sobre-interpretar 2 semanas de datos).*
