# ⚡ Estrategia PEAD (Earnings Momentum) — Documentación y Workflow de Scripts

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Ubicación scripts:** `work/estrategias/`
> **Ubicación docs:** `work/qlib_work/`

---

## 1. Qué es el PEAD

**PEAD = Post-Earnings Announcement Drift** (deriva post-anuncio de resultados).

> Cuando una empresa anuncia resultados **sorprendentemente** buenos/malos, el precio **sigue derivando** en esa dirección durante semanas/meses después del anuncio.

**Evidencia:** Bernard & Thomas (1989); Chan, Jegadeesh & Lakonishok (1996).

### La medida clave: SUE (Standardized Unexpected Earnings)
```
SUE = (EPS_real − EPS_consenso) / desviación histórica del error
```
En nuestro proyecto usamos el **`surprise_pct`** (sencillo): `(EPS_real / EPS_estimado − 1) × 100`.

---

## 2. Hallazgos validados

| Hallazgo | Resultado |
|---|---|
| La sorpresa de earnings predice el retorno post-anuncio | **IC Spearman 0.19-0.22** |
| Long-short (alto − bajo surprise) a 20d | **+5.29%** |
| Long-short a 60d | **+7.29%** |
| Como estrategia pura binaria (comprar sorpresa >5%) | Marginal: +1%/evento, 49% acierto |

**Conclusión:** el PEAD es una **señal de ranking fuerte** pero **no funciona como estrategia autónoma binaria**. Su mejor uso es como **refuerzo/filtro** del momentum (según Quinn).

---

## 3. Workflow de scripts (PEAD)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. OBTENCIÓN DE DATOS — APPEND-ONLY (point-in-time safe) ✓                    │
│    pead_fetch_append.py  →  yahooquery.Ticker(t).earnings                     │
│    │  (291 tickers, reintentos DNS; LEE historial, AÑADE SOLO filas nuevas)   │
│    ▼                                                                         │
│    pead_earnings_appended.csv  (historial append-only: ticker, quarter,      │
│    actual, estimate, surprise_pct, reported_ts)                              │
│    (fuente semilla: pead_earnings_data_full.csv original)                    │
│                                                                              │
│ 2. FASE A — Distribución de sorpresas                                        │
│    pead_faseA.py  →  analiza surprise% por trimestre                        │
│    │                                                                         │
│    ▼                                                                         │
│    pead_earnings_data.csv                                                    │
│                                                                              │
│ 3. FASE A2 — IC del retorno post-anuncio                                     │
│    pead_faseA2.py [FWD]  →  correlación(sorpresa, retorno*)                 │
│    │  (*retorno FWD días tras el anuncio, desde Qlib precios)                │
│    ▼                                                                         │
│    pead_returns_20d.csv / pead_returns_60d.csv                               │
│                                                                              │
│ 4. FASE C — Combinación con momentum                                         │
│    pead_combo.py  →  IC de mom_z + λ·pead_z                                  │
│                                                                              │
│ 5. ESTRATEGIA DE EVENTOS                                                     │
│    pead_eventos.py [FWD] [delay] [umbral]                                    │
│    │  (compra si surprise>umbral, mide retorno del evento)                   │
│    ▼                                                                         │
│    pead_eventos_{FWD}d_th{umbral}.csv                                        │
│                                                                              │
│ 6. BACKTEST COMBINADO (momentum + PEAD)                                      │
│    momentum_pead_backtest.py [universo] [topk] [λ]                           │
│    │  (señal = z(momentum) + λ·z(PEAD), TopkDropout)                        │
│    ▼                                                                         │
│    Resultado: combo NO supera a momentum solo (Sharpe 0.57 vs 1.0)           │
│    → PEAD se usa como FILTRO, no como señal sumada                           │
│                                                                              │
│ 7. PAPER-TRADING ESTRATEGIA 2 (momentum + filtro PEAD)                       │
│    backfill_pead.py → reconstrucción retroactiva 14→22-ago → state_pead.json │
│    simulation/simulate_pead.py [--reset]  → rebalancea estrategia 2 semanal  │
│    (lee pead_earnings_appended.csv, filtra names con sorpresa < -5%)         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Scripts y su propósito

| Script | Propósito | Salida |
|---|---|---|
| `pead_fetch_append.py` | **APPEND-ONLY** earnings (point-in-time safe): lee historial, añade solo filas nuevas, no borra/edita, guard anti-fallo | `pead_earnings_appended.csv` |
| `pead_fetch_full.py` | (Legacy) Sobrescribe earnings completos | `pead_earnings_data_full.csv` |
| `pead_faseA.py [N]` | Analizar distribución de sorpresas | `pead_earnings_data.csv` |
| `pead_faseA2.py [FWD]` | IC sorpresa → retorno post-anuncio | `pead_returns_{FWD}d.csv` |
| `pead_combo.py [FWD]` | Combinación momentum + PEAD, IC por señal | — (consola) |
| `pead_eventos.py [FWD][delay][umbral]` | Estrategia de eventos, validación | `pead_eventos_*.csv` |
| `momentum_pead_backtest.py [univ][topk][λ]` | Backtest combinado momentum+PEAD | Resultado consola |
| `simulation/backfill_pead.py` | Reconstrucción retroactiva estrategia 2 | `state_pead.json` |
| `simulation/simulate_pead.py [--reset]` | Paper-trading estrategia 2 (momentum + filtro PEAD) | `state_pead.json` |

### Fuentes de datos
- **Earnings:** `yahooquery` (endpoint quoteSummary bloqueado → usamos yahooquery que funciona)
- **Precios:** Qlib local (`close/factor`) y `prices_live.csv` (fresco, actualizador ligero)

### Nota sobre la estrategia 2 (paper-trading en paralelo)
- Estrategia 1: momentum 120 puro (`simulate.py`)
- Estrategia 2: momentum 120 + filtro PEAD negativo (`simulate_pead.py`)
- Ambas con €20,000 ficticios, rebalanceo semanal, cronjobs sábado (00:00 precios, 01:00 earnings, 15:00 sim 1, 16:00 sim 2)

---

## 4. Documentación asociada

| Documento | Contenido |
|---|---|
| `pead_hallazgo.md` | Alpha confirmado del PEAD (IC 0.19-0.22) |
| `pead_faseC.md` | Combinación momentum+PEAD (IC +0.008, limitaciones) |
| `pead_eventos_resultado.md` | Validación estrategia de eventos (resultado mixto) |
| `estrategia_pead_eventos.md` | Cómo operar PEAD por eventos (señal, entrada/salida, sizing) |
| `quinn_paper_combinado.md` | Veredicto Quinn sobre paper-trading combinado |

---

## 5. Estado actual y siguiente paso

- ✅ **Datos earnings append-only** (`pead_earnings_appended.csv`, point-in-time safe) — `pead_fetch_append.py`
- ✅ **Estrategia 2 en paper-trading** paralela (momentum + filtro PEAD) — `simulate_pead.py`, reconstruida retroactiva 14→22-ago
- ✅ **Cronjobs configurados:** sáb 00:00 precios, 01:00 earnings (append-only), 15:00 sim 1, 16:00 sim 2
- ⏳ **Pendiente Quinn:** backtest OOS (walk-forward) de la estrategia 2 para validarla como la 1
- ⏳ **Pendiente:** usar SUE (normalización) en vez de surprise% crudo + ventana de frescura (~40 días)

**Regla de oro (Quinn):** fusionar PEAD en paper-trading solo si el backtest combinado mejora el Sharpe del momentum solo sin empeorar el drawdown; el PEAD se usa como filtro/refuerzo, no como señal sumada.

## 6. Historia de decisiones

- 2026-08-22: el backtest combinado (señal de ranking sumada, 284 tickers) NO supera a momentum solo → se descarta la suma, se implementa el PEAD como filtro (estrategia 2).
- 2026-08-22: los datos de earnings pasan a **append-only** (point-in-time safe) por recomendación de Quinn, para evitar look-ahead y pérdida de datos.

---

*Documento de referencia del proyecto Qlib Work.*
