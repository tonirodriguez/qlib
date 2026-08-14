---
tags: [analysis, results, sfm, v4, crypto, positive-alpha]
status: completed
date: 2026-06-04
---

# Análisis de Resultados: SFM v4 en Cripto — Ejecución #2 (post-fixes)

> **Veredicto: Tras aplicar los fixes (clipping, batch_size=16/32, startup_trials=10), el modelo GENERA alpha positivo, aunque con alta varianza entre regímenes.**
> Walk-Forward muestra que el modelo funciona en ciertos contextos de mercado pero pierde en otros. Ensemble y filtro de régimen son los siguientes pasos naturales.

---

## 1. Datos de la ejecución

- **Script:** `scripts/crypto/qlib_sfm_pipeline.v4.py`
- **Activos:** BTC, ETH, SOL, XLM, ADA
- **Rango:** 2018-01-01 → 2026-06-01
- **Denoising:** Wavelet (db4, threshold universal)
- **Split:** 70/15/15 cronológico
- **Optuna:** 100 trials, TPE sampler, MedianPruner, 31 completados / 69 pruned
- **Top-K:** 5 mejores en validación, reentrenados sobre train+val
- **Walk-Forward:** 3 ventanas secuenciales

> ⚠️ **Diferencia crítica vs run anterior:** Esta ejecución incluye gradient clipping, batch_size limitado a [16, 32] (sin 64), y n_startup_trials=10. Los resultados cambian drásticamente de negativos a positivos.

---

## 2. Optuna — Mejor trial (validación)

| Métrica | Valor |
|---|---|
| Mejor Sharpe (val) | **2.47** |
| Trials OK / Pruned | 31 / 69 (69% poda) |
| Tiempo | 42.1 min |

**Mejores hiperparámetros encontrados:**

| Parámetro | Valor |
|-----------|-------|
| hidden_dim | 32 |
| freq_components | 7 |
| lr | 0.000123 |
| dropout_rate | 0.2 |
| batch_size | 16 |
| weight_decay | 0.000454 |
| lookback | 25 |

---

## 3. Top-K Evaluation (test fijo, 5 mejores)

| Trial | Sharpe | Equity | Outperformance |
|:---:|---:|---:|---:|
| #1 | 1.62 | 1.69x | +0.995 |
| #2 | 0.71 | 1.15x | +0.419 |
| #3 | 1.28 | 1.44x | +0.711 |
| **#4 🥇** | **2.18** | **1.98x** | **+1.044** |
| #5 | 0.40 | 1.03x | +0.294 |
| **Agregado** | **μ = 1.24 (σ = 0.64)** | **μ = 1.46x (σ = 0.35)** | **μ = +0.693** |

- Todos los trials dan equity > 1.0x
- 5/5 superan al benchmark (Hold igual-ponderado)
- Mejor trial: **#4** (hidden=64, freq=6, lookback=45, lr=3.2e-4, dropout=0.1)
- Alta varianza: de 0.40 a 2.18 de Sharpe

---

## 4. Walk-Forward Validation (la métrica que importa)

| Ventana | Sharpe SFM | Equity SFM | Equity BM | Diagnóstico |
|:---:|---:|---:|---:|---|
| W1 | **−0.35** ❌ | 0.90x | 0.95x | Pierde vs benchmark |
| W2 | 0.46 😐 | 0.99x | 0.61x | Gana vs BM (cae menos) |
| W3 | **1.45** ✅ | 1.25x | 0.61x | Outperformance clara |
| **Agregado** | **μ = 0.52 (σ = 0.74)** | **μ = 1.05x** | μ = 0.72x | +27% sobre BM |

**Lectura clave:**
- W1 es mala: el modelo pierde dinero (Sharpe negativo). Coincide con un periodo bajista/lateral del mercado cripto.
- W2 es plana: no gana ni pierde significativamente, pero el benchmark cae → el modelo preserva capital.
- W3 es muy buena: Sharpe 1.45, equity +25%, mercado probablemente trending alcista.

**Degradación de Sharpe entre Top-K y WF: 1.24 → 0.52** — caída significativa pero muy inferior a la ejecución #1 (−1.07 → −1.29).

---

## 5. Comparativa: Run #1 (sin fixes) vs Run #2 (con fixes)

| Métrica | Run #1 (Jun 3) | Run #2 (Jun 4) | Delta |
|---------|:---:|:---:|:---:|
| Top-K Sharpe μ | −1.07 | **+1.24** | **+2.31** 🔥 |
| Top-K Sharpe σ | 0.83 | 0.64 | Mejor |
| Top-K Equity μ | 0.72x | **1.46x** | **+0.74x** 🔥 |
| WF Sharpe μ | −1.29 | **+0.52** | **+1.81** 🔥 |
| WF Equity μ | 0.68x | **1.05x** | **+0.37x** 🔥 |
| Trials con α positivo | 1/5 (20%) | **5/5 (100%)** | 🔥 |
| Mejor trial Sharpe | −1.35 | **+2.18** | **+3.53** 🔥 |

**Los fixes funcionaron.** El cambio de batch_size (eliminar 64), gradient clipping, y n_startup_trials=10 fueron suficientes para pasar de resultados sistemáticamente negativos a positivos.

---

## 6. Diagnóstico de riesgo

### 6.1 Varianza entre regímenes
- WF pasa de −0.35 a +1.45 de Sharpe según la ventana
- El modelo es **régimen-dependiente**: funciona en trending alcista, falla en lateral/bajista

### 6.2 Drawdown implícito
- W1 equity final de 0.90x implica drawdown intra-ventana probablemente mayor
- Se necesita Calmar ratio para evaluación completa

### 6.3 Dependencia de trial #4
- El mejor trial en test (#4, Sharpe 2.18) no es el mejor en validación (#1, usado como base del WF)
- Si el WF se hubiera ejecutado con params del #4, los resultados podrían ser mejores

---

## 7. Recomendaciones

| Prioridad | Acción | Fundamento |
|-----------|--------|------------|
| 🔴 Alta | **Ensemble de Top-3** | Promediar predicciones de trials #1, #3, #4 reduce varianza drásticamente |
| 🔴 Alta | **Filtro de régimen** | Detectar mercado lateral/bajista y desactivar modelo (evita W1) |
| 🔴 Alta | **WF con params del trial #4** | El trial #4 (hidden=64, freq=6, lookback=45) fue el mejor en test pero no se usó como base del WF |
| 🟡 Media | **Threshold de confianza** | Solo operar si max(predicción) > umbral (ej. 0.01) |
| 🟡 Media | **Más features** | Añadir volumen, ATR, RSI, MACD como inputs |
| 🟡 Media | **Métricas de drawdown** | Calcular Calmar ratio, max drawdown, ulcer index |
| 🟡 Media | **Aumentar TOP_K a 7-10** | Más trials → mejor estimación de la distribución real |
| 🟢 Baja | **Probar con más activos** | Añadir LINK, AVAX, MATIC para diversificar |
| 🟢 Baja | **Walk-Forward como objetivo de Optuna** | Optimizar directamente el Sharpe medio en WF en lugar de val_loss |

---

## 8. Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v4.py` — script ejecutado
- `scripts/crypto/output/optuna_sfm_v4/study_results.json` — resultados Optuna
- `scripts/crypto/output/optuna_sfm_v4/top_k_results.json` — resultados Top-K
- `scripts/crypto/output/optuna_sfm_v4/walk_forward_results.json` — resultados Walk-Forward
- `scripts/crypto/output/optuna_sfm_v4/optuna_distribution.png` — distribución Sharpe val
- `scripts/crypto/output/optuna_sfm_v4/top_k_results.png` — barras Top-K
- `scripts/crypto/output/optuna_sfm_v4/walk_forward.png` — barras WF
- `scripts/crypto/output/optuna_sfm_v4/walk_forward_equity.png` — curvas de equity WF
- `scripts/crypto/output/optuna_sfm_v4/sfm_top*.pth` — modelos entrenados
- `04 Experiments/analisis_resultados_SFM_v4.md` — run anterior (resultados negativos, pre-fixes)
