# 📊 Comparativo de Estrategias — 2026-08-22

> **Proyecto:** Qlib Work
> **Fecha:** 2026-08-22
> **Propósito:** Comparar lado a lado las 3 estrategias de paper-trading en paralelo, tras implementar la E3 (PEAD-núcleo + momentum-táctico) según el plan de Quinn.

---

## 📈 Estado de las 3 estrategias (22-ago-2026)

| Estrategia | Script | Estado | Start (USD) | Valor (USD) | P&L | Posiciones |
|---|---|---|---|---|---|---|
| **E1** — Momentum 120 puro | `simulate.py` | `state.json` | $22,600 | $22,046 | **−2.45%** | 30 |
| **E2** — Momentum + filtro PEAD | `simulate_pead.py` | `state_pead.json` | $22,600 | $22,187 | **−1.83%** | 30 |
| **E3** — PEAD-núcleo + momentum-táctico | `simulate_pead_core.py` | `state_pead_core.json` | $22,035 | $22,023 | **−0.05%** | 34 (22+12) |

*Nota: E1/E2 arrancaron con €20k; E3 con €19.5k (equivalente al valor actual, para comparar justo).*

---

## 🔍 Lectura inicial (honesta)

1. **E1 (momentum puro) es la que peor va: −2.45%.** Coherente con el hallazgo del purged CV: el momentum está en un tramo flojo (agosto 2026).

2. **E2 (momentum + filtro PEAD) algo mejor: −1.83%.** El filtro negativo protege un poco.

3. **E3 (PEAD-núcleo + momentum-táctico) apenas varió: −0.05%.** Acaba de arrancar hoy (solo costes de entrada). Es LA nueva arquitectura: PEAD como núcleo.

---

## ⚠️ Importante (no sobreinterpretar)

**E3 acaba de nacer hoy (22-ago).** Su −0.05% es solo el coste de entrada, no un resultado real. **Las comparaciones significativas requieren semanas** (según Quinn, ≥24-50 rebalanceos para decidir). Este documento es el **punto de partida** de la medición en paralelo.

**Lo que este comparativo SI muestra ya:**
- La arquitectura E3 funciona y despliega correctamente sus dos libros (22 PEAD + 12 momentum)
- Las 3 corren en paralelo con cronjobs independientes (E1 🤸 15:00, E2 🕓 16:00, E3 🕔 17:00)

---

## ⏏️ Regla de mantenimiento (según plan Quinn §4)

- E1 y E2 se mantienen como **monitor** (control), no se reasignan
- E3 es **la apuesta** (nueva arquitectura)
- Documento vivo: se actualizará cada semana con los P&L de las 3

*Este comparativo se regenerará semanalmente con los P&L de las 3 estrategias.*

---

*Documento de referencia del proyecto Qlib Work. Alineado con `plan_E3_quinn_futuro.md`.*
