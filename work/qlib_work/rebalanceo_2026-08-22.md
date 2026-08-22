# 🔄 Rebalanceo Paper-Trading — 22-ago-2026

> **Proyecto:** Qlib Work — estrategia momentum 120d
> **Comparativa:** cartera 15-ago-2026 → cartera 22-ago-2026
> **Fuente:** `state.json` (versión previa desde git `17ec361f` vs actual)

---

## 📊 Resumen del rebalanceo

| Concepto | Valor |
|---|---|
| Fecha del rebalanceo | 22-ago-2026 |
| Datos usados | 2026-08-21 |
| Valor anterior | $22,057 |
| Coste IB | $11.27 (30 órdenes mín. tiered) |
| Valor tras costes | $22,046 |
| Posiciones anteriores | 30 |
| Posiciones nuevas | 30 (23 mantenidas + 7 nuevas) |

**Mejor momentum del nuevo top 30:** MU (Micron) +134.3%

---

## ❌ VENDIDO (7 posiciones que salieron del topk)

| Ticker | Empresa |
|---|---|
| MSFT | Microsoft |
| BKNG | Booking Holdings |
| NTAP | NetApp |
| KLAC | KLA Corporation |
| VRSN | VeriSign |
| AIZ | Assurant |
| IVZ | Invesco |

---

## ✅ COMPRADO (7 posiciones nuevas que entraron al topk)

| Ticker | Empresa | Sector |
|---|---|---|
| ELV | Elevance Health | Salud |
| EXPD | Expeditors Intl | Industria/logística |
| RVTY | Revvity | Salud/instrumentos |
| WAT | Waters Corp | Salud/instrumentos |
| BAX | Baxter Intl | Salud |
| BEN | Franklin Resources | Financiero |
| A | Agilent | Salud/instrumentos |

---

## 🔁 MANTENIDO (23 posiciones siguen en ambas)

ADP · AMAT · APA · BBY · BNY · CSCO · EXPE · GEN · HPQ · HUM · INTC · MET · MS · MU · NTRS · NUE · PAYX · STT · TGT · UNH · USL · VLO · WDC

---

## 📌 Observaciones

1. **Se vendió MSFT** — salió del top 30 por momentum (decisión de la estrategia, no de la cartera real).

2. **Rotación sectorial:** entran 5 posiciones de **salud** (ELV, RVTY, WAT, BAX, A) + industria (EXPD). El momentum rota de tech hacia **defensivos/no-tech** — coherente con la corrección del sector tech.

3. **Método del script:** el rebalanceo vende las posiciones que salen del topk y compra las nuevas con asignación igualitaria. El log marca "ventas 30 / compras 0" como detalle contable interno, pero en la práctica **se venden las 7 que salieron y se compran las 7 nuevas**.

---

*Registro del rebalanceo semanal del paper-trading momentum 120d. Generado el 22-ago-2026.*
