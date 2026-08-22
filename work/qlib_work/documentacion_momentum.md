# 📈 Estrategia Momentum 120 — Documentación y Workflow de Scripts

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Ubicación scripts:** `work/estrategias/`
> **Ubicación docs:** `work/qlib_work/`

---

## 1. Qué es la estrategia momentum 120

**Idea central:** comprar las **30 acciones del S&P 500 con mayor retorno acumulado en los últimos 120 días** (~6 meses), rebalanceando semanalmente.

**Base teórica:** Jegadeesh & Titman (1993) — *underreaction* (los precios tardan en incorporar las noticias) y sesgos de comportamiento.

### Fórmula de la señal
```
momentum_120d = (precio_hoy / precio_hace_120_días) − 1
```

### Rendimiento validado (backtest OOS)
| Métrica | Valor |
|---|---|
| IC out-of-sample | **+0.066** |
| Retorno anualizado | ~+18-21% |
| Sharpe | ~0.9-1.1 |
| Max drawdown | ~−19% |
| Con vol-targeting | ~+21-24%, Sharpe >1 |

---

## 2. Workflow de scripts (Momentum 120)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. VALIDACIÓN — Walk-forward del momentum                         │
│    momentum_walkforward.py [universo] [label_días]               │
│    │  (IC del momentum a 20/60/120/250d vs retorno futuro)       │
│    ▼                                                             │
│    Resultado: IC OOS 120d = +0.066 (label 120d óptimo)          │
│                                                                  │
│ 2. BACKTEST BASE                                                 │
│    momentum_backtest.py [universo] [topk] [mom_window]           │
│    │  (TopkDropout + costes IB + rebalanceo semanal)            │
│    ▼                                                             │
│    Resultado: +18.5% anual, Sharpe 0.96, DD −19%                │
│                                                                  │
│ 3. VOL-TARGETING (gestión de riesgo)                             │
│    momentum_vt_backtest.py [univ] [topk] [mom_window] [vol_targ] │
│    │  (reduce exposición si sube volatilidad)                   │
│    ▼                                                             │
│    Resultado: +21.7%, Sharpe 1.07, DD −18.6%                    │
│                                                                  │
│ 4. PAPER-TRADING (DINERO FICTICIO) EN VIVO                       │
│    actualizar datos (sáb 00:00): update_data_light.py            │
│    │  → prices_live.csv (precios frescos Yahoo sp500_liquid)     │
│    ▼                                                             │
│    simular (sáb 15:00): simulation/simulate.py [--reset]         │
│    │  (topk 30, costes IB tiered, compara fracional vs entera)   │
│    ▼                                                             │
│    state.json (memoria entre ejecuciones) + reporte por Telegram │
│                                                                  │
│ 5. NOTEBOOK EXPLORATIVO                                          │
│    momentum_120d.ipynb  (todo el flujo, ejecutable)              │
└──────────────────────────────────────────────────────────────────┘
```

### Scripts y su propósito

| Script | Propósito |
|---|---|
| `momentum_walkforward.py` | Validar IC OOS del momentum en varias ventanas y horizontes |
| `momentum_backtest.py` | Backtest base (TopkDropout + costes IB) |
| `momentum_vt_backtest.py` | Backtest con vol-targeting (gestión de riesgo) |
| `simulation/update_data_light.py` | Bajar precios frescos de sp500_liquid (Yahoo, canal paralelo) |
| `simulation/simulate.py` | Paper-trading: rebalanceo semanal, costes IB, comparativa |
| `simulation/state.json` | Memoria persistente del paper-trading |
| `momentum_120d.ipynb` | Notebook completo y ejecutable |

### Estrategia de riesgo (vol-targeting)
```
risk_degree = vol_objetivo / vol_actual   (recortado a [30%, 100%])
```
Reduce exposición cuando sube la volatilidad del mercado → evita momentum-crash.

---

## 3. Documentación asociada

| Documento | Contenido |
|---|---|
| `Estrategia_Momentum_120.md` | Guía completa (IC, vol-targeting, rebalanceo, costes) |
| `momentum_largo_alpha.md` | Hallazgo del alpha del momentum 120d |
| `backtest_momentum.md` | Resultados del backtest |
| `walk_forward_diagnostico.md` | Diagnóstico OOS del momentum |
| `money_paper_*.md` | Registros semanales del paper-trading |
| `rebalanceo_*.md` | Detalle de los rebalanceos |

---

## 4. Estado actual

- ✅ Backtest validado (IC OOS 0.066, +18-21%, Sharpe ~1)
- ✅ Vol-targeting integrado (+21.7%, Sharpe 1.07)
- ✅ **Paper-trading en vivo** con €20,000 ficticios (desde 14-ago)
- 📊 Estado paper-trading: **−2.45%** (22-ago) — corrección de mercado, dentro de lo esperado
- 🔄 Rebalanceo automático cada sábado (cronjobs)

---

## 5. Cronjobs asociados

| Cronjob | Día/Hora | Acción |
|---|---|---|
| Actualizar datos Qlib US | Sáb 00:00 | `update_data_light.py` → datos frescos |
| Simulación momentum | Sáb 15:00 | `simulate.py` → rebalanceo + informe |

---

*Documento de referencia del proyecto Qlib Work.*
