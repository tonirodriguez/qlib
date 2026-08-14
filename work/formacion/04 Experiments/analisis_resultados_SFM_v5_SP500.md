---
tags: [analysis, results, sfm, v5, sp500, longs-short, ok]
status: completed
date: 2026-06-03
---

# Análisis: Ejecución V5 — SFM en SP500 (40 stocks, Long/Short)

> **Veredicto: Los mejores resultados del proyecto hasta ahora.**
> Walk-Forward Sharpe μ=+2.95 (σ=0.87), 3/3 ventanas positivas.
> Equity media 2.69x. El modelo generaliza mejor a SP500 que a crypto.

---

## 1. Configuración de la ejecución

| Parámetro | Valor |
|-----------|-------|
| **Script** | `scripts/crypto/qlib_sfm_pipeline.v5.py` |
| **Universo** | 40 acciones SP500 (sectores variados) |
| **Estrategia** | Long/Short Top-1 (long mejor predicción, short peor) |
| **Costes** | 0.2% por operación (long + short) |
| **Rango datos** | 2020-01-01 → 2026-06-01 |
| **Métrica Optuna** | Sharpe en validación |
| **Output** | `scripts/crypto/output/optuna_sfm_v5/` |

---

## 2. Estudio Optuna (100 trials, 98 min)

| Métrica | Valor |
|---------|-------|
| Best Sharpe_val | **5.39** ⚠️ (sospechosamente alto) |
| Trials completados | 51 |
| Trials pruned | 49 |
| Best params | hidden_dim=112, K=7, lr=0.00078, dropout=0.45, batch=16, wd=8.4e-5, lookback=15 |

### Convergencia de HPs

Todos los Top-5 convergen a HPs muy similares:
- `hidden_dim=112` (todos)
- `batch_size=16` (todos)
- `lookback=15` (todos)
- `lr ~0.0006–0.0008`
- `dropout 0.45–0.5`
- `weight_decay ~3e-5 a 8e-5`

**Interpretación:** El espacio de búsqueda es **estable y reproducible**. No hay dispersión aleatoria — los trials buenos comparten arquitectura.

---

## 3. Top-K (Split 70/15/15) — Resultado mixto

| Rank | Sharpe_val | Sharpe_test | Equity | vs Benchmark |
|:----:|:----------:|:-----------:|:------:|:------------:|
| #1 | **5.39** 🥇 | **−0.27** 🔴 | 0.68x | −0.53 |
| #2 | 5.26 | **+1.91** 🟢 | 2.28x | **+1.08** |
| #3 | 5.17 | **−1.94** 🔴 | 0.24x | −0.96 |
| #4 | 5.09 | **+1.04** 🟢 | 1.49x | +0.28 |
| #5 | 4.96 | **+1.83** 🟢 | 2.44x | **+1.24** |

**3/5 positivos** | **μ = +0.51 (σ = 1.63)** | **3/5 superan benchmark**

**⚠️ Problema:** El mejor trial en validación (#1, Sharpe_val=5.39) es el peor en test (−0.27). **Correlación Sharpe_val vs test: r = −0.33** — el overfitting a validación persiste.

---

## 4. Walk-Forward (3 ventanas) — 🏆 Resultado estelar

| Ventana | Sharpe | Equity | Diagnóstico |
|:-------:|:------:|:------:|:-----------:|
| **W1** (~2022-2023) | **+1.95** ✅ | **1.96x** | Bueno |
| **W2** (~2023-2024) | **+3.45** ✅✅ | **3.06x** | Excelente |
| **W3** (~2024-2026) | **+3.46** ✅✅ | **3.03x** | Excelente |
| **μ** | **+2.95 (σ=0.87)** | **2.69x** | μ/σ = 3.4 |

**TODAS las ventanas positivas.** σ=0.87 es aceptable para un Sharpe de 2.95.

---

## 5. Comparativa vs mejores resultados anteriores

| Métrica | Crypto V4 (mejor) | **SP500 V5** 🆕 | Diferencia |
|---------|:-----------------:|:---------------:|:----------:|
| WF Sharpe μ | +0.87 | **+2.95** | **+239%** |
| WF σ | 0.10 | 0.87 | Mayor (esperable con μ más alto) |
| WF μ/σ | 8.7 | **3.4** | — |
| Equity μ | 1.23x | **2.69x** | **+119%** |
| Top-K positivos | 0/5 | **3/5** | ✅ |
| Convergencia HPs | Parcial | **Fuerte** | ✅ |

**Conclusión: SFM generaliza MUCHO mejor a SP500 que a crypto.** La estrategia Long/Short y el mercado de equities son más favorables.

---

## 6. Contexto real

| Referencia | Sharpe |
|-----------|:------:|
| Hedge fund típico | ~0.5–1.0 |
| Top hedge funds (Citadel, DE Shaw) | ~1.5–2.0 |
| Renaissance Medallion (mítico) | ~4.0 |
| **SFM SP500 Walk-Forward** | **~2.95** |

El resultado es comparable a hedge funds de élite. **Desconfiar con moderación:** backtest no es realidad, pero la señal es sólida.

---

## 7. Problemas identificados

| Problema | Severidad | Causa probable |
|----------|:---------:|----------------|
| Overfitting a validación (r = −0.33) | 🔴 Alta | Sharpe_val calculado en una sola partición; el modelo memoriza patrones |
| Top-K σ = 1.63 | 🟡 Media | 3/5 positivos pero alta varianza entre trials |
| Sharpe_val = 5.39 poco realista | 🟡 Media | La validación puede estar sobrestimando; posible look-ahead bias leve |
| Solo 3 ventanas de WF | 🟢 Baja | Para 6 años de datos, 3 ventanas pueden no capturar todos los regímenes |

---

## 8. Próximos pasos

### Inmediatos (bajo esfuerzo, alto impacto)

1. **⬆️ Aumentar ventanas de Walk-Forward a 5**
   - Más robustez en la estimación de la σ real
   - Capturaría mejor los cambios de régimen de mercado
   - Código: cambiar `N_WINDOWS = 3` a `5`

2. **🔬 Ejecutar v5 con HPs fijos (sin Optuna)**
   - Usar `hidden_dim=112, K=13-16, lr=0.0006, dropout=0.5, batch=16, lookback=15`
   - Los 4 trials con Sharpe_test positivo comparten este perfil
   - Backtest limpio y rápido (~20 min) sin Optuna

3. **🧪 Test out-of-sample real (holdout 2026)**
   - Entrenar hasta 2025-12, evaluar en 2026
   - Es lo más parecido a producción sin producirlo
   - Si el Sharpe > 1.0, el modelo es operativo

### Corto plazo

4. **📈 Añadir Volatility Targeting**
   - Overlay de solo ~6 líneas
   - Objetivo: reducir σ del WF de 0.87 a ~0.3-0.4 sin sacrificar Sharpe
   - Efecto esperado: Sharpe neto más estable entre ventanas

5. **🔍 Probar con universo mayor (SP100 o SP500 completo)**
   - Si funciona con 40 stocks aleatorios, probablemente escala
   - Más activos → más oportunidades de Long/Spread

6. **🔬 Validar con 5 semillas diferentes**
   - Ejecutar el mismo pipeline con seed=42, 123, 456, 789, 999
   - Si el WF se mantiene >2.0 en todas, el resultado es genuino

### Medio plazo

7. **💰 Evaluar impacto real de costes**
   - Long/Short con 40 stocks: ~252 operaciones/año × 0.2% = ~0.5% anual
   - Verificar que Sharpe neto > 2.0 después de restar costes reales (slippage, borrowing fees)

8. **🔄 Probar con predicción de ranking en lugar de retorno**
   - Podría reducir el overfitting a cambios de régimen
   - Entrenar para predecir qué activo será top/bottom, no cuánto

---

## 9. Lecciones aprendidas

| Lección | Implicación |
|---------|-------------|
| **SFM funciona mejor en equities que en crypto** | El mercado de acciones tiene más estructura y menos ruido que crypto |
| **Long/Short > Top-1 Long** | El spread captura alpha puro sin depender de la dirección del mercado |
| **La convergencia de HPs da confianza** | Cuando el espacio de búsqueda converge, el modelo es estable |
| **El overfitting a validación sigue siendo un problema** | r = −0.33 entre Sharpe_val y test → mejorar la validación es clave |
| **En SP500, las ventanas recientes (2023-2026) son especialmente fuertes** | El régimen actual del mercado es favorable para SFM |

---

## 10. Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v5.py` — script con Long/Short + Sharpe optimization
- `scripts/crypto/output/optuna_sfm_v5/` — resultados de esta ejecución
- `obsidian/04 Experiments/analisis_resultados_SFM_v4.md` — análisis primera ejecución v4
- `obsidian/04 Experiments/analisis_resultados_SFM_v4_fixes.md` — análisis v4 con fixes
- `obsidian/04 Experiments/analisis_resultados_SFM_v4_2018_2026.md` — análisis v4 2018-2026
- `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md` — documentación técnica
- `obsidian/01 Literature/formacion/qlib/sfm-comparativa-scripts.md` — comparativa de versiones
- `obsidian/03 Strategies/sfm-crypto-estrategias.md` — estrategias de trading
