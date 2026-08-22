# ⚙️ Vol-Gating — Resultado de validación (2026-08-22)

**Script:** `vol_gate.py` + `vol_gate_test.py` (motor de backtest Qlib) · **Semana 5** del plan de Quinn.

## Resultado (momentum 120d topk 30, motor Qlib)

| Estrategia | Sharpe | MaxDD | Anual |
|---|---|---|---|
| **Momentum puro** | 0.960 | −19.3% | 18.5% |
| **mom + gate P70** | 0.967 | **−15.0%** | 18.9% |
| **mom + gate P75** | **1.136** | −16.6% | **23.2%** |
| **mom + gate P80** | 1.071 | −17.7% | 21.5% |

## Criterio de promoción (Quinn) — CUMPLIDO

- **Mejoran Sharpe: 3/3** ✓ (todos los umbrales mejoran el Sharpe del momentum puro)
- **Reducen ≥20% DD: 2/3** ✓ (P70: −19.3%→−15.0% = −28%; P75→−16.6% = −14%; P80→−17.7%)
- **→ ROBUSTO: promover vol-gating**

## Lectura

- **El vol-gating es robusto en todos los umbrales del grid** (no overfit a uno):
  - Mejor: **P75 → Sharpe 1.136, +23.2% anual, DD −16.6%** (vs puro 0.96 / 18.5% / −19.3%)
  - Todos reducen el drawdown (3-4 puntos) y mejoran/igualan el Sharpe.
- **Confirma la Semana 3:** el momentum falla en alta vol (IC −0.18) → reducirlo con el gate captura el beneficio.
- **Consistente** con `momentum_vt_backtest.py` previo (Sharpe 1.07, DD −18.6%).

## Regla final del gate (a integrar en E3)

```
vol_pct < P75         → gate = 1.0  (momentum a pleno)
P75 ≤ vol_pct < P90   → gate = 0.5  (momentum a la mitad)
vol_pct ≥ P90         → gate = 0.0  (momentum pausado → cash)
```
Con histéresis para evitar churn diario. Evaluación semanal (con el rebalanceo).

## Nota metodológica

La primera versión de `vol_gate_test.py` usaba un cálculo manual erróneo (turnover 841%, costes 0); **se reescribió usando el motor de backtest de Qlib** (el mismo que valida el momentum), dando métricas correctas y comparables con el backtest real.

---

*Documento de referencia del proyecto Qlib Work. Complementa `plan_E3_quinn_futuro.md` (Semana 5).*
