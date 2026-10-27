# Auditoría — ¿El ranking de momentum aporta algo?

> **Fecha:** 2026-10-27
> **Script:** `work/estrategias/audit_momentum_alpha.py`
> **Objeto:** la premisa del proyecto — que rankear por momentum 120d y
> comprar el top-30 genera alfa de selección
> **Veredicto:** 🔴 **No aporta valor ajustado por riesgo.**

---

## 1. La pregunta correcta

El IC cross-sectional del momentum es **≈0 o negativo** en los horizontes donde
opera la estrategia (`auditoria_ic_momentum.md`). Pero el IC mide correlación
lineal de rango, y una estrategia top-30 es de **selección de cola**: puede
ganar por unas pocas posiciones aunque el IC promedio sea cero.

Así que la pregunta no es "¿hay IC?" sino:

> **¿El top-30 bate a 30 acciones elegidas al azar del mismo universo?**

Comparar contra un índice (^NDX, S&P) mezcla selección con beta y con
diferencias de volatilidad. Comparar contra carteras aleatorias del **mismo
universo y mismo tamaño** aísla la habilidad de selección.

### Diseño

| Cartera | Qué es |
|---|---|
| **TOP-30** | Mayor momentum 120d, rebalanceo semanal |
| **BOTTOM-30** | Menor momentum (control de signo) |
| **500 aleatorias de 30** | Distribución de resultados **sin** habilidad |
| **EW universo** | Equal-weight de los 283 (referencia práctica) |

Mismo calendario, mismos costes (5 bps). El top debe superar el **percentil 95**
de la distribución aleatoria para afirmar que el ranking aporta.

---

## 2. Resultados — periodo completo (2018-2026, 8,8 años)

| Cartera | CAGR | vol | Sharpe | maxDD |
|---|---:|---:|---:|---:|
| **TOP-30 momentum** | 10.3% | 20.1% | **0.59** | −36.9% |
| **BOTTOM-30 (inverso)** | **18.1%** | 28.7% | **0.72** | −54.5% |
| **EW universo (283)** | **12.2%** | 19.0% | **0.70** | −38.7% |
| aleatoria-30 (mediana) | 9.6% | — | 0.57 | — |

**Percentil del TOP-30: 57 de Sharpe, 62 de CAGR.**
Distribución aleatoria: p05=0.42, p50=0.57, **p95=0.70**.

El top-30 está **exactamente en la mediana**. Y pierde contra el equal-weight
del universo y contra su propio inverso.

---

## 3. Resultados — subperiodo del backtest original (2022-2026, 4,6 años)

| Cartera | CAGR | vol | Sharpe | maxDD |
|---|---:|---:|---:|---:|
| **TOP-30 momentum** | **17.0%** | 17.6% | **0.98** | −18.0% |
| **BOTTOM-30 (inverso)** | **21.9%** | 21.2% | **1.04** | −20.4% |
| **EW universo (283)** | 14.9% | 14.4% | **1.04** | −16.5% |
| aleatoria-30 (mediana) | 12.2% | — | 0.84 | — |

**Percentil del TOP-30: 81 de Sharpe, 96 de CAGR.**
Distribución aleatoria: p05=0.61, p50=0.84, **p95=1.09**.

Aquí el top-30 **sí bate al azar en retorno bruto** (percentil 96 de CAGR).
Pero **no en Sharpe** (81 < 95): gana más porque asume más riesgo.

---

## 4. Lo que no cambia con la ventana — y es lo decisivo

Tres hechos idénticos en ambos periodos:

### 4.1 El inverso no es peor

| Periodo | TOP Sharpe | BOTTOM Sharpe |
|---|---:|---:|
| 2018-2026 | 0.59 | **0.72** |
| 2022-2026 | 0.98 | **1.04** |

Si el ranking tuviera información direccional, comprar los peores debería
quedar sistemáticamente peor. **No ocurre en ninguna de las dos ventanas.**

**Matiz importante:** la ventaja del BOTTOM en CAGR (18.1% vs 10.3%) viene de
**más beta**, no de señal invertida: su volatilidad es 28.7% vs 20.1%. En
Sharpe quedan casi empatados. Conclusión: el ranking **no discrimina en
ninguna dirección**.

### 4.2 El índice simple empata o gana

| Periodo | TOP Sharpe (vol) | EW Sharpe (vol) |
|---|---|---|
| 2018-2026 | 0.59 (20.1%) | **0.70** (19.0%) |
| 2022-2026 | 0.98 (17.6%) | **1.04** (14.4%) |

Comprar los 283 a partes iguales da **mejor Sharpe con menos volatilidad**, sin
rotación y sin coste de investigación. El ranking no aporta nada que el
equal-weight no dé.

### 4.3 El percentil de Sharpe nunca llega a 95

57 en el periodo completo, 81 en el favorable. El umbral para afirmar
habilidad de selección no se alcanza **en ninguna ventana**.

---

## 5. Por qué el backtest daba +18.5% y Sharpe 0.96

Dos razones, ninguna fraudulenta, ambas importantes:

**1. La ventana.** El backtest original corrió **2022-01-01 → 2026-08-07**
(4,6 años), excluyendo 2018-2021: el crash COVID y el *momentum crash* de
2021, justo los periodos donde el momentum sufre. En el periodo completo
(8,8 años) el CAGR baja de 17.0% a **10.3%** y el Sharpe de 0.98 a **0.59**.

Elegir el periodo después de ver los resultados es una forma de overfitting.
Aquí es el mecanismo principal detrás del número documentado.

**2. El coste de rotación.** Esta simulación reconstruye el top-30 cada semana
(rotación alta). La estrategia viva usa `TopkDropout` con `n_drop=5` y
`hold_thresh=20`, que rota menos. Es decir: **esta simulación es un test más
duro que la estrategia real**.

Pero eso no afecta a la comparación, porque las 500 carteras aleatorias tienen
**la misma estructura de rotación**. El percentil es la métrica válida y es
independiente de esa diferencia.

---

## 6. Un bug de look-ahead encontrado en el propio audit

La primera versión de `simulate()` usaba `searchsorted(side="right")`, así que
el día del rebalanceo aplicaba los pesos **nuevos** al retorno de **ese mismo
día**, que ya había ocurrido: se decidía con el cierre que se estaba usando
como rentabilidad.

**Lo delató el test sintético:** en un mercado **aleatorio** (donde el momentum
no puede predecir por construcción), el top-30 daba **percentil 100**
(Sharpe +1.08 vs azar −0.46). Imposible sin fuga.

Corregido a `side="left"-1` (se opera al cierre; los pesos nuevos empiezan al
día siguiente): el percentil baja a **68**, dentro de la distribución aleatoria.

**Sin ese test, el resultado real habría salido inflado y lo habría presentado
como un hallazgo.**

---

## 7. Veredicto

> **El ranking de momentum 120d no aporta valor ajustado por riesgo sobre el
> universo sp500_liquid en 2018-2026.**

- Percentil 57 de Sharpe en el periodo completo (mediana del azar).
- Percentil 81 en el subperiodo favorable: retorno bruto por encima del azar,
  pero **no riesgo-ajustado**.
- El inverso del ranking no es peor → no hay información direccional.
- El equal-weight del universo empata o gana con menos volatilidad.

**El retorno de las carteras vivas (E1/E2/E3) es exposición al mercado
americano, no selección de acciones.** El coste de rotación semanal se paga
por una señal que no discrimina.

---

## 8. Qué hacer

### Decisión sobre las carteras vivas

**Si el objetivo es exposición a renta variable US:** el equal-weight del
universo da mejor Sharpe con menos volatilidad y sin rotación. Es más simple,
más barato y no requiere investigación.

**Si el objetivo es alfa de selección:** el momentum 120d no lo proporciona en
este universo. Hay que buscar otra señal.

### La única pista con evidencia

El IC es **consistentemente negativo a 10-30 días** (label 10d: −0.005;
20d: −0.010; 30d: −0.011), y el BOTTOM-30 rinde más que el TOP-30 en ambos
periodos. Eso apunta a **reversión de corto plazo**, un efecto documentado
(Jegadeesh 1990, Lehmann 1990) y distinto del momentum.

**No adoptarlo con esta evidencia.** El test correcto sería un long-short
beta-neutral sobre el mismo universo. Pero es la línea con más fundamento de
las exploradas.

### Lo que NO hacer

Seguir midiendo variantes de momentum (ventanas, topk, filtros PEAD) sobre la
misma premisa que acaba de fallar el test decisivo.

---

## 9. Balance de las auditorías

| # | Artefacto | Fallo |
|---|---|---|
| 1 | Config SP500 | No existía |
| 2 | `vol_pct` (mi aviso) | Falso positivo — era causal |
| 3 | Entorno qlib | xgboost roto |
| 4 | `vol_gate` | Mecanismo inerte |
| 5 | SFM v8 | 3 leaks de futuro |
| 6 | `momentum_vt` | Import roto |
| 7 | CSI300 | Contradicción documental |
| 8 | IC 0.066 del momentum | No reproducible; el real es 0.032 y no significativo |
| 9 | **Ranking de momentum** | **No aporta vs carteras aleatorias** |

**Patrón:** de nueve artefactos, ocho presentaban un número que no resistía una
comprobación. El único falso positivo fui yo (el `vol_pct`).

---

*Auditoría realizada el 2026-10-27. 500 carteras aleatorias por periodo.
Lógica validada con mercados sintéticos antes de usarla con datos reales.*
