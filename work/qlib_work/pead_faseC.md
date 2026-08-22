# 🔀 PEAD — Fase C: Combinación momentum + PEAD

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work

## Resultado

| Señal | IC total | IC medio anual |
|---|---|---|
| Momentum solo | −0.005 | −0.004 |
| PEAD solo | −0.002 | +0.001 |
| **Combo** (z-mom + z-pead) | **+0.008** | **+0.023** |

## Interpretación honesta

**El combo supera a cada señal sola** (consistente con la teoría de factores ortogonales), **pero con limitaciones técnicas que impiden concluir:**

1. **El PEAD solo tiene datos en los últimos 2 años** (el IC anual es NaN en 7 de 9 años) → la comparación no es un walk-forward limpio.
2. **Emomentum a 20 días es ~0** (ya sabíamos: funciona a 120 días, no 20). Aquí se midió a 20d.
3. **El forward-fill del PEAD entre trimestres suaviza la señal** — el PEAD es una señal de *evento* (cambia alrededor del anuncio), no una serie continua.

## Punto clave

La **Fase A2 ya demostró** que la sorpresa de earnings predice el retorno post-anuncio (IC 0.19, long-short +5-7% a 20d). Ese es el enfoque fiel (medir el efecto en el momento del anuncio).

## Próximos pasos (vías honestas)

1. **Integrar el PEAD como factor de evento** en un DataHandler de Qlib (capturar la sorpresa alrededor del anuncio), combinar "de verdad".
2. **O tratar el PEAD como señal independiente** (estrategia de eventos) en lugar de forzar la combinación.

*Script: `work/estrategias/pead_combo.py`*
