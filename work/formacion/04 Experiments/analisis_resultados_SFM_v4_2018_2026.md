---
tags: [analysis, results, sfm, v4, crypto, 2018-2026, mse, inestable]
status: completed
date: 2026-06-03
---

# Análisis: Ejecución v4 con datos 2018-2026 (MSE)

> **Veredicto: Con datos desde 2018, el modelo pierde consistencia temporal.**
> Walk-Forward bipolar (σ=1.44), Top-K completamente negativo (0/5).
> La ventana más temprana (2020-2022) es desastrosa: equity 0.36x.

---

## 1. Configuración de la ejecución

| Parámetro | Valor |
|-----------|-------|
| **Rango temporal** | 2018-01-01 → 2026-06-01 |
| **Métrica de Optuna** | MSE (val_loss) — ejecución anterior al cambio a Sharpe |
| **Script** | `scripts/crypto/qlib_sfm_pipeline.v4.py` |
| **Fixes aplicados** | clipping, n_startup=10, batch [16,32], NaN/Inf handling en datos |

---

## 2. Estudio Optuna

| Métrica | Valor |
|---------|-------|
| Best val_loss | 0.002521 |
| Best params | hidden_dim=96, K=10, lr=0.00145, dropout=0.4, batch=32, wd=8.15e-5, lookback=25 |
| Trials completados | 49 |
| Trials pruned | 51 |
| Tiempo | 60.4 min |

---

## 3. Top-K (5 mejores por val_loss)

| Trial | Sharpe | Equity |
|-------|--------|--------|
| #1 | −0.59 | 0.50x |
| #2 | −0.44 | 0.60x |
| #3 | −0.25 | 0.61x |
| #4 | −0.21 | 0.72x |
| #5 | −0.85 | 0.37x |
| **Media** | **−0.47 (σ=0.24)** | **0.56x (σ=0.12)** |

**0/5 positivos.** El mejor trial (por val_loss) es el peor en Sharpe (−0.59).

---

## 4. Walk-Forward (3 ventanas)

| Ventana | Sharpe | Equity | Diagnóstico |
|---------|--------|--------|------------|
| 1 (~2020-2022) | **−1.20** | **0.36x** 🔴 | **Desastroso.** Pierde el 64% del capital |
| 2 (~2022-2024) | **+2.29** | **4.30x** 🟢 | **Espectacular.** Multiplica por 4.3x |
| 3 (~2024-2026) | **+1.00** | **1.60x** 🟢 | Bueno, consistente |
| **Media** | **+0.69 (σ=1.44)** | **2.08x (σ=1.64)** | ⚠️ Engañosa |

---

## 5. Comparativa con ejecución anterior (2023-2026 con fixes)

| Métrica | Anterior (2023-2026) | Nueva (2018-2026) | ¿Mejora? |
|---------|---------------------|-------------------|----------|
| val_loss | 0.00120 | 0.00252 | ❌ |
| Trials pruned | 57% | 51% | ⬇️ |
| Top-K Sharpe μ | −0.98 (σ=0.53) | −0.47 (σ=0.24) | ⬆️ |
| Top-K positivos | 1/5 | **0/5** | ❌ |
| Top-K Equity μ | 0.63x | 0.56x | ❌ |
| **WF Sharpe μ** | **+0.87 (σ=0.10)** 🟢 | **+0.69 (σ=1.44)** 🔴 | ❌ |
| **WF Equity μ** | **1.23x (σ=0.05)** 🟢 | **2.08x (σ=1.64)** 🔴 | ❌ |

---

## 6. Diagnóstico

### 🔴 Inestabilidad temporal severa

El modelo es **bipolar** entre ventanas:
- **Ventana 1**: pierde 64% del capital. El modelo apuesta sistemáticamente en la dirección equivocada.
- **Ventana 2**: multiplica por 4.3x. Resultado extraordinario, pero sospechoso de overfitting.
- **Ventana 3**: consistente con ejecuciones anteriores (~Sharpe +1.0).

### 🔴 Correlación val_loss vs Sharpe: r = −0.02

Sigue siendo prácticamente **cero**. El MSE no discrimina entre trials que generan alpha y trials que pierden dinero. **El cambio a Sharpe como métrica de Optuna es necesario.**

### 🔴 Top-K 0/5 positivos

Ni siquiera el mejor trial en validación da Sharpe positivo en test. El modelo no genera alpha en la partición test del split 70/15/15.

---

## 7. Posibles causas

1. **Non-stationarity del mercado**: 2018-2020 es un régimen muy diferente a 2021-2026 (COVID, bull market crypto, post-COVID). El modelo no puede generalizar entre regímenes tan distintos con una sola configuración de HPs.

2. **La ventana 1 incluye periodos de alta volatilidad atípica**: si el modelo no fue entrenado adecuadamente para esos regímenes, las predicciones pueden ser sistemáticamente wrong-way.

3. **MSE como métrica de optimización**: el modelo optimiza para minimizar error de predicción, no para maximizar rentabilidad ajustada a riesgo. Esto es especialmente dañino cuando los datos abarcan múltiples regímenes.

---

## 8. Lecciones aprendidas

| Lección | Implicación |
|---------|-------------|
| Más datos históricos **no siempre mejoran** el modelo | Incluir regímenes muy diferentes puede desestabilizar el modelo |
| La σ del Walk-Forward es la métrica clave | μ=0.69 con σ=1.44 es inútil; μ=0.87 con σ=0.10 es operativo |
| El MSE no sirve como métrica de optimización | r=−0.02 confirma que no discrimina. Sharpe en validación es el camino |

---

## 9. Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v4.py` — script con fixes y cambio a Sharpe
- `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md` — nota técnica
- `obsidian/01 Literature/formacion/qlib/sfm-comparativa-scripts.md` — comparativa de versiones
- `obsidian/04 Experiments/analisis_resultados_SFM_v4.md` — análisis primera ejecución (sin fixes)
- `obsidian/04 Experiments/analisis_resultados_SFM_v4_fixes.md` — análisis segunda ejecución (con fixes, 2023-2026)
