# 🔀 Backtest Estrategia 2 (momentum + FILTRO PEAD) — Resultado OOS

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Script:** `momentum_pead_filter_backtest.py`
> **Datos:** `pead_earnings_appended.csv` (1,133 eventos, 283 tickers)

---

## Resultado (umbral filtro −5%)

| Métrica | Momentum puro (base) | Momentum + Filtro PEAD |
|---|---|---|
| Retorno anualizado | ~+18-21% | **+16.61%** |
| Sharpe | ~0.9-1.1 | **0.875** |
| Max drawdown | ~−19% | **−19.35%** |
| Valor final ($100k) | — | $197,182 |
| Puntos excluidos por filtro | 0 | 3,766 |

## Veredicto honesto

**El filtro PEAD NEGATIVO NO mejora el momentum puro en backtest:**

- **Sharpe 0.875 vs ~1.0** (peor)
- **Retorno +16.6% vs +18-21%** (algo menor)
- Posibles razones:
  1. **Limitación de datos:** los earnings solo cubren ~2 años (2025-26), el filtro casi no actúa en 2022-2024 → señal incompleta.
  2. **Posible desalineación look-ahead** en el `ffill` entre el anuncio y el rebalanceo.
  3. La muestra corta de earnings hace el resultado poco representativo.

## Conclusión (coherente con Quinn)

**Ni la suma (Sharpe 0.57) ni el filtro (Sharpe 0.87) superan al momentum puro (Sharpe ~1.0) en backtest.**

La evidencia de backtest NO respalda que el filtro PEAD añada valor. El único brazo que puede dar evidencia real es el **paper-trading en vivo de la estrategia 2** (que corre en paralelo), donde a corto plazo mostró −1.78% vs −2.45% del momentum puro — pero eso es ruido de 2 semanas según Quinn.

## El valor que SÍ tiene el PEAD

- Como **señal de ranking de eventos**: IC Spearman 0.19-0.22 (real, pero solo explotable en el momento del anuncio)
- Como **filtro**: sin edge claro en backtest con los datos actuales

## Próximos pasos (si se quisiera perseguir)

- Corregir la alineación point-in-time del filtro (garantizar que solo usa sorpresas `<= fecha`)
- Conseguir más histórico de earnings (varios años, no solo 2)
- Evaluar el filtro solo en el periodo donde hay datos (2025-26), no en todo el backtest

---

*Documento de referencia del proyecto Qlib Work.*
