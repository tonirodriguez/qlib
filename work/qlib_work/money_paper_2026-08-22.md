# 💵 Paper-Trading — Estado Semanal (2026-08-22)

> **Proyecto:** Qlib Work — simulación estrategia momentum 120d con dinero ficticio
> **Capital ficticio:** €20,000 · **Operativa:** topk 30 · **Fecha de datos:** 2026-08-21
> **Fuente:** `work/estrategias/simulation/simulate.py` + `state.json`

---

## 📊 Estado general

| Concepto | Valor |
|---|---|
| Capital inicial | €20,000 ($22,600) |
| Valor cartera actual | $22,046 = €19,509 |
| **P&L ficticio** | **−$554 = −€491 (−2.45%)** |
| Posiciones | 30 |
| Rebalanceo | 22-ago (datos 21-ago) |
| Coste IB del rebalanceo | $11.27 |
| Mejor momentum | MU (Micron) +134.3% |

---

## 📈 Evolución desde el inicio

| Fecha | Valor | P&L |
|---|---|---|
| Inicio (14-ago) | $22,600 | €0 (0%) |
| 15-ago | $22,454 | −0.70% |
| **22-ago (hoy)** | **$22,046** | **−2.45%** |

---

## 🔍 Lectura honesta

**La estrategia ha caído −2.45% desde el inicio** (esta semana −1.75% aprox).

### ¿Por qué?
1. **El mercado tech corrigió** — coincide con la cartera real (MSFT, META bajando). El momentum compra high-beta, que cae más en correcciones.
2. **El top 30 rotó** — ahora el líder es MU (Micron) +134% (antes INTC). Rotación normal del momentum.
3. **Costes IB aplicados** ($11.27/semana) — desgaste real.

### ¿Es preocupante?
- **No.** El momentum 120d es de **medio plazo** (señal de 6 meses).
- Drawdown máximo validado en backtest: **−19%** → estamos a −2.45%, muy lejos.
- Las primeras semanas de momentum suelen fluctuar con el mercado.

### Señal de alarma (si ocurre)
- Caída **sostenida acelerada** acercándose a −10%+ en pocas semanas
- Drawdown que supera lo esperado del backtest (<−19%)

---

## 📋 Top posiciones actuales (fraccionales)

Se rebalanceó hoy al nuevo top 30 por momentum. Líder: MU (Micron) +134.3%.

*(Ver la tabla completa fraccional vs entera en la salida del script `simulate.py`.)*

---

*Registro semanal del paper-trading momentum 120d. Generado el 2026-08-22.*
