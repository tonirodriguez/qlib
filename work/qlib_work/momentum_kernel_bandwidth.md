# Ancho de banda del momentum: ¿aporta la ponderación por recencia?

> **Fecha:** 2026-10-18 (actualizado con el afilado h=35/50)
> **Script:** `work/estrategias/momentum_kernel_bandwidth.py`
> **Resultados:** `work/estrategias/momentum_kernel_bandwidth_results.json`
> **Estado:** experimento completado (7/7 variantes). Documento de decisión.

---

## 1. Qué propone el artículo

**Referencia:** Navnoor Bawa, *"Kernel Regression Is From 1964. Simons's Renaissance Ran It in 1988. AQR Proved a Cousin in 2024."* — Medium, 29-sep-2026.
(Referencia pendiente de citación académica precisa; el paper subyacente es Kelly, Malamud & Zhou, *"The Virtue of Complexity in Return Prediction"*, **Journal of Finance 2024**.)

La tesis del artículo:

1. **La regresión de kernel no es nueva.** Nadaraya-Watson la publican en 1964. Carmona la propone a Simons en 1987; Simons la llamó "caja negra", el equipo la probó igualmente y **Medallion arrancó en 1988 con ella**.
2. **El modelo de AQR de 2024 (Kelly-Malamud-Zhou) es un primo de esa técnica.** Usa 15 predictores estándar (los de Goyal-Welch) y ventanas de entrenamiento de hasta 12 meses. Reporta **Sharpe ≈ 0.47**, ratio de información 0.31 contra el mercado, **t ≈ 2.9-3.0**, sobre CRSP 1926-2020. El R² predictivo fuera de muestra es **negativo** — la virtud no está en predecir mejor, sino en que la *complejidad* (muchos parámetros) se regulariza implícitamente vía el kernel (random features de Rahimi-Recht).
3. **El único dial real es el ANCHO DE BANDA del kernel.** Reconstruyendo los pesos desde los datos públicos de Goyal: con la ventana de 12 meses del paper, **el kernel pone ~65 % del peso en los 3 meses más recientes** (mediana). Ensanchar la campana gaussiana hace que ese 65 % caiga al **25 %**, y entonces el modelo *es* una media móvil simple.
4. **La pregunta incómoda:** *"¿sobre cuántos meses está promediando de verdad la señal por la que pagas?"* La ventana nominal (12 meses) engaña: la ponderación efectiva no es uniforme.
5. **Reconstrucción propia del autor:** con ventana de 12 meses sobre Goyal, su rebuild da **Sharpe −0.10 en 2021-2025** (vs. 0.47 reportado en 1926-2020). Con el error estándar de un Sharpe a 5 años ≈ **0.45**, ese −0.10 **no se distingue de cero**. No es una refutación; es una advertencia de significancia estadística.
6. **Dos papers rivales marcan los extremos del dial:** el preprint de Guo (2026) con el setup exacto de KMZ da Sharpe 0.54/0.39/0.46 vs 0.52/0.35/0.43 de la media simple de 12 meses — casi indistinguibles; al *centrar los predictores*, caen a 0.21/0.00/0.12. El rival de Nagel defiende el lado de la recencia; el otro extremo es la media móvil.

**Lo que el artículo NO dice:** que la recencia sea una estrategia a copiar. Es un **método** (cómo medir memoria efectiva) y una **advertencia** (el Sharpe reportado tiene enorme incertidumbre y la ventana nominal miente).

---

## 2. Qué buscamos

Trasladar ese experimento a **nuestra** estrategia de momentum ya validada. La pregunta concreta:

> Si en lugar de la **media simple** de retornos diarios sobre 120 días usamos una **ponderación por kernel gaussiano sobre el lag** (mismo lookback máximo, 120 días), ¿mejora la relación rentabilidad/riesgo? ¿Y dónde está el óptimo?

Formulación de la señal:

```
w_i = exp( -(i)^2 / (2 h^2) ),   i = 0..119   (i = 0 es el día más reciente)
señal = Σ_i w_i · r_{t-i}   /   Σ_i w_i
```

- `h → ∞` ⇒ pesos uniformes ⇒ **momentum 120d clásico** (la referencia ya validada).
- `h` pequeño ⇒ **recencia extrema** (solo importan los últimos días).
- El **único parámetro que movemos es `h`**; todo lo demás (lookback 120d, motor, costes, rebalanceo) queda idéntico.

Métricas de "memoria efectiva" que medimos en paralelo:
- % del peso total que cae en los últimos **63 días** (≈ 3 meses, la métrica del artículo).
- % en los últimos 21 días y 5 días.
- nº de días necesarios para acumular el **99 %** del peso.

---

## 3. Universo de prueba

Definido en el propio script/JSON (`momentum_kernel_bandwidth_results.json`):

| Parámetro | Valor |
|---|---|
| **Universo** | `sp500_liquid` (S&P 500 filtrado por liquidez) |
| **Fuente de datos** | Qlib, `~/.qlib/qlib_data/us_data` (region US) |
| **Lookback máximo** | 120 días (idéntico en todas las variantes) |
| **Selección** | Top-30 por señal, `TopkDropoutStrategy` (n_drop = 5, hold_thresh = 20) |
| **Rebalanceo** | Semanal |
| **Ventana de backtest** | 2022-01-01 → 2026-08-07 (~4.6 años) |
| **Benchmark** | `^NDX` |
| **Costes** | Interactive Brokers: open 0.04 %, close 0.06 %, mínimo 1.0, limit_threshold 0.095, deal_price = close |
| **Motor** | Backtest de Qlib (`SimulatorExecutor`) |

Nota metodológica: es el **mismo setup** que `vol_gate_test.py`, para que los números sean directamente comparables con el momentum 120d ya documentado.

---

## 4. Qué obtenemos

### 4.1 Memoria efectiva por ancho de banda

| h (días) | peso últ. 63 d | peso últ. 21 d | peso últ. 5 d | días p/ 99 % del peso |
|---|---|---|---|---|
| **inf** (media simple 120d) | 0.525 | 0.175 | 0.042 | 119 |
| 60 | 0.738 | 0.285 | 0.069 | 116 |
| 50 | 0.804 | 0.329 | 0.080 | 112 |
| 40 | 0.885 | 0.399 | 0.099 | 100 |
| 35 | 0.927 | 0.449 | 0.112 | 90 |
| 25 | 0.988 | 0.594 | 0.156 | 65 |
| 15 | 1.000 | 0.833 | 0.256 | 39 |

**Lectura:** la media simple 120d ya concentra un 52.5 % del peso efectivo en los 3 meses recientes. Estrechar el kernel concentra el peso hacia el presente: a `h = 15` el 100 % del peso cae en los últimos 63 días y el 83 % en los últimos 21. El descenso del nº de días para el 99 % del peso es monótono con `h` — aquí no hay sorpresas.

### 4.2 Backtest (ordenado por Sharpe)

| Variante | Sharpe | MaxDD | Anual | ΔSharpe vs. base |
|---|---|---|---|---|
| **kernel h=35d** | **1.215** | −22.4 % | **30.2 %** | **+0.294** |
| kernel h=40d | 1.109 | −22.7 % | 23.6 % | +0.188 |
| kernel h=60d | 1.048 | −23.1 % | 23.8 % | +0.127 |
| momentum 120d (media simple) | 0.921 | −18.3 % | 18.4 % | — |
| kernel h=25d | 0.900 | −23.0 % | 17.2 % | −0.021 |
| kernel h=50d | 0.800 | −22.9 % | 16.7 % | −0.121 |
| kernel h=15d | 0.756 | −24.3 % | 15.2 % | −0.165 |

### 4.3 Conclusiones — con una advertencia importante

1. **El mejor punto del grid es `h ≈ 35d`**: Sharpe 1.215 (+0.29) y rentabilidad 30.2 % anual. El óptimo interior se confirma entre h=60 y h=25; los extremos (h=15 y la propia media simple) son peores.
2. ⚠️ **PERO la curva es DENTADA, no suave.** Grid completo:
   `inf 0.921 → 60: 1.048 → 50: 0.800 → 40: 1.109 → 35: 1.215 → 25: 0.900 → 15: 0.756`
   Hay un **valle en h=50** (0.800, peor que h=60 y que h=40) y un **pico en h=35** (1.215). Un efecto real de ancho de banda debería ser *suave y monótono a cada lado del óptimo*. Este zigzag (sube 60, baja 50, sube 40 y 35) es la firma típica de **ruido / data-snooping**, no de una estructura económica estable. Afilar el grid con h=35 y h=50 era justo lo que hacía falta para verlo — y lo confirma: **el h=50 intermedio no está entre 60 y 40, está por debajo de ambos.**
3. ⚠️ **La mejora viene con DRAWDOWN MÁS PROFUNDO** en todas las variantes de kernel (−22 % a −24 % vs −18.3 % de la media simple). El kernel gana por *rentabilidad bruta*, no por *reducir riesgo*.
4. **Conclusión honesta:** el "óptimo" h=35 **no debe tomarse como hallazgo firme todavía**. Es un candidato prometedor que exige el análisis de robustez del punto 5.2 antes de decidir nada. Presentarlo como "encontramos el mejor ancho de banda" sería precisamente el error que el artículo denuncia (confundir un Sharpe puntual con evidencia).

---

## 5. Próximos pasos

### Inmediatos (bajo coste)
1. ~~Afilar el óptimo~~ ✅ **hecho**: h=35 (1.215) y h=50 (0.800) añadidos. El valle en h=50 descarta que el grid sea suave.
2. **Robustez temporal (AHORA CRÍTICA):** partir el backtest en sub-periodos (2022-23 / 2024 / 2025-26) y ver si h=35 sigue ganando en cada uno. Dada la dentición de la curva, **esto es lo que separa un hallazgo real de un artefacto.** Si h=35 gana solo por un tramo concreto, es overfit.
3. **Sensibilidad a costes y turnover:** una señal que pesa más lo reciente suele operar más. Medir el **turnover por variante** (no medido aún) y ver si la ventaja de h=35 sobrevive en neto tras fricción.
4. **Bootstrap / intervalos de confianza:** remuestrear los retornos semanales por bloques y ver si el ΔSharpe +0.29 de h=35 cae dentro del ruido. El SE de un Sharpe a 4.6 años es alto; con la curva dentada, la duda es legítima.

### De decisión (más peso)
5. **Aplicar el lente de "memoria efectiva" a nuestras OTRAS señales** (vol-gate, PEAD, E3): preguntarnos cuántos días promedian *de verdad*. Es el método del artículo, no la estrategia.
6. **Importar la disciplina estadística:** reportar **intervalos de confianza** de nuestros Sharpe, no solo el punto. Un ΔSharpe de +0.29 sobre 4.6 años puede no ser significativo.
7. **Decidir si `h=35` entra en producción.** Requiere: (a) el análisis de robustez del punto 2, (b) aceptar el DD más profundo o combinarlo con el vol-gate para domarlo, (c) verificar que el turnover extra no se come la mejora en neto tras costes.

### Lo que NO haremos
- **No copiar el modelo de AQR de 2024** (Sharpe reportado 0.47 con SE alto, R² OOS negativo y rebuild a −0.10 en 2021-25). Se usa como **método y como vara de medir**, no como estrategia.
- **No confundir "kernel" con magia**, ni presentar h=35 como óptimo firme mientras la curva siga dentada y falte el test de robustez.

---

## Anexo — Reproducibilidad

```bash
cd /opt/data/qlib/work/estrategias
export MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1   # evita OOM
/opt/data/qlib-venv/bin/python momentum_kernel_bandwidth.py                 # todas (7)
/opt/data/qlib-venv/bin/python momentum_kernel_bandwidth.py --only 35       # una sola
```

**Nota de robustez del script:** la ejecución en lote moría por **OOM** (`exit 137`, `oom_kill`, swap lleno) al acumular variantes — `kernel_momentum()` creaba 120 DataFrames intermedios. Se vectorizó (un solo acumulador in-place) y se añadió ejecución por variantes aisladas con **guardado incremental** al JSON. Cada variante se ejecuta ahora en su propio proceso; el bloque de *memoria efectiva* se recalcula siempre completo para no machacar perfiles.

*Documento de referencia del proyecto Qlib Work.*
