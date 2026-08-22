# Estrategia combinada Momentum 120d + PEAD — ¿Paper-trading sin backtest combinado?

**Analista:** Quinn (Investment Research, 14+ años buy-side)
**Cliente:** Toni (inversor sistemático, Qlib)
**Fecha:** 22-ago-2026
**Decisión solicitada:** ¿Es defendible pasar a paper-trading de la combinación (momentum 120d + PEAD) sin tener el backtest combinado funcionando? Proponer solución priorizada con criterio de decisión.

---

## 1. Veredicto directo

**NO pases a paper-trading de la estrategia combinada tal cual. Pero SÍ puedes, en paralelo, arreglar el backtest y probar la combinación "a mano" fuera de Qlib — y en ese proceso tomarás la decisión con datos, en 1-2 días de trabajo.**

Concretamente, mi veredicto es doble y matizado:

- **No es defendible** arrancar el paper-trading *combinado* como un salto ciego (sin ninguna validación histórica de la interacción entre las dos señales), porque el riesgo específico de un sistema con dos señales **es precisamente la interacción** — y esa interacción es lo único que el bug te impide medir.
- **Sí es defendible y recomendable**, con las dos señales corriendo **en paralelo pero por separado**, mientras arreglas la combinación con un método robusto y barato: el momentum ya está en vivo y el PEAD se valida solo. Cuando la combinación esté validada, recién entonces se fusiona.

La respuesta corta a "¿puedo saltarme el backtest?" es: **no te lo recomiendo, y no necesitas hacerlo** — porque hay un camino de 1-2 días que te da la validación con casi todo reusado.

---

## 2. Qué se sabe / qué se desconoce (matriz de confianza)

| Componente | Estado | Confianza | Fuente de la evidencia |
|---|---|---|---|
| Momentum 120d: señal sólida, rentable y de bajo riesgo relativo | **VALIDADO** (IC OOS +0.066, +18-21% anual, Sharpe ~1, DD −19%) | **Alta** | Backtest OOS + ya en paper-trading desde 14-ago (€20k, −2.45% hasta ahora) |
| PEAD: la sorpresa de earnings predice el retorno post-anuncio | **VALIDADO como señal de ranking** (IC Spearman 0.19-0.22) | **Alta** (pero muestra corta, ver abajo) | Investigación de Toni |
| PEAD como estrategia pura binaria | **MARGINAL** (+1%/evento, 49% acierto) | Alta (bajo poder, no sobrecargarlo) | Investigación de Toni |
| **Combinación momentum+PEAD: mejora real vs momentum solo** | **DESCONOCIDO** | **Baja — es exactamente lo que no está medido** | — |
| Interacción de las dos señales (correlación, solapamiento, si se refuerzan o se anulan) | **DESCONOCIDO** | **Baja** | — |
| Robustez del PEAD con solo ~2 años de earnings | **LIMITADA** | Media (baja muestra ⇒ menos de ~8 ciclos de resultados ⇒ ruido de ciclo grande) | Muestra ~2 años |

### Lectura honesta de la matriz

- **Lo que está en riesgo no es la calidad de las señales individuales** (ambas están razonablemente bien fundamentadas), **sino la premisa de que "dos señales fuertes suman"**. Esa premisa es cierta *a menudo* pero **no siempre**: dos señales correlacionadas aportan mucho menos de lo que sumaría su IC individual, y a veces una señal con colas fatales (PEAD concentrado en la ventana post-anuncio) añade riesgo de calendario sin añadir alfa.
- La pregunta que debe decidir el paper-trading combinado — **¿la combinación mejora el Sharpe del momentum solo (no solo el retorno)?** — es numéricamente respondible y **no la puedes responder con la cabeza, solo con la combinación medida**.
- El bug es técnico (pandas/reindex/zscore/stack produce serie vacía), **no conceptual** — eso a favor de que la combinación *puede* ser probablemente buena. Pero "el bug no es el concepto" NO equivale a "el concepto está bien": el bug simplemente te impide verificarlo.

**Convicción global:** 7/10 en que la combinación *probablemente* mejora el momentum (señales ortogonales, PEAD real), pero **esa convicción no es suficiente para saltarse la medición**. La decisión la debe tomar el número, no la esperanza.

---

## 3. Opciones y soluciones concretas, priorizadas

Ordeno por **mejor relación esfuerzo/valor de información**. La opción 1 es la que haría yo primero.

### Opción 1 (RECOMENDADA) — Arreglar el bug del backtest combinado con un método robusto FUERA de Qlib

**Qué:** No pierdas más tiempo en el stack completo de Qlib para el resultado combinado. Construye el backtest combinado con un **método manual, vectorizado, de 50 líneas**, fuera de Qlib, usando las **salidas ya calculadas** de cada señal (no el pipeline end-to-end).

**Cómo (concreto):**
1. **Reusa el output de cada señal por separado.** Ya tienes el score diario de momentum (a partir del backtest que validó) y el score de sorpresa de earnings. No re-derives nada con pandas `stack` en un solo DataFrame — ese es exactamente el punto donde el bug vive (alinear por (fecha, activo) con reindex de fechas distintas produce la serie vacía).
2. **Resuelve el cruce de calendarios explícitamente.** Los earnings no ocurren cada día; el momentum se rebalancea semanal. Construye la señal combinada con un **join explícito sobre (fecha, ticker)** con `merge` on keys (no `reindex` mágico), y **propaga la sorpresa de earnings forward hasta la fecha de rebalanceo** (`ffill` dentro de cada ticker), de modo que en cada rebalanceo semanal sepas la última sorpresa conocida. Ese `ffill` manual sobre el cruce de calendario es la corrección del bug.
3. **Define la combinación con un formato claro y falsable desde el día 1**, p.ej.:
   - **Ranking combinado:** `rank_score_t = w · rank(momentum_120d) + (1−w) · rank(PEAD_sorpresa)`, con `w` en `{0.6, 0.7, 0.8}`.
   - **O como filtro/refuerzo:** momentum puro, pero **+peso adicional a los nombres del top-30 que además tienen sorpresa > +5%**, o **excluir del top-30 cualquier nombre con sorpresa fuertemente NEGATIVA** (esto es lo que más probablemente añade valor: no comprar momentum con sorpresa catastrofica — el PEAD más potente es el del lado negativo).
4. **Métrica objetivo definida a priori:** comparar **Sharpe y drawdown de la combinación vs momentum solo en el mismo periodo**, no solo retorno. El estándar de éxito no es "gana más", es "**mejor riesgo-ajustado sin añadir drawdown**".

**Esfuerzo:** 1-2 días. **Valor:** responde de forma numérica la pregunta exacta que bloquea la decisión, con todo lo ya validado reusado. **Riesgo:** bajo (es código simple, vectorizado, unit-testable).

**Por qué es la 1:** es más barato y más robusto que pelear con el pipeline Qlib completo, elimina el bug por construcción (merge explícito + ffill en vez de reindex), y no bloquea nada mientras tanto.

### Opción 2 — PEAD como refuerzo del momentum QUE YA ESTÁ EN PAPER-TRADING (sin rehacer el motor)

**Qué:** Mientras arreglas la combinación (opción 1), ya puedes **operativizar la parte del PEAD que tiene más valor a priori** sobre el sistema de momentum ya en vivo: **el filtro negativo**.

**Cómo:** Al rebalanceo semanal del momentum, si uno de los 30 nombres del top-30 acaba de reportar una **sorpresa fuertemente negativa** (p.ej. < −2σ o < −10% vs consenso), **sustitúyelo por el siguiente nombre** del ranking que no tenga sorpresa negativa. Esto capitaliza la parte más robusta y barata del PEAD (evitar momentum "tocado" post-anuncio) sin cambiar la arquitectura del motor, sin doble señal de ranking, y sin rehacer nada.

**Ventaja:** es un delta pequeño, fácil de vigilar, y ataca el lugar donde el PEAD tiene más alfa (el lado negativo), que es también el que se correlaciona menos con el momentum.
**Esfuerzo:** medio día. **Valor:** te da exposición inmediata al concepto *combinado* (interacción de la señal) con un cambio quirúrgico. **No sustituye** a la opción 1 como validación global.

### Opción 3 — Paper-trading de las DOS señales por separado (en paralelo), no combinadas

**Qué:** Corre el momentum (ya vivo) y un **paper-trading PEAD puro separado** (mismo €20k ficticio, reglas iguales) en paralelo. Es la validación "limpia" de cada señal en condiciones reales de ejecución, sin mezclar todavía.

**Valor:** genera evidencia out-of-sample real de ejecución (slippage, timing post-anuncio, liquidez en la ventana del PEAD) para *cada* señal, que es la pieza que el backtest no da. **No valida la interacción**, pero deja ambas piernas listas y medidas para cuando la opción 1 diga cómo combinarlas.
**Esfuerzo:** bajo (el motor momentum ya existe; solo añadir una pierna PEAD). **Es complementaria a la 1 y a la 2, no rival.**

### Opción 4 — Paper-trading combinado DIRECTO, sin backtest (LO QUE PREGUNTA TONI)

**Qué:** Saltarse la validación y fusionar ya en vivo.

**Por qué NO la prefiero:** al fusionar sin saber la interacción **no puedes atribuir después un resultado bueno o malo a nada** — si la combinación va mal, ¿es el PEAD, el momentum, o la forma de fusionarlos? Y si el bug fueraconde un problema real de alineación (p.ej. el `ffill` mal hecho duplica o salta posiciones), lo descubrirías **con dinero — real en el futuro — parado sobre una base que no comprobaste**. En paper hay bien poco en juego, pero el *hábito* de saltarse la validación al primer bug sí tiene coste: normaliza un procedimiento que, trasladado a capital real, es una fábrica de pérdidas atribuibles a nada.

**La única situación en que la aceptaría:** si el bug tardara **semanas** en arreglarse (no es el caso) **Y** la combinación fueran señales perfectamente decorrelacionadas con lógica de fusión trivial conocida. No se cumple nada de eso aquí.

### Opción 5 (NO recomendada) — Dudar del concepto o abandonar el PEAD

El dato del PEAD es real (IC 0.19-0.22), la ortogonalidad es plausible, y el bug es técnico. Abandonar sería tirar trabajo validado por un problema de pandas. Se descarta.

---

## 4. Recomendación final (clara y accionable)

**Plan en 3 frentes, en orden:**

1. **HOY — Frente 1 (inmediato, medio día):** aplica la **opción 2** al portfolio momentum ya en paper-trading: **filtro negativo por sorpresa de earnings** (sustituir del top-30 cualquier nombre con sorpresa < −2σ por el siguiente del ranking). No rehaces el motor; es un delta quirúrgico y vigilable.

2. **ESTA SEMANA — Frente 2 (validación, 1-2 días):** construye el **backtest combinado manual fuera de Qlib** (opción 1): merge explícito por (fecha, ticker) + `ffill` de la sorpresa hasta el rebalanceo, ranking combinado `w·momentum + (1−w)·PEAD` con `w∈{0.6,0.7,0.8}`, y **compara Sharpe + drawdown vs momentum solo**. Este número, y solo este, decide la fusión.

3. **EN PARALELO — Frente 3:** pon en marcha (si quieres) la pierna **PEAD pura por separado** en paper-trading (opción 3) para medir la ejecución real de la señal (slippage/timing post-anuncio). Útil para calibración, no bloquea nada.

**Regla de oro:** la **fusión en paper-trading combinado solo se enciende cuando la opción 1 diga** "la combinación supera al momentum solo en Sharpe, sin empeorar el drawdown" — o, como mínimo, "mejora el retorno con riesgo-ajustado equivalente y cero names con sorpresa negativa dentro". Antes de ese gate, corren las dos señales por separado (frentes 1 y 3).

**Lo que NO debes hacer:** fusionar hoy, sin número, por la urgencia de "aprovechar que el duelo está en márgenes". Un día de validación vale más que una semana de paper fusionado a ciegas, y aquí la validación cuesta 1-2 días.

---

## 5. Criterio de decisión (cómo saber si la combinación funciona)

Define estos umbrales ANTES de mirar el resultado del backtest combinado (para no racionalizar después):

**Indicadores de éxito — TODOS deben cumplirse para fusionar:**
1. **Sharpe de la combinación ≥ Sharpe del momentum solo** (en el mismo periodo y universo). No basta "gana más": exijo no empeorar el riesgo-ajustado.
2. **Drawdown máximo de la combinación ≤ drawdown del momentum solo** (aprox., tolerancia ±1-2pp). Un refuerzo no debe añadir riesgo de cola.
3. **Correlación de la señal PEAD con la señal momentum < ~0.4** (medida: correlación de los *rankings* semanales). Si es >0.5, la "combinación" aporta poco y no justifica la complejidad.
4. **La combinación es estable, no dependiente de un solo `w`:** el resultado debe mantenerse para un rango de pesos, no solo para el `w` óptimo (sobreajuste a un punto).

**Indicadores de fracaso (cualquiera invalida la fusión):**
- La combinación empeora el Sharpe o el drawdown vs momentum solo.
- El rendimiento solo mejora *de media* pero concentra los retornos en un puñado de fechas de earnings (riesgo de calendario insano): comprobar que no hay >40% del alfa en el 10% de las fechas.
- La mejora desaparece si quitas 1-2 nombres "estrella" del PEAD (frágil ⇒ no robusto).

**Gate para el paper-trading combinado:** se enciende SOLO si el backtest manual (opción 1) cumple los 4 criterios de éxito. Si cumple una mayoría pero no todos, se puede experimentar en paper con la variante que falle menos, documentando la excepción. Si falla 2 o más, **no se fusiona: se queda el momentum con filtro negativo (opción 2) y se abandona la idea de ranking combinado** — habrás ahorrado meses de paper a ciegas.

**Criterio mínimo absoluto (si no hay ni Sharpe ni casi datos):** aun en el caso extremo de no poder validar nada, no fusiones. Corre PEAD como pierna separada. NUNCA arranques una estrategia combinada de la que no puedes describir, con números, por qué debería ser mejor que sus partes.

---

### Nota de honestidad (para Toni)

- El **~2 años de earnings** es la limitación más seria de todo el ejercicio: ~8 trimestres ⇒ ~8 observaciones de ciclo por nombre. Un IC 0.19-0.22 con esa muestra es prometedor pero con **amplio intervalo de confianza** — no lo trates como un número de 14 años de datos. Esto refuerza, no debilita, la recomendación de **refuerzo/filtro conservador** (frente 1) antes que de señal dominante.
- El momentum ya en vivo está **−2.45%** desde el 14-ago: eso es ruido de <1 semana, **no señal de nada**; no lo uses ni a favor ni en contra de fusionar.
- No estás perdiendo oportunidad por validar: en un horizonte de años, 1-2 días de validación son una fracción mínima del ruido que te ahorran.

**Convicción de esta recomendación: 8/10.** El esqueleto es sólido; lo único que la bajaría es si el backtest manual revelara que la interacción es negativa (en cuyo caso la recomendación pivota, limpiamente y con datos, al frente 1).

---

*Analista: Quinn · Documento interno de decisión · No es asesoramiento de inversión*
