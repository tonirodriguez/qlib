---
tags: [strategy, crypto, sfm, v4, proposal]
status: draft
date: 2026-06-03
---

# Estrategias de trading para SFM en crypto

> Estrategias alternativas a Top-1 Long para el pipeline SFM v4.
> El modelo predice retornos multi-activo diarios (BTC, ETH, SOL, XLM, ADA).
> Objetivo: mejorar Sharpe, reducir varianza, ser robusto a cambios de régimen.

---

## 1. Long/Short entre pares 🥇

**Descripción:** Compras el activo con mejor predicción y vendes en corto el que peor predicción tiene. Capturas el spread independientemente de la dirección del mercado.

```python
idx_max = np.argmax(preds[t])
idx_min = np.argmin(preds[t])
ret = real[t, idx_max] - real[t, idx_min]  # spread
# costes: 0.001 (long) + 0.001 (short) = 0.002
```

**Ventajas:**
- Elimina la dirección del mercado — ganas cuando aciertas el ranking aunque todo caiga
- Sharpe más estable entre regímenes
- Ya implementado en la v5 (SP500) — portar es trivial

**Riesgos:**
- Crypto es cara para hacer shorts (funding rates)
- Con solo 5 activos el spread puede ser pequeño
- ADA/XLM tienen poca liquidez para shorts reales (en backtest es asumible, en real dependería del exchange)

**Líneas de código:** ~5 (portar de v5, ajustar costes)

---

## 2. Top-K Equal Weight + Cash filter 🥈

**Descripción:** En lugar de apostar todo al #1, repartes equitativamente entre los K mejores que tengan predicción positiva.

```python
K = 3
top_k_idx = np.argsort(preds[t])[::-1][:K]
pos_mask = preds[t][top_k_idx] > 0
valid = top_k_idx[pos_mask]
ret = np.mean([real[t, i] for i in valid]) if len(valid) > 0 else 0.0
```

**Ventajas:**
- Diversificación — reduce el riesgo de apostar a un solo activo
- Menos varianza y drawdown que Top-1
- Sigue siendo simple e interpretable

**Riesgos:**
- Si el modelo es muy bueno seleccionando al #1, diluyes su señal con #2, #3...
- El K óptimo es un hiperparámetro más a optimizar

**Líneas de código:** ~8

---

## 3. Signal-weighted (asignación por magnitud) 🥉

**Descripción:** Asignas peso a cada activo proporcional al valor de su predicción (solo positivas). Aprovecha toda la información continua del modelo.

```python
preds_t = preds[t]
weights = np.maximum(preds_t, 0)      # cero para predicciones negativas
weights /= (weights.sum() + 1e-10)     # normalizar a suma=1
ret = np.dot(real[t], weights)         # portfolio weighted
```

**Ventajas:**
- Aprovechas toda la información del modelo, no solo el ranking
- Asignación continua (si BTC predice +3% y ETH +0.5%, pones 6x más en BTC)
- Matemáticamente óptimo si las predicciones son retornos esperados insesgados

**Riesgos:**
- Penaliza si el modelo está mal calibrado en magnitudes (predice +5% cuando es +1%)
- Puede concentrar demasiado en un activo si la predicción es muy extrema

**Líneas de código:** ~8

---

## 4. Volatility Targeting (gestión de riesgo) 🏅

**Descripción:** Overlay que escala el tamaño de la posición en función de la volatilidad realizada reciente. Objetivo: mantener volatilidad anualizada constante.

```python
vol_target = 0.15  # 15% volatilidad anual objetivo
vol_realizada = np.std(retornos_ultimos_21d) * np.sqrt(252)
factor_escala = vol_target / (vol_realizada + 1e-10)
factor_escala = np.clip(factor_escala, 0.0, 2.0)  # límite 2x
```

**Ventajas:**
- **Estabiliza el Sharpe de forma masiva** — la técnica más usada por hedge funds
- Reduce automáticamente exposición cuando el mercado está volátil (crypto alcanza 100%+ vol anualizada)
- Suaviza la curva de equity y reduce drawdown
- Funciona como overlay sobre cualquier estrategia de las anteriores

**Riesgos:**
- Añade un hiperparámetro: vol_target
- Forward-looking: asume que la volatilidad reciente es predictiva de la futura (cierto en finanzas, pero no perfecto)

**Líneas de código:** ~6 (overlay independiente)

---

## 5. Threshold adaptativo

**Descripción:** No operas si la mejor predicción no supera un umbral mínimo (e.g. 0.3%). Evita días de ruido donde la señal es marginal.

```python
if np.max(preds[t]) < 0.003:  # 0.3% mínimo
    ret = 0.0  # cash
```

**Ventajas:**
- Elimina señales marginales que suelen ser ruido
- Reduce número de operaciones y costes de transacción
- Complementa perfectamente cualquiera de las estrategias anteriores

**Riesgos:**
- El umbral es un hiperparámetro más (puede optimizarse con Optuna)
- Umbral muy alto → pierdes días buenos con señal débil

**Líneas de código:** ~3

---

## Tabla comparativa

| Estrategia | Sharpe esperado vs Top-1 | Líneas | Overlay adicional | Riesgo principal |
|-----------|------------------------|--------|------------------|-----------------|
| **Signal-weighted + cash** | +0.2 a +0.5 | ~8 | — | Mala calibración de magnitudes |
| **Long/Short** | +0.5 potencial | ~5 | — | Costes de short en crypto |
| **Top-K Equal Weight** | +0.1 a +0.3 | ~8 | — | Dilución si modelo es preciso |
| **VolTarget** | +0.3 a +0.6 | ~6 | **Sobre cualquiera** | Forward-looking bias |
| **Threshold** | +0.1 a +0.3 | ~3 | **Sobre cualquiera** | Umbral mal calibrado |

---

## Recomendación de implementación

La mejor combinación es combinar varias en capas:

```
Estrategia base → Signal-weighted + cash filter + threshold 0.3%
  └── Overlay → Volatility Targeting (15% target)
```

**Orden sugerido:**
1. **Signal-weighted + cash filter** — impacto alto, código mínimo, no añade hiperparámetros
2. **Threshold adaptativo** — 3 líneas, mejora casi segura
3. **Volatility Targeting** — el que más impacto tiene en estabilidad de Sharpe
4. **Long/Short** — portar de v5, probar si compensan los costes en crypto
5. **Top-K Equal Weight** — solo si los anteriores no funcionan

---

## Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v4.py` — script base con Top-1 Long + cash filter
- `scripts/crypto/qlib_sfm_pipeline.v5.py` — tiene Long/Short implementado
- `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md` — documentación técnica
- `obsidian/04 Experiments/analisis_resultados_SFM_v4_2018_2026.md` — últimos resultados
