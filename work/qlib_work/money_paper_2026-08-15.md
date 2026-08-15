# 💵 Paper-Trading — Estado Semanal (2026-08-15)

> **Proyecto:** Qlib Work — simulación de la estrategia momentum 120d con dinero ficticio
> **Capital ficticio:** €20,000 · **Operativa:** topk 30 · **Fecha de datos:** 2026-08-14
> **Fuente:** `work/estrategias/simulation/simulate.py` + `state.json`

---

## 📊 Estado general

| Concepto | Valor |
|---|---|
| Capital inicial | €20,000 ($22,600) |
| Valor cartera actual | $22,454 = €19,871 |
| **P&L ficticio** | **−$146 = −€129 (−0.65%)** |
| Posiciones | 30 |
| Último coste rebalanceo | $11.28 |

---

## 📋 Acciones a comprar esta semana (datos 14-ago-2026)

**Top 30 por momentum 120d** — mayor momentum: **INTC (+134.9%)**

| # | Ticker | Fracc. | Entero | Precio |
|---|---|---|---|---|
| 1 | INTC | 7.30 | 7 | $102.50 |
| 2 | MU | 0.77 | 1 | $971.66 |
| 3 | HUM | 1.92 | 2 | $389.05 |
| 4 | NTAP | 3.61 | 4 | $207.08 |
| 5 | WDC | 1.47 | 1 | $508.80 |
| 6 | EXPE | 2.25 | 2 | $332.69 |
| 7 | VLO | 2.19 | 2 | $341.67 |
| 8 | HPQ | 24.86 | 25 | $30.11 |
| 9 | STT | 3.90 | 4 | $191.74 |
| 10 | NUE | 2.78 | 3 | $268.91 |
| 11 | CSCO | 6.70 | 7 | $111.68 |
| 12 | UNH | 1.86 | 2 | $401.73 |
| 13 | BNY | 4.59 | 5 | $163.24 |
| 14 | APA | 18.49 | 18 | $40.47 |
| 15 | PAYX | 6.13 | 6 | $122.02 |
| 16 | BBY | 8.66 | 9 | $86.42 |
| 17 | BKNG | 3.53 | 4 | $212.06 |
| 18 | KLAC | 3.67 | 4 | $203.72 |
| 19 | NTRS | 3.91 | 4 | $191.41 |
| 20 | TGT | 4.85 | 5 | $154.48 |
| 21 | AMAT | 1.48 | 1 | $507.18 |
| 22 | VRSN | 2.63 | 3 | $284.24 |
| 23 | USL | 14.75 | 15 | $50.75 |
| 24 | ADP | 2.74 | 3 | $272.96 |
| 25 | GEN | 26.28 | 26 | $28.48 |
| 26 | MS | 3.44 | 3 | $217.36 |
| 27 | MET | 7.66 | 8 | $97.66 |
| 28 | AIZ | 2.65 | 3 | $282.38 |
| 29 | IVZ | 22.99 | 23 | $32.55 |
| 30 | MSFT | 1.51 | 2 | $495.40 |

---

## 💰 Saldos y costes

### Opción FRACCIONARIA
| Concepto | Valor |
|---|---|
| Saldo antes de compra | $22,465 |
| Acciones a comprar | 199.61 |
| Coste IB (30 órdenes) | $10.50 |
| Total compra | $22,464.18 |
| **Saldo después** | **$22,454** |

### Opción ENTERA
| Concepto | Valor |
|---|---|
| Saldo antes de compra | $22,465 |
| Acciones a comprar | 202 |
| Coste IB (30 órdenes) | $10.50 |
| Total compra | $23,031.39 |
| **Diferencia vs fracc.** | **+$567 más de inversión** |

### 💡 Lectura de costes
- **Coste IB idéntico en ambas ($10.50)** — el mínimo por orden de $0.35 domina en posiciones pequeñas (30 × $0.35 = $10.50)
- **La diferencia real** es el capital: fraccionaria $22,464 vs entera $23,031 (+$567)
- Con acciones fraccionarias de IB se replica la cartera casi exacta

---

## ⚠️ Notas
- Base de costes IB tiered: comisión `max($0.35, $0.0035/acción)`, más SEC/TAF solo en ventas
- **MSFT está en la lista** (1.51 → 2 enteras) — la estrategia sugiere entrada, y ya es parte de la cartera real
- Es **dinero ficticio** de simulación, no recomendación de inversión personalizada

---

*Registro semanal del paper-trading momentum 120d. Generado el 2026-08-15.*
