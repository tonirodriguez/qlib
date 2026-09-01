# 🎯 Plan de Acción — De momentum-pilar a PEAD-núcleo + momentum-táctico (semanas 1-8)

**Autor:** Quinn · Investment Research Senior (14+ años buy-side)
**Sujeto:** Toni · proyecto Qlib (lab + paper-trading €20k)
**Fecha:** 2026-08-22
**Base verificada:** momentum 120d NO robusto (purged CV, régimen-dependiente: IC −0.10 a −0.13 en 2020-23 vs +0.02 a +0.065 en 2023-26) · PEAD SÍ robusto (purged CV: IC Spearman +0.085@20d a +0.130@60d).

---

## 0. ⚠️ Reglas de honestidad que gobiernan TODO este plan

1. **No racionalización.** El purged CV no te da permiso para "esperar al régimen correcto". Te dice: *no dependas del momentum autónomo*. El plan lo asume desde el día 1.
2. **No sobreapostar PEAD.** PEAD es robusto en ~6 años de una muestra; es prometedor, no certidumbre. Lo tratamos como núcleo *modesto*, no como magia.
3. **Separar régimen vs decaimiento.** "Régimen" (vol/crisis condiciona el IC) y "decaimiento secular" (el factor perdió eficiencia) producen acciones distintas. El laboratorio debe separarlas — ese es uno de sus objetivos explícitos.
4. **Paper-time = laboratorio barato.** 100% del riesgo es ficticio. Este es el momento de corregir la arquitectura, no después con capital real.
5. **Prohibido el detector sofisticado ahora.** HMM/Markov = benchmark académico de laboratorio, jamás capa de producción mientras no supere al vol-gating con holgura en múltiples transiciones.

---

## 1. PILAR DEL PLAN: convertir la Estrategia 2 en "PEAD-núcleo + momentum-táctico"

### 1.1 Diagnóstico de la arquitectura actual
Hoy tienes **2 simuladores gemelos** (`simulate.py` → `state.json`, `simulate_pead.py` → `state_pead.json`) que son **el mismo momentum topk-30**; la diferencia es que el 2º añade un *filtro negativo* (SUE < −2σ fresco) que saca del topk a los tocados por earnings malos.

**El problema de fondo:** en ambos, el **rank principal y el apalancamiento del capital es momentum**. El PEAD solo *vetas* nombres; no aporta convicción positiva. El plan invierte los papeles.

### 1.2 Nueva arquitectura objetivo (Estrategia 3 — `estrategia_pead_nucleo`)
**Un solo simulador nuevo en lugar de parchear los dos:** `work/estrategias/simulation/simulate_pead_core.py` con `state_pead_core.json`. No tocar los 2 existentes (ver §4).

**Selección de cartera (dos libros de capital separados, misma cuenta ficticia):**

- **LIBRO NÚCLEO — PEAD (60-70% del capital).**
  - Ranking por **sorpresa signada reciente** (SUE del último anuncio *dentro de la ventana de frescura*; usa `load_last_surprise()` ya escrito en `simulate_pead.py`).
  - Topk PEAD = 20-25 nombres con mayor SUE positivo fresco (long-only, PEAD positivo es long).
  - Rebalanceo **semanal** (mismo cronjob fijo). Cada ticker que reporta earnings se "renueva" su señal; los que superan la frescura se degradan/procesan como vencidos → **captura el drift de 20-60d de forma natural**.
  - Capital igualitario entre los 20-25 (peso ~3-4% c/u). **Nunca >30 posiciones** para mantener costes IB bajos (30 órdenes ≈ $10.5 + SEC/TAF).

- **LIBRO TÁCTICO — Momentum (30-40% del capital, techo duro 50%).**
  - Ranking momentum 120d (código ya existente).
  - Topk 10-12 sobre el resto del capital.
  - **VOL-GATING obligatorio** (sección §3): el momentum solo despliega su capital pleno cuando la vol realizada del SP500 está en zona normal; se reduce a 1/3 o se pausa en zona alta.

**Regla combinada:** los pesos **no se eligen por un oráculo**, son fijos (núcleo 60-70 / táctico 30-40) y solo el *vol-gating* modula el libro táctico. El sobrepeso a momentum **nunca** supera el 50% del total, en línea con la recomendación previa.

**Archivos concretos a crear:**
- `simulate_pead_core.py` (simulador combinado, reutilizando `load_last_surprise`, `ib_trades_cost`, `get_prices` de los existentes — refactoriza esas funciones a un `sim_utils.py` común).
- `state_pead_core.json` (estado; distinto de los 2 actuales).
- Entrada nueva en crontab sábado: `17:00 sim estr3` (tras los 2 actuales).

**Decisión de arquitectura honesta:** NO intentar "PEAD long + momentum en los mismos topk con pesos combinados por nombre" (complejo, poco turnover de PEAD vs alto de momentum choca). **Libros separados = 2 fuentes de retorno ortogonales, cada una con su gestión.** Más simple y testable.

---

## 2. LABORATORIO: demostrar la dependencia de régimen con rigor

Objetivo: pasar de "sospecha en 2 ciclos" a "afirmación cuantificada" **o** descartarla limpiamente. Dos hipótesis competidoras, separadas.

**Script nuevo: `work/estrategias/regimen_test.py`** (extiende `momentum_purgedcv.py`). Estructura:

1. **Backtest extendido hacia atrás** — más transiciones, no más datos del mismo régimen.
   - Extiende `END` hacia atrás todo lo que el universo permita y, sobre todo, añade **ex-regímenes** (2008-09, 2015-16, 2018) usando el universo SP500 de Qlib aunque sea con lista de tickers más sucia/constante. El objetivo: **≥4 transiciones alcista→bajista** observadas, no 1-2.
   - Documenta el trade-off: más historia = más survivorship bias. Anótalo explícitamente.

2. **IC condicionado por ESTADO, no por ventana de 3 años.**
   - Define estado por proxys objetivos: (a) vol realizada 20d del SP500 en percentil >75/80 = "estrés"; (b) `market_in_drawdown` (retorno 120d del SP500 < 0); (c) índice **Momentum Crash indicator** (retorno del decil perdedor > retorno decil ganador, estilo Daniel-Moskowitz).
   - Calcula `IC_spearman(momentum, fwd_60d)` **dentro de cada estado**, con CI boostrap (percentiles 2.5-97.5, 1000 remuestras).
   - **Clave:** reporta si los CI de "estrés" vs "calma" se solapan. Si se solapan, NO puedes afirmar "técnicamente distinto" — solo "direccionalmente consistente".

3. **Regresión de interacción formal** (statsmodels):
   - `IC_momentum_t ~ a + b·market_ret_t + c·I(vol_alta)_t + d·momentum_crash_t + e`, donde `I(vol_alta)` es el estado en t.
   - La hipótesis de régimen exige: coeficiente **c (o d) significativo, negativo y estable** a través de re-muestreos por bloque temporal (cluster-robust SE por año).
   - **Contraste con decaimiento:** corre la misma regresión sobre el **tiempo calendario** (`IC ~ tiempo` + estado). Si el término de tiempo es negativo y significativo mientras el de estado no, el problema es **decaimiento secular**, no régimen → la respuesta es reducir size, no añadir régimen.

4. **Hipótesis falsable POR ESCRITO antes de correr** (métrica pre-registrada, no muevas el arco tras ver el resultado):
   > "El momentum es régimen-dependiente" se **falsifica** si, con ≥4 transiciones y CI honestos, el IC condicionado a estados de estrés NO difiere sistemáticamente (en dirección y magnitud) del IC en calma — es decir, si `c` no es significativo o los CI se solapan.

**Entregable:** `work/qlib_work/regimen_test_resultado.md` con tabla por estado, coeficientes, CI, y veredicto régimen-vs-decaimiento.

**Script de apoyo:** `work/estrategias/extract_estados.py` para construir la serie de estados (vol pct, drawdown, momentum-crash) y guardarla en CSV para que `regimen_test.py` la consuma.

---

## 3. PROTOTIPO de vol-gating simple (NO HMM)

**Script nuevo: `work/estrategias/vol_gate.py` + `vol_gate_test.py`.**

1. **Métrica:** vol realizada 20d del SP500 (retornos diarios del índice, desv. anualizada) y/o percentil de la serie histórica.
2. **Regla simple (umbral con histéresis para evitar churn):**
   - `vol_pctile_20d < P75` → gate = 1.0 (momentum a pleno)
   - `P75 ≤ vol_pctile < P90` → gate = 0.5 (momentum a la mitad)
   - `vol_pctile ≥ P90` → gate = 0.0 (momentum pausado, el libro táctico pasa a cash)
   - **Histéresis:** permanecer en estado bajo durante ≥N rebotes (p.ej. el gate no sube hasta que la vol baje de P70, no de P75) para no apagar/encender cada día.
3. **Frecuencia de evaluación:** semanal, en el mismo rebalanceo (coherente con cronjobs). Sin lógica intradía.
4. **Integración:** si el prototipo lo valida, el gate se aplica en `simulate_pead_core.py` reduciendo el capital desplegado del libro táctico (los pesos del núcleo PEAD no cambian — el PEAD es long y no se gatea por vol de índice).
5. **Medición de efecto real** en backtest: comparar momentum puro vs momentum+gate vs momentum+gate con distintos umbrales (P70/P75/P80) sobre **Sharpe, max-drawdown, turnover y costes IB netos**. No solo Sharpe: el gate debe reducir drawdown **sin** carcomer el retorno por el lag.
6. **Criterio de promoción:** solo si con *todos* los umbrales razonables (grid-guardado, no el mejor elegido) el gate mejora Sharpe neto o reduce ≥20% el max-DD. Si solo "gana" con el umbral óptimo sobre elegido, es overfit — no lo promuevas.

**NO construir HMM.** El vol-gating se valida contra momentum puro; HMM queda como nota académica en `quinn_regimenes.md` (ya documentado) y jamás en producción hasta que demuestre superar al gate con holgura en ≥4 transiciones.

---

## 4. QUÉ HACER CON LAS 2 ESTRATEGIAS ACTUALES EN PAPER

**Mantener ambas como MONITOR, no como apuestas principales. No crear 3ª en paralelo a las 2 — la 3ª ES la nueva arquitectura.**

| Estrategia | Qué hacer | Estado / archivo | Peso imputado |
|---|---|---|---|
| **E1 momentum 120** (`simulate.py`) | **Seguir monitorizando** (ya −2.45%). Es tu línea base de "qué pasa si no cambio nada". Útil como experimento de control. | `state.json` | monitor, no apuesta |
| **E2 momentum+filtro PEAD** (`simulate_pead.py`) | **Congelar decisiones ahí.** Sigue corriendo (auto, sin coste de mantenimiento) pero **no reasignes capital nuevo pensando en ella**; su lección ya se tomó (invertir pesos). | `state_pead.json` | monitor |
| **E3 PEAD-núcleo + momentum-táctico** (`simulate_pead_core.py`) | **La nueva estrategia.** Arranca en semana 1-2 con el diseño §1. | `state_pead_core.json` | **la apuesta** |

**Regla de mantenimiento:** no elimines E1/E2 ni borres sus estados — son la prueba viva de *por qué* cambiaste. Documenta en `qlib_work/` un `comparativo_estrategias_2026-08-22.md` con los 3 P&L lado a lado desde hoy.

**Capital ficticio:** reponderar a E3 es gratis en paper. Pero para no partir de cero, al crear E3 **reinicia con un capital equivalente** al valor actual de la cartera real (€~19,6k), no con €20k, para comparar P&L de forma justa contra E1/E2.

---

## 5. CRITERIOS DE ÉXITO / DECISIÓN / CUÁNDO PARAR

### 5.1 Éxito del plan (semanas 1-8)
- ✅ E3 desplegada y corriendo en paper con arquitectura PEAD-núcleo + momentum-táctico (≤50% momentum, vol-gate activo).
- ✅ `regimen_test.py` con veredicto claro: régimen confirmado **o** descartado/decaimiento — con CI y coeficientes, no puntos.
- ✅ `vol_gate.py` validado con grid-guardado y decisión documentada de promover o no.
- ✅ Documentación honesta actualizada (resultados + decisiones en `qlib_work/`).

### 5.2 Cuándo PARAR / PIVOTAR (alarmas accionables)
1. **El PEAD también se degrada** en paper (P&L E3 plano/negativo sostenido con PEAD-núcleo). → **Parad el proyecto de señales individuales.** El problema ya no es de régimen ni de reponderar: es del espacio completo de señales. Reducid exposición y reevaluad la premisa de que hay alpha gestionable con 2 señales en esta muestra.
2. **El vol-gating solo "funciona" con el umbral óptimo sobreajustado** → no promuevas; queda en laboratorio. Acepta momentum a peso bajo y techo duro sin gate si el gate no aporta robusto.
3. **Después de las 8 semanas, sin métricas honestas** → no escales. Sigue en paper-time. El capital real jamás entra mientras el diseño dependa de un factor único (momentum o PEAD).
4. **CI de estados que se solapan** → no declares "2 regímenes"; declara "direccionalmente consistente pero no distinguible en esta muestra". Eso baja la urgencia de cualquier régimen-detectador.

### 5.3 Criterio final de "distintas señales sí sirven juntas"
Si E3 (PEAD+gate) estabiliza el drawdown y bate a E1 y E2 en riesgo-ajustado neto a las 8 semanas → el reponderamiento fue la solución, el detector era prescindible. Si aun así la cartera total es frágil, el siguiente experimento es diversificar a una **tercera señal ortogonal** (factor value/quality del lab, no más momentum), no un régimen-detectador.

---

## 6. CRONOGRAMA SEMANAS 1-8

| Semana | Foco | Acciones concretas | Entregable |
|---|---|---|---|
| **1** | **Arquitectura E3** | Refactor `sim_utils.py` (extraer `get_prices`, `load_last_surprise`, `ib_trades_cost`). Escribir `simulate_pead_core.py` con libros PEAD-núcleo (60-70%) + momentum-táctico (30-40%), tope 50%. Reiniciar con capital actual. | `simulate_pead_core.py` corriendo en paper, `state_pead_core.json` |
| **2** | **Lab estado + E3 live** | `extract_estados.py` (vol pct, drawdown, momentum-crash). Ajustar crontab (17:00 E3). Primer P&L de E3 a 1 semana + comparativo con E1/E2. | `extract_estados.py`, `comparativo_estrategias_2026-08-22.md`, crontab actualizado |
| **3** | **Rigurosidad régimen** | `regimen_test.py`: backtest extendido hacia atrás (2018→ex-regímenes), IC por estado + CI boostrap, regresión interacción (statsmodels, cluster-robust). **Pre-registrar hipótesis falsable.** | `regimen_test.py`, hipótesis pre-registrada en `qlib_work/` |
| **4** | **Rigor (continuación)** | Correr backtest extendido + regresión en ex-regímenes. Contraste **régimen vs decaimiento** (término tiempo). | `regimen_test_resultado.md` (veredicto) |
| **5** | **Vol-gating** | `vol_gate.py` (umbral P75/P90 + histéresis) + `vol_gate_test.py` (grid P70/75/80 guardado, Sharpe/DD/turnover/costes). | `vol_gate.py`, `vol_gate_test.py` |
| **6** | **Vol-gating + integración** | Si valida → integrar gate en el libro táctico de E3. Si no → documento de decisión de no-promover. Comparar E3-gate vs E3-sin-gate. | `vol_gate_resultado.md`, E3 actualizada |
| **7** | **Medición / revisión** | Revisar E1/E2/E3 a 6-7 semanas. Evaluar alarmas §5.2 (¿PEAD degrada? ¿gate robusto?). Decisión de promover gate / ajustar tope de momentum. | Revisión semestral documentada |
| **8** | **Decisión + siguiente ciclo** | Decisión global (mantener/pivotar según §5). Actualizar `quinn_regimenes.md`/`README` con aprendizajes. Si todo estable → abrir pregunta de escalar (siguiente fase, AÚN sin capital real). | Plan de siguiente fase |

**Carga realista (proyecto personal):** ~2-4h/semana. Las semanas 1, 3-4 y 5 son las de más trabajo (script + ejecución + documentación). Las semanas 2, 6-7 son ligeras (dejar correr + medir). No programes más de 1-2 scripts nuevos por semana.

---

## 7. QUÉ NO HACER (anti-prioridades, por si aparece la tentación)

- ❌ **NO construir HMM/Markov detector** para producción este trimestre.
- ❌ **NO optimizar el topk / rebalanceo / ventana del momentum** en busca de "el mejor momentum". El momentum no es el problema a pulir; es el componente a tumbar a peso táctico.
- ❌ **NO sobreajustar los pesos 60/40 PEAD/momentum.** Son un punto de partida razonable, no un hiperparámetro a grid-search. La robustez viene de la estructura, no del split exacto.
- ❌ **NO meter capital real** hasta que E3 tenga un historial ininterrumpido de varias semanas y el diseño no dependa de un factor único.
- ❌ **NO mezclar el proyecto cripto (`work/crypto/`)** en este plan. Frente separado; no se toca en semanas 1-8.

---

## 8. RESUMEN EJECUTIVO (una pizarra)

> El purged CV ya te dio la respuesta. Momento: **no es tu pilar; PEAD sí es robusto.** Semana 1-2 construyes la Estrategia 3 (PEAD-núcleo 60-70% + momentum-táctico ≤50% con vol-gate), mantienes E1/E2 como monitor. Semanas 3-4 demuestras (o descartas) la dependencia de régimen con *rigor*: IC por estado con CI, regresión de interacción, y separas régimen vs decaimiento. Semana 5-6 prototipas vol-gating simple y lo integras solo si es robusto en grid-guardado. Semanas 7-8 mides E1/E2/E3 y decides. **Paras si el PEAD también se degrada** (el problema es todo el espacio de señales), jamás sobreapuestas a un factor único, y no escalas a capital real sin historial limpio. El detector sofisticado no se construye todavía. Esto es arquitectura y tamaño de posición, no más sofisticación.

---

## 🔄 Estado de ejecución (registro vivo)

| Semana | Tarea | Estado | Evidencia / Archivos |
|---|---|---|---|
| 1 | Arquitectura E3 (PEAD-núcleo + momentum-táctico) | ✅ Hecho | `simulate_pead_core.py`, `sim_utils.py`, `state_pead_core.json` |
| 2 | Lab estado + E3 live | ✅ Hecho | `extract_estados.py` → `estados_mercado.csv`; cronjob 17:00; `comparativo_estrategias_2026-08-22.md` |
| 2 | Documentar 3 KPI de estado | ✅ Hecho | `kpi_estado_mercado.md` (vol_pct, drawdown120, mom_crash) |
| 3 | Rigor de régimen (`regimen_test.py`, hipótesis falsable) | ✅ Hecho | `regimen_test.py` → **régimen confirmado**: calma IC +0.024 vs estrés −0.184 (CI no solapan); `regimen_test_resultado.md` |
| 4 | Rigor (cont. + régimen vs decaimiento) | ✅ Hecho | `vol_alta` t=−3.06 significativo; **tiempo t=+1.32 NO significativo → es régimen, no decaimiento secular** |
| 5 | Vol-gating (`vol_gate.py`, grid) | ✅ Hecho | `vol_gate.py`, `vol_gate_test.py` (motor Qlib) → **validado**: gate P75 Sharpe 1.136 vs 0.96 puro, DD −16.6% vs −19.3%; `vol_gate_resultado.md` |
| 6 | Integración vol-gate en E3 | ✅ Hecho | `simulate_pead_core.py` usa `vol_gate.py` validado (P75/P90 + histéresis) en el libro táctico |
| 7 | Medición E1/E2/E3 | ⏳ En curso | Requiere semanas de datos en paper-trading (se completará en ~6-8 semanas) |
| 8 | Decisión + siguiente ciclo | ⏳ Pendiente | Tras la medición de la S7 |

**Nota hallazgo (22-08):** el KPI `mom_crash` apenas se activa en sp500_liquid a 120d; `vol_pct` y `drawdown120` son la base del análisis de régimen. Detalle en `kpi_estado_mercado.md`.

**Documento narrativo:** la secuencia completa y motivos de E1→E2→E3 está en `evolucion_E1_E2_E3.md`.

---

## 📋 Detalle de las Semanas 7 y 8

### Semana 7 — Medición E1/E2/E3 (en curso, pasiva)

**Objetivo:** dejar que las 3 estrategias acumulen **evidencia real en paper-trading** (no backtest), y medir de forma honesta cuál (si alguna) supera a las demás en riesgo-ajustado.

**Qué la hace especial:** a diferencia de las semanas 1-6 (activas, de construcción), la S7 es **pasiva**: el trabajo lo hacen automáticamente los **cronjobs del sábado** (00:00 precios, 01:00 earnings, 15:00 E1, 16:00 E2, 17:00 E3).

**Acciones concretas al llegar a la semana 7:**
1. **Regenerar el comparativo** `comparativo_estrategias_<fecha>.md` con los P&L acumulados de E1/E2/E3.
2. **Evaluar las alarmas de Quinn (§5.2):**
   - ¿El PEAD (núcleo de E3) se degrada? (P&L E3 plano/negativo sostenido) → si SÍ, **parar el proyecto de señales** (el problema es todo el espacio).
   - ¿El vol-gate solo "funcionó" en el backtest pero no en vivo? → documentar.
   - ¿Los drawdowns están dentro de lo esperado del backtest?
3. **Calcular métricas de decisión:** Sharpe/max-DD de cada estrategia en vivo (con los datos del paper), turnover real, costes.
4. **Comparar con los backtests previos:** ¿E3 se comporta como esperábamos (más estable que E1, PEAD aportando)?

**Criterio de éxito de la S7:** E3 (PEAD-núcleo + vol-gate) tiene **mejor riesgo-ajustado neto** que E1 y E2, con drawdown acotado.

**Entregables:** `comparativo_estrategias_2026-XX-XX.md` actualizado, documento de medición con métricas en vivo.

---

### Semana 8 — Decisión + siguiente ciclo (activa, de análisis)

**Objetivo:** tomar la **decisión global** sobre qué hacer con el sistema, y definir el siguiente ciclo.

**Decisiones a tomar (según los umbrales de Quinn):**

| Evento en la medición | Decisión |
|---|---|
| E3 estabiliza DD y bate a E1/E2 en riesgo-ajustado | ✅ Confirmar arquitectura PEAD-núcleo + momentum-táctico |
| PEAD también se degrada | 🛑 **Parar**: el problema es todo el espacio de señales, no el reponderar |
| E3 no mejora ni empeora (ruido) | ⚖️ Extender paper-time; no escalar aún |
| Vol-gate no aporta en vivo | ⚙️ Quitar el gate, momentum a peso bajo fijo, o revisar umbrales |

**Acciones de cierre:**
1. **Actualizar la documentación general:** `README` del workspace, `quinn_regimenes.md`, plan con los aprendizajes reales (no los previstos).
2. **Pregunta de escalado (AÚN sin capital real):** si todo es estable, abrir la pregunta de cómo sería pasar a real (límites, tamaño) — pero como **siguiente fase**, con más historial.
3. **Diversificar a una tercera señal ortogonal** (value/quality) si E3 es estable pero se quiere más alpha — NO más momentum.
   - **Ya se adelantó la investigación:** las 2 señales ortogonales candidatas (reversal 5d, Amihud illiquidity) están validadas en laboratorio → ver **`plan_siguiente_fase_senales_ortogonales.md`** (plan de la siguiente fase a atacar tras la S8).

**Criterios de parada / no-escalar:**
- Sin métricas honestas tras 8 semanas → NO escalar.
- Diseño que dependa de un factor único (momentum O PEAD) → NO escalar.
- Vol-gating solo "funciona" con un umbral overfit → no confiar en él.

**Entregables:** `README` y documentación actualizada, documento de decisión (`decision_s8.md`), plan de siguiente fase.

**Regla de oro (Quinn):** el capital real NO entra hasta que la estrategia principal tenga un **historial ininterrumpido de varias semanas** y el diseño **no dependa de un factor único**.

---

*Plan de referencia del proyecto Qlib Work. Complementa `quinn_regimenes.md` y `cambio_pead_filtro_a_nucleo.md`.*
