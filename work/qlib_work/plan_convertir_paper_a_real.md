# 💰 PLAN DE REFERENCIA — De Paper-Trading a Carteras Reales con Beneficio Recurrente

**Autor:** Quinn · Investment Research Senior (14+ años buy-side, con experiencia real en llevar estrategias de paper/backtest a capital real de forma recurrente y sostenible)
**Proyecto:** Qlib Work (Toni)
**Fecha:** 2026-08-23
**Estado:** Documento de referencia del proyecto — el roadmap para convertir las estrategias en paper (sobre todo **E3: PEAD-núcleo + momentum-táctico + vol-gate**) en **capital real que produzca beneficio real y recurrente**.

> **Mandato:** el objetivo NO es más investigación ni diversificación académica. Es un **camino documentado, gradual y de riesgo controlado** para llevar la E3 del paper al dinero real que genere caja de forma recurrente. Honestidad: distinguir claramente el papel (donde no hay riesgo) de lo real (donde sí lo hay), y no dejar la E3 "midiéndose para siempre".

---

## 1. OBJETIVO DEL PLAN

Convertir la estrategia **E3 (PEAD-núcleo 65% + momentum-táctico 35% con vol-gate)** — hoy en paper-trading sin capital real — en **una cartera real operada de forma recurrente** que produzca **beneficio recurrente y sostenible** con riesgo controlado.

Principios que gobiernan TODO el plan:
1. **El paper es laboratorio barato (0% riesgo); lo real es dinero con riesgo.** No confundir los dos. El paper valida la arquitectura; lo real valida la ejecución, los costes y el comportamiento bajo pérdida real.
2. **Escalado gradual condicionado a hitos**, nunca "all-in". El capital real se sube por tramos y solo si cada tramo supera umbrales pre-registrados.
3. **Priorizar el beneficio recurrente con riesgo controlado**, no el return máximo ni el Sharpe máximo en ventanas cortas. Un sistema que paga caja de forma predecible vale más que uno que hace +40% un año y −30% el siguiente.
4. **La disciplina ES el activo**: no reponderar los simuladores durante la medición, no racionalizar, no sobreapostar a un factor único (PEAD es robusto, no infalible).

**Contexto verificado (no se re-inventa):** E1 (momentum 120, monitor −2.45%) y E2 (momentum+filtro PEAD, monitor −1.83%) son **monitor, NO capital real**. E3 es **LA apuesta** (recién arrancada, −0.05%). El momentum 120d NO es robusto (régimen); el PEAD SÍ (IC +0.085 a +0.130 con purged CV); el vol-gate está validado (Sharpe 1.136 vs 0.96). Toni tiene ADEMÁS una **cartera real separada** (NVO/AAPL/GOOGL/MSFT/META, ~$14,200, +9.2%, MSFT al 44%, META −17.2%) que es un **frente distinto de gestión de riesgo** — no se mezcla con este sistema.

---

## 2. CRITERIOS DE PUERTA (GATE) — PAPEL → REAL

> El arranque de capital real es **condicional**, no automático. La decisión S8 (~2 meses de paper) decide **arquitectura** (mantener/pivotar la E3). El **gate papel→real** se evalúa en una decisión aparte tras conseguir historial limpio suficiente.

### 2.1 Requisitos previos (no negociables)
- **Historial de paper ininterrumpido de E3:** mínimo **12 semanas corridas** (≈3 meses) corriendo sin reponderar, sin parchear simuladores, sin cambiar topk/split/ventana. **24 semanas preferible** antes del tramo 3. El cronjob semanal (00:00 precios, 01:00 earnings, 17:00 E3) debe haberse ejecutado sin fallos en todas las semanas (alarma de `decision_s8_alarmas.py`: estado de >20 días = cronjob caído).
- **No dependencia de un factor único:** el diseño (PEAD-núcleo + momentum-táctico gateado) se mantiene como está. Si algún momento se volviera "todo PEAD" o "todo momentum", eso ALARMA, no se escala.
- **La arquitectura no depende de un overfit:** el vol-gate debe aportar robusto (no solo con el umbral óptimo elegido); los pesos 65/35 son estructurales, no hiperparámetros a grid-search.

### 2.2 Umbrales mínimos para abrir el TRAMO 1 (primer capital real, 5-10%)
Estos se evalúan **en vivo** sobre el paper (netos de costes IB reales):
| Métrica | Umbral mínimo para tramo 1 | Nota |
|---|---|---|
| **Sharpe anualizado en vivo** | **≥ 0.6–0.8** | Con 12–24 semanas el Sharpe en vivo es ruidoso. No perseguir >1 en ventana corta; el objetivo es estar claramente por encima de 0 con banda de CI honesta. |
| **Max drawdown en vivo** | **≤ 20%** (preferible ≤15%) | El vol-gate busca ~−15%. Nunca exceder el peor DD del backtest purged CV (~−19% sin gate, ~−15% con gate) + margen. |
| **Consistencia del PEAD-núcleo (el pilar)** | **% de rebalances con contribución positiva ≥ 55–60%** | El pilar robusto debe dar resultado positivo la mayoría de las semanas; si va plano/negativo sostenido (>3 semanas), es alarma §5.2 y NO se escala (el problema sería todo el espacio de señales). |
| **Vol-gate aportando** | Comparar DD de E1 vs E3 en ventanas de alta vol: E3 debe caer sustancialmente menos | Mismo criterio que `decision_s8_alarmas.py` (E1 −X% vs E3 −Y%, diff>0). |

### 2.3 Cómo se decide (S8 y después)
- **S8 (≈2 meses de paper):** decide **arquitectura** (mantener/pivotar según §5.2 de `plan_E3_quinn_futuro.md`: PEAD degradado = parar; E3 bate a E1/E2 = confirmar; ruido = extender). **S8 NO es el punto automático de meter capital.**
- **Decisión GATE (post-S8, a las ≥12 semanas limpias):** aquí se aplican los umbrales §2.2. Si se cumplen → se autoriza el **tramo 1 (5-10%)**. Si no → se extiende el paper hasta que se cumplan (o se pivota).
- **Cada tramo posterior** (2 y 3) se aprueba con los mismos umbrales **re-evaluados en vivo sobre el tramo activo**, no sobre el backtest.
- **Proceso:** umbrales pre-registrados por escrito (este documento los fija); un script leerá el paper y emitirá el veredicto del gate. El humano toma la decisión final informado.

---

## 3. ESTRUCTURA DE CAPITAL Y ESCALADO GRADUAL

### 3.1 Definir el "capital destinable" (separado)
Toni debe fijar qué cantidad está dispuesto a arriesgar en ESTE sistema (estrategias cuantitativas). Debe ser **independiente** de la cartera real existente (NVO/AAPL/GOOGL/MSFT/META), que es un libro de gestión de riesgo propio con sus reglas. No usar dinero de emergencia ni el 100% del ahorro.

### 3.2 Tramos de capital (escalado por hitos)
| Tramo | Capital del destinable | Cuándo se abre | Hito de aprobación |
|---|---|---|---|
| **Tramo 1** | **5–10%** | Tras el gate (≥12 semanas limpias + umbrales §2.2) | Gate superado |
| **Tramo 2** | +10–15% (total ~20–25%) | Tras ~8–12 semanas del tramo 1 | Tramo 1 en beneficio neto, Sharpe en vivo ≥0.6, sin DD>tope, PEAD aportando, ejecución sin errores |
| **Tramo 3** | hasta máximo ~50% (nunca 100%) | Tras más historial real (24+ semanas) | Tramo 2 consolidado + subida de capital sin degradación de métricas |
| **Buffer** | resto | Siempre | Se mantiene en cash; nunca se apuesta el 100% |

### 3.3 Qué pasa si un tramo FALLA
- **Regla de oro: no doblar tras pérdida (no martingale).** Si un tramo rompe el **max DD en vivo (−20%)** o las métricas caen por debajo de los umbrales → **se REDUCE al tramo inferior** (o a monitor) y **se detiene el escalado**. No se sube más capital hasta diagnosticar y documentar (ver §5.4 stop total).
- **Reducción gradual, no pánico:** se recorta exposición (p.ej. vuelta al tramo 1) para no congelar pérdidas por mal market timing, pero **si el DD duro se rompe → stop total determinista** (se decide por regla, no por emocion).
- **Toda parada/reducción se documenta** (`decision gate/parada`) y se re-evalúa el diseño antes de cualquier nueva entrada.

---

## 4. OPERATIVA RECURRENTE REAL

### 4.1 Rebalanceo real
- **Frecuencia:** semanal (sábado), en coherencia con los cronjobs de paper. PEAD tiene poco turnover (la señal se renueva al reportar); momentum más. **Evaluar a las pocas semanas reales** si el rebalanceo semanal es neto de costes o conviene quincenal/mensual (si el turnover real es bajo, se espacia para ahorrar comisiones IB sin perder señal).
- **Regla de no-rotación:** **no rebalancear si el turnover esperado < un umbral (p.ej. 10–15% del capital del tramo)** — el beneficio de la rotación tiene que superar los costes IB reales. Ya están modelados (`ib_trades_cost` en `sim_utils.py`).
- **Ejecución guiada, no autopilot:** cada sábado el sistema emite la **lista de órdenes reales del día** (comprar/vender para alinear las posiciones reales de ese tramo al objetivo del libro PEAD-núcleo + momentum-táctico con su vol-gate). El humano ejecuta en IB con cabeza. **Ningún bot opera solo con dinero real** sin pasar antes por supervisión semanal explícita.

### 4.2 Costes IB reales
- Los costes ya modelados en paper (`ib_trades_cost`: comisión por orden + SEC/TAF) se contrastan con los reales de IB tras el primer mes. Si la comisión real difiere, se actualiza el modelo y se re-verifican los umbrales de rotación y el Sharpe neto.
- **Spread y slippage real** (no modelados en paper): el rebalanceo semanal con órdenes de mercado debe ejecutarse con **límite** o en ventanas de liquidez para no regalar margen; se mide slippage real y se lo descuenta de la efectividad.
- Posiciones pequeño tamaño (peso ~3-4% por nombre) → **30+ órdenes semanales pueden carcomer el beneficio neto** en un libro pequeño (tramo 1). Se ajusta el umbral de rotación y, si hace falta, se **reduce el número de nombres** en el tramo 1 (p.ej. topk menor) para respetar el cost/beneficio (está explícito en el diseño: nunca >30 posiciones para costes IB bajos).

### 4.3 Qué se reinvierte y qué se retira
- **Durante el escalado (tramos 1→2→3):** los beneficios del sistema se **reinvierten** (para crecer el capital del tramo y llegar a los hitos de escalado). No se retira caja todavía.
- **Una vez consolidado (fin de tramo 3 o quiebre de un umbral de beneficios):** se activa la política de **sweep periódico** (ver §7). La caja extraída NO se devuelve al sistema; es el "beneficio recurrente" que cobra el inversor.

---

## 5. GESTIÓN DE RIESGO REAL

### 5.1 Stops y reglas por posición
- **Stops por nombre:** en un libro long-only rotativo semanal el propio rebalanceo es disciplinado (sale del ranking y se vende), pero en real se añade un **stop de pérdida individual** (p.ej. −20% por nombre desde entrada) para acotar el peor caso de un ticker que se desploma entre rebalances.
- **Tope de posición único:** **ninguna posición puede superar ~8–10% del capital del sistema.** Esto es una lección directa del error de la cartera real de Toni (MSFT al 44% = riesgo dominante). En un libro con pesos igualitarios ~3-4% esto se cumple por diseño, pero se verifica siempre.
- **Decisión de tesis por escrito** para nombres malos, igual que se pide para META en la cartera real (no dejarlos "a la deriva").

### 5.2 Tamaño de posición
- Pesos fijos por libro (núcleo 65% / táctico 35%, techo momentum 50%) con **pesos igualitarios dentro de cada libro** (~3-4% por nombre). No se decide por oráculo.
- **No sobreapostar PEAD:** aunque es robusto (~6 años de muestra, no certidumbre absoluta), se limita la exposición al libro PEAD y se diversifica el número de nombres; no apalancamiento jamás.

### 5.3 Vol-gate en real
- El mismo gate del simulador (`vol_gate.py`, umbrales P75/P90 + histéresis) se aplica **en vivo cada rebalanceo**: si la vol realizada del SP500 está en percentil ≥ P90, el **libro táctico queda en cash real** (no se invierte ese capital); en P75–P90 se reduce a la mitad. El PEAD **no se gatea** (robusto en todos los estados).
- Implementación: `arranque_real.py` lee el nivel de gate actual y **no genera órdenes de compra para el libro táctico** cuando gate=0, y reduce tamaño cuando gate=0.5.

### 5.4 Máximo drawdown en VIVO y stop total
- **Tope duro:** si el capital del sistema cae **−20% desde su máximo de tramo**, se activa el **stop total determinista**: se reduce a monitor, se detiene el escalado y se diagnostica antes de cualquier re-entrada. Es una regla, no una emoción.
- Se monitoriza el DD del tramo real activo semanalmente (`riesgo_real.py` → memo).

### 5.5 No sobreapostar el sistema entero
- **No apalancamiento, no margen, no 100% del destinable.** Máximo ~50% del capital destinable en el sistema, resto en cash/buffer.
- **E1 y E2 son monitor, no capital real.** Jamás invertir dinero real en momentum puro o momentum+filtro; solo E3 (la arquitectura cuyo riesgo-ajuste está validado).
- No usar el sistema para "remediar" la cartera real existente (MSFT/META): frentes separados con reglas separadas.

---

## 6. CRONOGRAMA POR FASES

| Fase | Plazo | Qué ocurre | Puerta de salida |
|---|---|---|---|
| **Fase 0 — Medición paper E3 (pasiva)** | Ahora → ~3 meses (S12) | E3 corre sola (cronjobs sábado); regenerar comparativo y alarmas; **NO tocar simuladores** | Gate §2 superado (≥12 semanas limpias + umbrales) |
| **Decisión GATE** | Fin de Fase 0 | Aplicar umbrales §2.2 → autorizar (o no) el **tramo 1** | Veredicto del gate + decisión humana documentada |
| **Fase 1 — Tramo 1 real** | ~8–12 semanas | Arrancar con **5–10%** del destinable, rebalanceo semanal guiado, medir costes IB reales, slippage, ejecución | Tramo 1 en beneficio neto, Sharpe vivo ≥0.6, sin DD>tope |
| **Fase 2 — Tramo 2** | +8–12 semanas | Subir a **~20–25%**, re-evaluar umbrales en vivo sobre tramo activo | Hitos §3.2 superados |
| **Fase 3 — Tramo 3 + consolidación** | +3–6 meses | Escalar hasta **máx ~50%**, consolidar operativa, **activar sweep de beneficios** (§7) | Sistema estable con beneficio recurrente retirable |
| **En adelante — Operativa recurrente** | continuo | Rebalanceo semanal + riesgo_monitor + sweep periódico + revisión trimestral del diseño | Beneficio recurrente neto sostenido con DD acotado |

**Total realista hasta escala completa:** ~6–9 meses. **El primer capital real NO entra antes de ~3 meses de paper limpio.** Este cronograma es deliberadamente lento: el coste de la prisa es perder dinero real por una estrategia aún no validada en vivo.

---

## 7. DEFINICIÓN OPERATIVA DE "BENEFICIO RECURRENTE" (CÓMO COBRA EL INVERSOR)

### 7.1 Dos caras del beneficio — distinguirlas
- **Beneficio compuesto (reinvertir):** el capital del sistema crece y se reinvierte. Es retorno compuesto, pero **no genera caja** al inversor.
- **Beneficio recurrente (sweep / retirada):** una parte del P&L se **retira del sistema de forma periódica** y pasa a manos del inversor. Eso ES el "beneficio real recurrente".

### 7.2 Política de cobro (híbrida, definida aquí)
1. **Reinversión durante el escalado:** entre tramos 1→2→3, los beneficios se reinvierten al 100% (el objetivo es crecer el capital del tramo hasta que la escala haga que los costes fijos y la caja retirable sean relevantes).
2. **Sweep periódico en consolidación (fin de Fase 3 en adelante):**
   - Cada **trimestre**, si el capital del sistema está **en beneficio neto y fuera de drawdown** (por encima del capital base del tramo + banda de confort, p.ej. +5% sobre base), se retira **50% del beneficio neto del trimestre** (o el % que Toni fije, p.ej. 25–50%).
   - **Nunca** se retira con cargo al capital base ni para cubrir pérdidas: el sweep solo se hace sobre el exceso de beneficio consolidado.
3. **Regla clara de "el inversor cobra":** el beneficio recurrente = **sweep trimestral del excedente sobre el capital base**, registrado en el ledger (sección 8). No se toca el capital base ni el buffer.

### 7.3 Por qué esto es "recurrente y sostenible"
- La caja sale **solo cuando hay beneficio consolidado y fuera de DD** → el sistema no se descapitaliza.
- La **frecuencia fija (trimestral)** y la **fórmula (50% del exceso)** hacen el cobro predecible, no dependiente del estado de ánimo.
- Documentar la política por escrito es el requisito para que Toni pueda "cobrar" sin dudar y sin romper el sistema.

---

## 8. ACCIONES CONCRETAS — SCRIPTS Y ARCHIVOS

> **Principio de diseño:** los scripts de real son **read-only sobre el estado y emiten informes/órdenes guiadas**. **Ninguno opera el broker solo** sin supervisión semanal explícita del humano.

### 8.1 Crear
| Script / Archivo | Ruta sugerida | Qué hace |
|---|---|---|
| **`arranque_real.py`** | `work/estrategias/simulation/` | Lee `state_pead_core.json` (paper) + precios actuales, reconstruye el objetivo del libro (núcleo+táctico con vol-gate del día) y **emite la lista de órdenes reales del día** para alinear las posiciones del tramo al objetivo. Aplica `ib_trades_cost` real, respeta el umbral de no-rotación y el gate (no compra el táctico si gate=0). Genera memo `ordenes_real_<fecha>.md`. |
| **`riesgo_real.py`** | `work/estrategias/` | Cada sábado: pesos por posición + alerta concentración >10%, stop por nombre, DD del tramo activo vs tope −20%, nivel de vol-gate, alarma de E1/E2 que nunca están en real. Genera memo `riesgo_real_<fecha>.md`. **Es un informe, no un bot.** |
| **`capital_real_ledger.py`** (+ `capital_real.csv`) | `work/estrategias/` | Registra: tramo activo, capital base del tramo, aportes, sweeps retirados, beneficio retenido vs retirado. Da la trazabilidad de cuánto "cobra" el inversor y cuánto se reinvierte. |
| **`decision_gate_real.py`** | `work/estrategias/` | Aplica los umbrales §2.2 sobre el paper y emite el **veredicto del gate** (AUTORIZA / NO tramo N). Un script que evita decisiones emocionales: lee el paper, calcula Sharpe/DD/consistencia vivos y responde sí/no. |

### 8.2 Modificar
- **`decision_s8_alarmas.py`:** añadir los umbrales de gate §2.2 (Sharpe vivo, DD, consistencia PEAD) y una sección para la cartera real del tramo; mantener el resto read-only.
- Auto-pre-registrar en cada ejecución el veredicto del gate en `qlib_work/decision_gate_<fecha>.md`.

### 8.3 Monitorizar (ya existente)
- `estado_portfolio_*.md` (cartera real existente), `comparativo_estrategias_*.md` (E1/E2/E3), `money_paper_*.md`, `estados_mercado.csv` + `vol_gate.py` (nivel de gate). Añadir al cron del sábado los nuevos `riesgo_real` y (solo en fase 1+ con tramo activo) `arranque_real`.

### 8.4 Cronjobs sábado (mantener + ampliar)
Los actuales (00:00 precios, 01:00 earnings, 15:00 E1, 16:00 E2, 17:00 E3) se mantienen intactos durante la medición. Solo al entrar en Fase 1 se añade la generación de órdenes reales y el riesgo_real.

---

## 9. QUÉ NO HACER AL IR A REAL (errores clásicos)

- ❌ **NO meter capital real antes del gate** (≥12 semanas de E3 limpias + umbrales §2.2). El primer euro real NO se arriesga "para probar".
- ❌ **NO reponderar, parchear ni cambiar topk/split/ventana de los simuladores durante la medición.** La disciplina ES el activo; cualquier cambio reinicia el reloj del historial.
- ❌ **NO sobreapostar PEAD ni momentum.** PEAD es robusto en ~6 años de muestra, no certidumbre; el momentum sigue siendo frágil (se mantiene táctico, ≤50%, gateado).
- ❌ **NO escalar a 100% del destinable ni apalancarse ni usar margen.** Máximo ~50% del destinable + buffer en cash.
- ❌ **NO operar autopilot sin supervisión humana.** El rebalanceo es guiado; el humano ejecuta y revisa. Ningún bot friega el dinero real sin tu firma semanal.
- ❌ **NO perseguir Sharpe o win-rate altos en ventanas cortas** (12–24 semanas de papel son ruido; se decide con bandas y comparando con el backtest purged CV, no con el pico).
- ❌ **NO invertir capital real en E1 (momentum puro) ni E2 (momentum+filtro):** son monitor, su arquitectura tiene al momentum como pilar = no robusto.
- ❌ **NO usar este sistema para "remediar" la cartera real existente** (MSFT 44%, META −17%). Son frentes separados: el sistema arranca con su propio capital destinable y sus propias reglas.
- ❌ **NO sobre-ingeniería al ir a real:** sin HMM/detector sofisticado, sin 3ª señal ortogonal mientras no haya capital real y beneficio recurrente consolidado. El foco es ejecutar E3, no complicarla.
- ❌ **NO romper el max DD en vivo (−20%)** "por si rebota". Stop total determinista, documentado, ejecutado.
- ❌ **NO retirar beneficios con cargo al capital base ni para cubrir pérdidas.** El sweep solo se hace sobre el exceso consolidado fuera de DD.
- ❌ **NO doblar el capital tras una pérdida (no martingale).** Un tramo que falla se reduce/documenta, nunca se duplica.

---

### Síntesis en una pizarra
> **E3 (PEAD-núcleo + momentum-táctico + vol-gate) es la única apuesta con derecho a capital real.** Se mide en paper ≥12 semanas limpias (S8 decide arquitectura, no capital). Si el **gate** se supera (Sharpe vivo ≥0.6–0.8, DD ≤20%, PEAD aportando ≥55–60% de las semanas, vol-gate protegiendo), se abre el **tramo 1 (5–10% del destinable)**, rebalanceo semanal **guiado** con costes IB reales y vol-gate en vivo. Se escala por **tramos** según hitos, con **stop total a −20%** y nunca el 100% en juego. **El beneficio recurrente** se define como **sweep trimestral del 50% del exceso sobre el capital base, solo en beneficio y fuera de DD**. La cartera real existente de Toni (MSFT/META) es un frente de gestión de riesgo **aparte**. El beneficio real NO es más investigación: es ejecutar con disciplina el sistema ya validado, cobrar caja de forma recurrente y no romperlo.

---
*Documento de referencia del proyecto Qlib Work. Complementa `quinn_revision_plan_beneficios.md`, `plan_E3_quinn_futuro.md` y `evolucion_E1_E2_E3.md` — y es el roadmap concreto hacia capital real.*
