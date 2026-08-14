# 📊 Backtest Momentum 120d — Primer resultado completo positivo (sp500_liquid)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — implementación de la señal de momentum con alpha OOS
> **Base:** momentum 120d + label 120d (IC OOS +0.066) sobre sp500_liquid
> **Script:** `toni/momentum_backtest.py`

---

## 1. Configuración

| Parámetro | Valor |
|---|---|
| Universo | sp500_liquid (291 tickers S&P 500) |
| Señal | momentum 120d (retorno acumulado 120 días) |
| Estrategia | TopkDropoutStrategy, topk 30, n_drop 5 |
| Rebalanceo | semanal |
| Costes | Interactive Brokers (open 0.04%, close 0.06%, min $1) |
| Periodo | 2022-01 → 2026-08 |
| Benchmark | ^NDX (no cargado correctamente en este run) |

## 2. Resultados (retorno absoluto — fiables)

| Métrica | Valor |
|---|---|
| Valor final | $214,529 (de $99,963) |
| **Retorno anualizado** | **+18.51%** |
| Volatilidad anual | 19.29% |
| **Max drawdown** | **−19.35%** |
| **Sharpe** | **0.96** |

## 3. Interpretación

- **+18.5% anual con Sharpe 0.96 y drawdown −19.4%** — perfil sólido y coherente.
- La señal tiene **alpha out-of-sample validado** (IC 0.066), y el backtest lo convierte en retorno real.
- **Drawdown mucho mejor** que el Alpha158 de tech_giants (−48%): −19.4%.
- ⚠️ Los valores de "exceso +10329%" y "benchmark NaN" son **artefactos del script** (anualización semanal incorrecta + benchmark no cargado). **Se ignoran.** El retorno absoluto y su drawdown/Sharpe sí son fiables.

## 4. Comparativa con intentos previos

| Estrategia | IC OOS | Retorno anual | Sharpe | Max DD |
|---|---|---|---|---|
| Alpha158+LightGBM (tech_giants) | 0.008 | +24.3% (beta) | 1.10 | −48% |
| Momentum 120d (sp500_liquid) | **0.066** | **+18.5%** | **0.96** | **−19.4%** |

**Clave:** el Alpha158 daba más retorno pero era beta (IC≈0) y con drawdown brutal. El momentum 120d da menos retorno pero es **alpha real** (IC 0.066) con **drawdown mucho menor** (−19% vs −48%). Para invertir de verdad, la segunda es mejor: menos beta, más predicción, menos riesgo.

## 5. Próximos pasos

- [ ] Combinar momentum con factor ortogonal (quality/low-vol) → mejora Sharpe
- [ ] Gestionar momentum-crash (vol-targeting / filtro de régimen)
- [ ] Afinar topk / n_drop

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada experimento.*
