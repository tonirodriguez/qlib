---
tags: [comparativa, v4, v5, sfm, sp500, crypto]
status: completed
date: 2026-06-03
---

# Comparativa: SFM v4 (Cripto) vs v5 (SP500)

> **Propósito:** La v5 es un port de la v4 al mercado de acciones US. Aquí se documentan todas las diferencias arquitectónicas, de estrategia y de datos entre ambas versiones, incluyendo el fundamento de cada cambio.

---

## 1. Visión general

| Aspecto | v4 (cripto) | v5 (SP500) |
|---------|-------------|------------|
| **Script** | `scripts/crypto/qlib_sfm_pipeline.v4.py` | `scripts/crypto/qlib_sfm_pipeline.v5.py` |
| **Output** | `scripts/crypto/output/optuna_sfm_v4/` | `scripts/crypto/output/optuna_sfm_v5/` |
| **Líneas** | ~914 | ~966 |
| **Pipeline común** | SFM + Wavelet Denoising + Optuna (100 trials) + Top-K (5) + Walk-Forward (3 ventanas) | ✅ idéntico | ✅ idéntico |

---

## 2. Datos de entrada

| Aspecto | v4 | v5 | Fundamento del cambio |
|---------|----|----|-----------------------|
| **Activos** | 5 cryptos (btc, eth, sol, xlm, ada) | **40 stocks** SP500 multi-sector | Validar si SFM generaliza a otros mercados |
| **Carga de datos** | `load_and_process_crypto_data()` | `load_and_process_sp500_data()` | API diferente: crypto usa `\` y fetching manual; SP500 usa `D.features()` |
| **Rango temporal** | 2023-01-01 → 2026-06-01 (3.5 años) | **2020-01-01 → 2026-06-01** (6.5 años) | Más datos → mejor entrenamiento; SP500 tiene datos históricos más largos |
| **Features** | close, pct_change, ratio MA5/close | close, pct_change, ratio MA5/close | ✅ mismos features, misma lógica |
| **Denoising** | Wavelet (db4) | Wavelet (db4) | ✅ idéntico |

### Sectores cubiertos en v5

| Sector | Stocks |
|--------|--------|
| 🖥️ Tech | AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, AMD, CRM, CSCO |
| 💰 Financiero | JPM, BAC, GS, V, MA |
| 💊 Farma/Salud | JNJ, PFE, UNH, ABBV, MRK |
| ⛽ Energía | XOM, CVX, COP |
| 🛒 Consumo | WMT, PG, KO, PEP, COST |
| 🏗️ Industrial | BA, CAT, GE, MMM, HD, LOW |
| 🎬 Varios | DIS, NFLX, NKE, IBM, T |

---

## 3. Extracción de datos: v4 vs v5

### v4 — Cripto

```python
def load_and_process_crypto_data(cryptos, start_date, end_date, ...):
```

Usa datos locales de cripto (descargados con ccxt o similares). El DataFrame se construye desde listas de precios por cripto y se pivota por fecha. No usa Qlib `D.features()`.

### v5 — SP500

```python
def load_and_process_sp500_data(stocks, start_date, end_date, ...):
```

Usa **Qlib `D.features()`** con los instrumentos del SP500 cargados en el proveedor US de Qlib. Hace pivot por instrumento para construir la matriz multi-activo.

```python
df_qlib = D.features(stocks, fields, start_time=start_date, end_time=end_date)
df_close = df_reset.pivot(index='datetime', columns='instrument', values='$close')
```

Filtra activos que no tengan datos completos y elimina filas con NaNs.

---

## 4. Estrategia de trading

| Aspecto | v4 (cripto) | v5 (SP500) | Fundamento |
|---------|-------------|------------|------------|
| **Estrategia** | **Top-1 Long**: compra la crypto con mayor predicción positiva | **Long/Short Top-1**: long la mejor predicción, short la peor | En SP500, el short está disponible y permite capturar alpha incluso en mercados laterales |
| **Costes** | **0.1%** (solo compra) | **0.2%** (compra + venta short, dos piernas) | Refleja el coste real del long/short |
| **Benchmark** | Media simple de las 5 cryptos | Media simple de los 40 stocks (equally-weighted) | Mismo concepto, más activos |
| **Caso borde** | Si todas las predicciones son negativas, no opera (return 0) | Si el mejor y el peor coinciden (todas iguales), no opera | Misma lógica de protección |

### Código v4 (estrategia)

```python
# Por cada día: elige la crypto con mayor predicción
best_asset = np.argmax(preds, axis=1)
strategy_returns = np.array([real[t, best_asset[t]] for t in range(len(best_asset))])
strategy_returns -= 0.001  # costes 0.1%
```

### Código v5 (estrategia)

```python
# Por cada día: long la mejor predicción, short la peor
for t in range(n_samples):
    idx_max = np.argmax(pred_t)
    idx_min = np.argmin(pred_t)
    if idx_max == idx_min:
        strategy_returns[t] = 0.0  # todas iguales → no operar
    else:
        strategy_returns[t] = real_t[idx_max] - real_t[idx_min]
strategy_returns -= 0.002  # costes 0.2%
```

---

## 5. Métricas de evaluación

| Métrica | v4 | v5 | ¿Cambio? |
|---------|----|----|---------|
| test_loss (MSE) | ✅ | ✅ | idéntico |
| Sharpe Ratio | ✅ (anualizado ×√252) | ✅ (anualizado ×√252) | idéntico |
| Equity final | ✅ | ✅ | idéntico |
| Benchmark final | ✅ | ✅ | idéntico |
| Outperformance | ✅ (equity − benchmark) | ✅ (equity − benchmark) | idéntico |
| Directional accuracy | ✅ | ✅ | idéntico |
| Sharpe del benchmark | ❌ no se calcula | ✅ se calcula en gráfica WF | leve mejora |

---

## 6. Visualizaciones

| Output | v4 | v5 |
|--------|----|----|
| `optuna_distribution.png` | ✅ histograma + barras completados/pruned | ✅ idéntico |
| `top_k_results.png` | ✅ barras Sharpe + equity por trial | ✅ idéntico |
| `walk_forward.png` | ✅ Sharpe + equity (barras) por ventana | ✅ idéntico |
| `walk_forward_equity.png` | ✅ curvas SFM vs Baseline con Sharpe | ✅ idéntico (etiquetas: "Baseline" en vez de "Benchmark") |

---

## 7. Resumen de diferencias en tabla completa

| Dimensión | v4 | v5 |
|-----------|----|----|
| **Activos** | 5 cryptos | 40 stocks SP500 |
| **Sectores** | 1 (cripto) | 7 (tech, finanzas, salud, energía, consumo, industrial, varios) |
| **Rango temporal** | 2023–2026 (3.5 años) | 2020–2026 (6.5 años) |
| **Carga de datos** | Función propia (crypto) | `D.features()` de Qlib |
| **Estrategia** | Top-1 Long | Long/Short Top-1 |
| **Costes transacción** | 0.1% | 0.2% |
| **Dimensionalidad features** | 15 (3 features × 5 cryptos) | **120** (3 features × 40 stocks) |
| **Dimensionalidad output** | 5 (una por crypto) | **40** (una por stock) |
| **Modelo SFM** | mismo | mismo |
| **Optuna** | 100 trials, batch [16,32] | 100 trials, batch [16,32] |
| **Gradient clipping** | ✅ max_norm=1.0 | ✅ max_norm=1.0 |
| **n_startup_trials** | 10 | 10 |
| **Denoising** | Wavelet db4 | Wavelet db4 |
| **Top-K** | 5 | 5 |
| **Walk-Forward** | 3 ventanas | 3 ventanas |
| **Tiempo estimado** | ~35 min | ~60–90 min (por 8x más dimensionalidad) |

---

## 8. Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v4.py` — script v4
- `scripts/crypto/qlib_sfm_pipeline.v5.py` — script v5
- `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md` — nota técnica v4
- `obsidian/01 Literature/formacion/qlib/sfm-comparativa-scripts.md` — comparativa v1→v4
- `obsidian/04 Experiments/analisis_resultados_SFM_v4.md` — análisis resultados v4 (sin fixes)
- `obsidian/04 Experiments/analisis_resultados_SFM_v4_fixes.md` — análisis resultados v4 (con fixes)
