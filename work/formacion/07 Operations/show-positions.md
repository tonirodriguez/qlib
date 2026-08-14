# show_positions.py — Ver qué comprar/vender en cada experimento

> Script independiente para inspeccionar las posiciones de cualquier experimento de Qlib.

---

## ⚡ Uso rápido

```bash
# 1. Ver runs disponibles
python scripts/show_positions.py

# 2. Último día con cambios (qué comprar/vender)
python scripts/show_positions.py --run <RUN_ID> --diffs

# 3. Un día concreto
python scripts/show_positions.py --run <RUN_ID> --date 2020-03-15

# 4. Resumen de tickers más rotados en todo el backtest
python scripts/show_positions.py --run <RUN_ID> --trades

# 5. Cambiar top N (defecto: 50)
python scripts/show_positions.py --run <RUN_ID> --top 10
```

---

## 📖 Modos

### `--run <RUN_ID>` (obligatorio tras listar)

Muestra las posiciones de un día concreto del backtest.

| Flag | Defecto | Descripción |
|------|---------|-------------|
| `--date` / `-d` | `last` | Fecha `YYYY-MM-DD` o `last` |
| `--top` / `-t` | `50` | Número de posiciones a mostrar |
| `--diffs` | `false` | Compara con el día anterior (COMPRAR/VENDER/HOLD) |

**Salida de ejemplo:**
```
📊 Run: mlflow_recorder
   Experiment: qlib_baseline_lightgbm_alpha158_csi300_tuned
   Total trading days: 871
   Date range: 2017-01-03 → 2020-07-31

📅 2020-07-31
   Cash:      4.915.880  |  Portfolio:    177.511.522  |  Total:    182.427.402

Acción       |     Acciones |     Precio |          Valor |     Peso | Días | Acción
SZ300136     |      378.412 |    13.9292 |      5.270.991 |    2.89% |    2 |   HOLD
SZ000157     |      160.140 |    24.3096 |      3.892.938 |    2.13% |    1 | 🟢 COMPRAR
SH601633     |      924.457 |     4.2110 |      3.892.860 |    2.13% |    1 | 🟢 COMPRAR
...
SH600588     |           0 |          0 |             0 |    0.00% |    0 | 🔴 VENDER
```

**Leyenda de la columna Acción:**
- 🟢 **COMPRAR** — nueva entrada o aumento de posición
- 🔴 **VENDER** — posición total o parcialmente cerrada
- **HOLD** — se mantiene igual que el día anterior

### `--trades`

Resumen agregado de los tickers que más se han rotado durante todo el backtest.

```
Acción       |       Comprado |        Vendido |          Total | Días en cartera
SZ002714     |    101.571.717 |    101.228.664 |    202.800.381 | 1225 días
```

Útil para detectar tickers de alta rotación (mucho ruido) vs tickers que el modelo mantiene estables.

---

## 🗺️ Arquitectura

El script lee los artifacts que Qlib guarda automáticamente tras cada backtest:

```
mlruns/<experiment_id>/<run_id>/artifacts/portfolio_analysis/
├── positions_normal_1day.pkl   ← posiciones día a día (diccionario fecha → Position)
├── report_normal_1day.pkl      ← return, turnover, cost, benchmark
├── port_analysis_1day.pkl      ← métricas de riesgo agregadas
└── indicator_analysis_1day.pkl ← ffr, pa, pos
```

No necesita Qlib inicializado — solo Python estándar + pickle + numpy/pandas para leer los `.pkl`.

---

## 📦 Dependencias

- Python 3.8+
- `numpy`, `pandas` (ya instaladas con Qlib)
- `pyyaml` (ya instalado con Qlib)

**No necesita Qlib activo** — funciona directamente sobre los archivos de `mlruns/`.

---

## 📝 Registrar en la wiki

```bash
# Si quieres regenerar la wiki después de un experimento:
python scripts/run_baseline_workflow.py --config ... --mode train
```

Luego:

```bash
python scripts/show_positions.py --run <RUN_ID> --top 20 --diffs
```

---

> **Siguiente paso:** Usa `--diffs` para ver exactamente qué órdenes ejecutaría el modelo mañana, y `--trades` para entender qué tickers dominan tu rotación.
