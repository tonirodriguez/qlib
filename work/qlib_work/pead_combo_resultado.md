# 🔀 Backtest Combinado Momentum + PEAD — Resultado DEFINITIVO (datos completos)

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Datos:** `pead_earnings_data_full.csv` — **284 tickers, 1,137 eventos** (recuperación completa)

---

## Resultado (backtest con datos COMPLETOS de earnings)

| λ (peso PEAD) | Retorno anual | Sharpe | Max DD |
|---|---|---|---|
| 0.6 | +10.22% | 0.569 | −18.4% |
| 0.7 | +10.15% | 0.581 | −18.4% |
| 0.8 | +10.09% | 0.566 | −18.4% |
| **Solo momentum** | **+18-21%** | **~1.0** | ~−19% |

## Veredicto

**❌ La combinación PEAD + momentum (como señal de ranking combinada) es PEOR que el momentum solo.**

- Sharpe ~0.57 vs ~1.0
- Retorno ~+10% vs +18-21%

Incluso con los datos completos (284 tickers), la fusión de rankings **no mejora** — empeora.

## Por qué (interpretación honesta)

1. **El PEAD es una señal de EVENTO, no una serie continua.** Forzarlo con z-score + forward-fill entre trimestres lo convierte en una señal que se diluye y añade ruido al sumarla al momentum.
2. **La fuerza del PEAD está en el momento del anuncio** (IC 0.19 post-anuncio), no propagada en el tiempo.
3. Quinn lo advirtió: forzar la combinación de rankings no era el camino correcto para el PEAD.

## Conclusión según criterios de Quinn

La fusión solo si el combo supera al momentum en Sharpe sin empeorar DD:
- ❌ **NO cumple** → **NO fusionar PEAD como señal de ranking combinada**

## El uso correcto del PEAD (accionable)

El PEAD debe usarse como **REFUERZO/FILTRO del momentum**, no como señal que se suma:
- **Filtro negativo:** no comprar momentum con sorpresa fuertemente negativa (< −2σ o < −10%)
- Capturar la fuerza del PEAD en el momento del anuncio, no propagada

Este es el enfoque que la evidencia respalda.

---

*Documento de referencia del proyecto Qlib Work.*
