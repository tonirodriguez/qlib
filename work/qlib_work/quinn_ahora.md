# 🎯 QUINN — Qué hacer AHORA (semanas 7-8: medición pasiva E1/E2/E3)

**Autor:** Quinn · Investment Research Senior (14+ años buy-side)
**Sujeto:** Toni · proyecto Qlib work (lab + paper-trading, sin capital real)
**Fecha:** 2026-08-23
**Base verificada (NO plan — ejecutada):**
- E1 momentum puro **−2.45%** · E2 momentum+filtro PEAD **−1.83%** · E3 PEAD-núcleo+momentum-táctico+vol-gate **−0.05%** (recién arrancada 22-ago).
- Momentum 120d NO robusto = **régimen**, no decaimiento (calma IC +0.024 vs estrés −0.184, CI no solapan; `vol_alta` t=−3.06; tiempo t=+1.32 NS).
- PEAD SÍ robusto (purged CV IC Spearman +0.085…+0.130). Vol-gate **validado** (gate P75: Sharpe 1.136 vs 0.96, DD −16.6% vs −19.3%).
- E3 ya integra `vol_gate.py`. Cronjobs OK (sáb 00:00 precios, 01:00 earnings, 15:00/16:00/17:00 E1/E2/E3).
- Proyecto cripto (`work/crypto/`) = frente separado, no tocado en este ciclo.

---

## 1. VEREDICTO DIRECTO — ¿qué hacer ahora?

**No toques nada de lo que corre (E1/E2/E3) ni construyas sofisticación.** Las semanas 7-8 son de **medición pasiva**: las 3 corren solas acumulando evidencia. El trabajo de valor AHORA está en el **laboratorio paralelo**, donde NO estorba la medición.

**Priorización de las opciones (a–g):**

| Rango | Opción | Veredicto |
|---|---|---|
| 🥇 **1º** | **(d) Robustecer datos de earnings + validar PEAD-núcleo con más historia** | **SÍ — la más urgente.** Tu núcleo de E3 está validado sobre **~2 años** de earnings. Es el eslabón más débil de toda la cadena. Extender historia = más eventos PEAD = decisión S8 con más rigor. | 
| 🥈 **2º** | **(c) Investigar 3ª señal ortogonal (value/quality) en laboratorio, SIN meterla en paper** | **SÍ — alto valor estratégico.** Desriesga el "no dependas de un factor único" antes de la decisión de escalar. Solo laboratorio, no tocar el papel de E3. |
| 🥉 **3º** | **(e) Infraestructura ligera para la decisión S8** (dashboard/aleret de alarmas §5.2) | **SÍ — versión mínima.** Un script read-only que vigila los umbrales de Quinn y regenera el comparativo. Nada de dashboards complejos. |
| ⚪ 4º | **(b) Avanzar frente cripto** | **SÍ, solo con ancho de banda sobrante y 100% separado.** Es trabajo legítimo paralelo, pero NO debe desplazar (c)(d)(e) ni ensuciar la medición. |
| 🔴 | **(a) "NADA y esperar"** | **NO como opción única.** La disciplina es NO tocar el paper; pero quedarse parado 6 semanas desperdicia el laboratorio. La regla correcta es: *no toques el papel, sí trabaja el lab*. |
| 🔴 | **(f) Backtest extendido del momentum (2008/2015/2018)** | **NO ahora — rendimiento decreciente.** El régimen YA está probado con rigor (CI, t=−3.06, no decaimiento). Más transiciones = robustez theatER, riesgo de racionalizar. Solo si en S8 el régimen se pone en duda de nuevo. |
| 🔴 | **(g) / más detector / optimizar topk / pesos** | **NO.** Prohibido por regla de oro (ver §3). |

**La pregunta correcta de ahora no es "qué pulir de lo que ya hay", sino "qué hará más sólida la decisión de la semana 8".** Esa es la lente que prioriza (d)→(c)→(e).

---

## 2. QUÉ SÍ HACER AHORA (concreto, priorizado)

### Rutina pasiva obligatoria (no la saltes) — S7
1. **Cada sábado medir, no decidir.** Los cronjobs ya corren solos. Tu única acción semanal: regenerar `comparativo_estrategias_<fecha>.md` y `estado_portfolio_<fecha>.md` con los 3 P&L acumulados.
2. **Evaluar las alarmas §5.2 con lápiz, no con cirugía:**
   - ¿E3 (PEAD-núcleo) plano/negativo **sostenido**? → es la señal de "parar el espacio de señales".
   - ¿El vol-gate funciona en vivo o solo en backtest?
   - ¿Drawdowns dentro de lo esperado del backtest (DD ~−17% típico)?
3. **No reponderes, no cambies umbrales, no parchees simuladores** sobre la marcha. Anota si hay desviación; se decide en S8.

### 🥇 (d) — Extender historia de earnings y re-validar PEAD-núcleo
**Por qué:** tu convicción en PEAD como núcleo reposa en un purged CV sobre ~2 años de eventos. Eso es poco para apostar el 65% del capital ficticio de E3. Quieres más eventos antes de confirmarlo en S8.

**Scripts/acciones concretas (`work/estrategias/`):**
- Revisar y correr ampliado `pead_fetch_full.py` / `backfill_pead.py` para traer **más histórico de anuncios y SUE** que el corte actual (~2 años). YahooQuery permite mucho más atrás en la mayoría de tickers; documenta cuánto se gana y qué cobertura/calidad pierdes (survivorship, cambios de ticker).
- Re-correr `pead_purgedcv.py` **sobre el sample ampliado** con la misma metodología (IC Spearman, purged CV, ventanas 20-60d). Reporta si el IC sigue en rango +0.085…+0.130 o si se degrada al añadir historia. **Eso es exactamente lo que S8 necesita saber.**
- Entregable: `pead_purgedcv_v2_resultado.md` — "PEAD-núcleo con 2 años vs N años: ¿se sostiene?".
- **NO** reescribir `simulate_pead_core.py` ni tocar `state_pead_core.json` con estos datos nuevos a mitad de medición. El backtest de PEAD es laboratorio; el paper de E3 sigue con sus datos actuales para no contaminar la comparación.

### 🥈 (c) — Arrancar la 3ª señal ortogonal en laboratorio (value/quality)
**Por qué:** el plan ya lo marcó (§5.3, §8): el siguiente experimento es una señal **ortogonal** (value/quality), NO un detector de régimen ni más momentum. Si empiezas ahora, llega validada a la decisión S8 / siguiente ciclo.

**Scripts/acciones concretas (`work/estrategias/`):** (crear nuevo, no tocar sims)
- `value_quality_purgedcv.py` — replica **exactamente** la metodología que ya validaste (`pead_purgedcv.py` / `momentum_purgedcv.py`): IC Spearman, purged CV, CI bootstrap.
- Señales candidatas **simples, con datos que ya tienes en Qlib US** (no traer infra compleja): B/M (book-to-market), y/o un proxy de calidad (ROE/ROIC estable), y/o dividend yield. **Uno a la vez** — un factor por estudio, sin apilarlos.
- Pre-registra la hipótesis falsable por escrito (misma rigurosidad que el régimen) antes de correr.
- Entregable: `value_quality_resultado.md` — IC por señal, CI, y veredicto "ortogonal y útil / correlacionado / ruido".
- **Límite duro:** esto **no entra en el paper de E3** hasta la decisión S8. Nada de "aprovecho y lo añado al libro" a mitad de medición.

### 🥉 (e) — Infraestructura MÍNIMA para la decisión S8
**Script nuevo read-only:** `work/estrategias/decision_s8_alarmas.py`
- Lee los 3 estados (`state.json`, `state_pead.json`, `state_pead_core.json`) + `estados_mercado.csv`.
- Calcula en vivo: P&L acumulado, Sharpe/max-DD aproximado, turnover, y **flaggea los umbrales §5.2** (E3 plano/negativo sostenido, vol-gate sin aportar, DD fuera de backtest).
- Emite un **alerta de una línea** cuando un umbral se cruza; regenera el comparativo.
- **NO** construir panel web, NI base de datos, NI alertas por email/Telegram sofisticadas. Un CLI que escupe un memo markdown es suficiente y no se convierte en proyecto de mantenimiento.

### ⚪ (b) — Frente cripto (opcional, con ancho sobrante)
- Legítimo y no estorba a la medición, pero **no es prioridad de este ciclo**. Si lo tocas, hazlo en `work/crypto/` con su propia rutina y documentación, y **explícita que es independiente** de la decisión S8 de las estrategias de acciones. No lo mezcles en el mismo lab.

---

## 3. QUÉ NO HACER (anti-prioridades — la parte más importante)

- ❌ **NO tocar E1/E2/E3 durante las semanas 7-8.** No reponderar, no cambiar topk, no ajustar el split 65/35, no parchear simuladores con datos nuevos. Esa es exactamente la disciplina que el plan pide (E1/E2 = monitor, E3 = apuesta en examen). Cualquier toque **contamina la medición** que justamente estás haciendo.
- ❌ **NO construir HMM/Markov / detector de régimen sofisticado.** El vol-gating simple ya ganó; el régimen ya está probado. Todo detector sofisticado es un proyecto de vanidad con riesgo de overfit. (Nota académica que ya existe en `quinn_regimenes.md`.)
- ❌ **NO "optimizar el momentum"** (ventana 120d, topk, rebalanceo, umbrales del gate). El momentum no es el problema a pulir; es el componente a mantener a peso táctico. Toda optimización ahora es sobreingeniería.
- ❌ **NO grid-search del split PEAD/momentum (65/35).** Es un punto de partida estructural, no un hiperparámetro. La robustez viene de la estructura, no del split exacto.
- ❌ **NO racionalizar** ("hay que esperar al régimen bueno del momentum", "en calma el momentum funciona"). Eso es exactamente lo que el purged CV prohíbe. Si te surge la tentación, relee `plan_E3_quinn_futuro.md` §0.2.
- ❌ **NO validar PEAD solo para confirmar lo que quieres oír.** Correlaciona con 2 años de historia y si añadir más lo degrada, dilo en el memo. El objetivo es saberlo ANTES de S8.
- ❌ **NO meter capital real.** Regla de oro intacta: solo tras un historial ininterrumpido de varias semanas Y un diseño que no dependa de un factor único.
- ❌ **(f) NO** re-abrir el backtest extendido del momentum a 2008/2015/2018 este ciclo. Ya respondido con rigor; ir a por más transiciones es rendimiento decreciente y da pie a racionalizar.

---

## 4. QUÉ ESPERAR Y CUÁNDO RE-EVALUAR

**Calendario realista:**
- **Ahora → ~4 semanas (mediados de sept-2026): punto de control S7.** Regenera comparativo; evalúa las 3 alarmas §5.2. NO es decisión, es lectura. Con tu cadencia semanal obtienes ~4-5 rebalanceos de E3 — suficiente para *tendencia* inicial, no suficiente para sentencia (necesitas ≈8-10+ y ojalá ≥24 como el plan pedía para decidir).
- **~8 semanas desde el arranque de E3 (≈mitad/final de oct-2026): decisión S8.** Toma la decisión global según §5.2/§8.

**Qué esperar (honesto, sin promesas):**
- Espera que **E3 sea más estable que E1** (el gate + PEAD-núcleo deberían acotar el drawdown); no esperes un batido espectacular en 4 semanas. PEAD es un drift modesto, no una bala.
- Espera que **E1 siga flojo** en régimen de corrección tech (ya rota a defensivos). Eso no es una sorpresa; es coherente con el hallazgo. No lo toques.
- Espera que **el PEAD-núcleo muestre su cola honesta**: en algún momento un ticker reportará mal y saldrá. Eso es señal funcionando, no error.
- **Re-evalúa la prioridad (d)/(c)/(e) en el punto de control S7**: si alguna revela algo que cambie la decisión (PEAD se degrada con más historia, value/quality resulta fuerte y ortogonal), actualiza el plan S8 en consecuencia. Si no, sigues con lo previsto.

---

## 5. CONVICCIÓN

**Nivel de convicción: alta (y disciplinada).**

- **En la arquitectura:** el reponderamiento a PEAD-núcleo + momentum a peso táctico + vol-gate es la decisión correcta, y el probarme a mí mismo es justo el riesgo más grave de este ciclo — **el lab (d)(c) que propongo ni siquiera toca el papel**, así que la medición queda limpia.
- **En lo que NO hacer:** convicción alta también. Si E1/E2/E3 se tocan a mitad de medición, todo este trabajo pierde valor como experimento. La autodisciplina es el activo principal ahora.
- **Riesgo residual honesto:** PEAD-núcleo reposa en ~2 años de earnings; por eso (d) es lo primero. No es que dude de PEAD — es que quiero saberlo con N años antes de confirmarlo en S8. Esa es la diferencia entre un investigador y un convencido.
- **Regla de oro intacta:** sin capital real, sin factor único, sin detector sofisticado, sin sobreapostar. Si el PEAD también se degrada con más historia, eso **no es un fracaso del plan**: es el lab haciendo su trabajo y ahorrándote el error en real. Cuando sepas eso antes de S8, estarás donde querías estar.

---

*Documento de decisión "qué hacer ahora" — Quinn. Complementa `plan_E3_quinn_futuro.md` (S7-S8) y `comparativo_estrategias_2026-08-22.md`. El punto de control de la S7 re-evaluará estas prioridades.*
