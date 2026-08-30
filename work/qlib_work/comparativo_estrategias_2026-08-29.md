# 📊 Comparativo de Estrategias — 2026-08-29

> **Proyecto:** Qlib Work
> **Fecha:** 2026-08-29
> **Propósito:** Comparar lado a lado las 3 estrategias de paper-trading en paralelo (Semana 7 del plan de Quinn — medición pasiva).
> **Datos:** estados de las simulaciones del sábado 29-ago (fecha de datos 28-ago).

---

## 📈 Estado de las 3 estrategias (29-ago-2026)

| Estrategia | Script | Estado | Start (USD) | Valor (USD) | Valor (EUR) | P&L | Posiciones |
|---|---|---|---|---|---|---|---|
| **E1** — Momentum 120 puro | `simulate.py` | `state.json` | $22,600 | $22,114.66 | €19,570.50 | **−2.15%** | 30 |
| **E2** — Momentum + filtro PEAD | `simulate_pead.py` | `state_pead.json` | $22,600 | $22,256.22 | €19,695.77 | **−1.52%** | 30 |
| **E3** — PEAD-núcleo + momentum-táctico | `simulate_pead_core.py` | `state_pead_core.json` | $22,035 | $21,912.61 | €19,391.69 | **−0.56%** | 34 (22+12) |

*Nota: E1/E2 arrancaron con €20k; E3 con ~€19.5k (equivalente al valor actual para comparar justo). Gate E3 = 1.0 (vol normal, momentum-táctico a pleno).*

---

## 📈 Evolución desde el comparativo anterior (22-ago → 29-ago)

| Estrategia | P&L 22-ago | P&L 29-ago | Variación semanal |
|---|---|---|---|
| **E1** momentum puro | −2.45% | −2.15% | 🟢 **+0.30 p.p.** (mejora) |
| **E2** momentum + filtro PEAD | −1.83% | −1.52% | 🟢 **+0.31 p.p.** (mejora) |
| **E3** PEAD-núcleo + táctico | −0.05% | −0.56% | 🔴 **−0.51 p.p.** (corrige, entra el rebalanceo real) |

---

## 🔍 Lectura honesta

1. **E3 ya no está plana.** El −0.05% anterior era solo el coste de entrada (acababa de nacer el 22-ago). Con el primer rebalanceo real en marcha, hoy registra **−0.56%**. Es la nueva arquitectura, y su PEAD-núcleo está desplegando sus 22 posiciones + 12 de momentum-táctico.

2. **E1 sigue siendo la peor (−2.15%)** y **E2 mejora (−1.52%)**: coherente con el filtro PEAD negativo que protege del momentum débil de este tramo (hallazgo del purged CV: momentum flojo en este período).

3. **La mejora semanal de E1 y E2 (+0.3 p.p.) contrasta con la corrección de E3** — pero es **ruido de 1-2 semanas**, no señal. Las tres corren el mismo mercado; las diferencias de 1 semana con carteras de 30-34 nombres no son concluyentes.

---

## ⚠️ Importante (no sobreinterpretar)

**La S7 es medición pasiva.** Según Quinn, hacen falta **≥24-50 rebalanceos (6-12 meses)** para decidir si una arquitectura supera a otra. Una semana no decide nada.

**Lo que este comparativo SÍ valida hoy:**
- ✅ Las 3 estrategias corren en paralelo correctamente (cronjobs del sábado: 15:00 E1, 16:00 E2, 17:00 E3).
- ✅ E3 despliega sus dos libros con el vol-gate activo (gate=1.0, mercados en vol normal).
- ✅ El filtro PEAD de E2 sigue protegiendo (E2 > E1 consistentemente).

**Lo que NO hay que concluir todavía:**
- ❌ No decidir entre arquitecturas con 1-2 semanas de data.
- ❌ No "ajustar" E3 por su −0.56% inicial (es ruido de rebalanceo).

---

## ⏏️ Regla de mantenimiento (plan Quinn §4)

- E1 y E2 se mantienen como **monitor** (control), no se reasignan.
- E3 es **la apuesta** (nueva arquitectura).
- La decisión real (S8) vendrá tras varias semanas más de evidencia.

*Este comparativo se regenerará semanalmente con los P&L de las 3 estrategias.*

---

*Documento de referencia del proyecto Qlib Work. Alineado con `plan_E3_quinn_futuro.md`.*