"""Momentum puro + walk-forward validation sobre tech_giants.

Señal: momentum (retorno acumulado pasados en varias ventanas: 20, 60, 120 días)
como predictores directos del retorno futuro a 10 días (label). Sin modelo ML:
se usa la correlación (IC) entre momentum-pasado y retorno-futuro, y el long-short
spread del decil. Walk-forward por ventanas para ver si el alpha se sostiene OOS.

Si el momentum tiene edge real, el IC será >0 de forma sostenida.
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
import sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

# ------- Parámetros (universo y label horizon configurable por argumento) -------
INSTRUMENTS = sys.argv[1] if len(sys.argv) > 1 else "tech_giants_universe"
FWD = int(sys.argv[2]) if len(sys.argv) > 2 else 10   # horizonte del label (días)
START = "2018-01-01"
END = "2026-08-01"

# Ventanas de momentum a probar (días)
MOM_WINDOWS = [20, 60, 120, 250]

print("Cargando cierres del universo tech_giants...")
from qlib.data import D as _D
# Resolver el universo a la lista de tickers
inst_pool = _D.instruments(INSTRUMENTS)
tickers = _D.list_instruments(inst_pool, as_list=True)
print(f"Tickers en universo {INSTRUMENTS}: {len(tickers)}")
close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
close = close["$close"].unstack(level=0)  # columnas = tickers, index = fecha
close = close.sort_index()
print(f"Shape cierres: {close.shape} | rango: {close.index[0].date()} → {close.index[-1].date()}")

# Construir tabla: por cada fecha e instrumento, momentum a varias ventanas y retorno futuro
dfs = []
for w in MOM_WINDOWS:
    mom = close.pct_change(w)
    mom = mom.stack(dropna=False).rename(f"mom{w}")
    dfs.append(mom)

# Retorno futuro a FWD días (usando cierres desplazados -2/-1 como label equivalente al modelo)
fwd_ret = close.shift(-FWD) / close - 1
fwd_ret = fwd_ret.stack(dropna=False).rename("fwd_ret")

alldf = pd.concat([*(d for d in dfs if not d.empty), fwd_ret], axis=1, keys=None)
# El MultiIndex tras stack() es (datetime, instrument) — nombrarlo correctamente
alldf = alldf.rename_axis(["date", "instrument"])
alldf = alldf.dropna()
print(f"Filas válidas (ticker x fecha): {len(alldf)}")

# --- Walk-forward: dividir por año y medir IC + long-short por ventana ---
alldf = alldf.reset_index()
alldf["date"] = pd.to_datetime(alldf["date"])
alldf["year"] = alldf["date"].dt.year

print("\n" + "="*70)
print("WALK-FORWARD MOMENTUM — IC (corr momentum → retorno futuro 10d) por año")
print("="*70)

mom_cols = [f"mom{w}" for w in MOM_WINDOWS]
all_ic = []
for year in sorted(alldf["year"].unique()):
    ydf = alldf[alldf["year"] == year]
    if len(ydf) < 100:
        continue
    row_ic = {}
    for col in mom_cols:
        ic = ydf[col].corr(ydf["fwd_ret"])
        row_ic[col] = ic
    # Long-short del mejor momentum (60d como referencia)
    ydf["pct"] = ydf.groupby("date")["mom60"].rank(pct=True)
    top = ydf[ydf["pct"] >= 0.7]["fwd_ret"].mean()
    bot = ydf[ydf["pct"] <= 0.3]["fwd_ret"].mean()
    all_ic.append((year, row_ic, top, bot))
    ic_str = " | ".join(f"{c}: {row_ic[c]:+.4f}" for c in mom_cols)
    print(f"  {year}: {ic_str} | L/S(60d): {(top-bot)*100:+.2f}%")

print("\n" + "="*70)
if all_ic:
    ic_matrix = pd.DataFrame([r[1] for r in all_ic], index=[r[0] for r in all_ic])
    print(f"IC medio por ventana de momentum (out-of-sample por año):")
    print(ic_matrix.mean().round(4))
    best_col = ic_matrix.mean().abs().idxmax()
    print(f"\nMejor ventana: {best_col} (IC medio {ic_matrix[best_col].mean():+.4f})")

    print("\nLECTURA:")
    ic_all_mean = ic_matrix.mean()
    if ic_all_mean.max() > 0.02:
        print(f"✅ Momentum con {ic_all_mean.idxmax()} tiene alpha OOS (IC {ic_all_mean.max():.4f} > 0.02).")
    elif ic_all_mean.max() > 0:
        print(f"⚠️ Momentum positivo pero débil OOS (IC max {ic_all_mean.max():.4f}).")
    else:
        print("❌ El momentum tampoco muestra alpha robusto OOS en este universo/frecuencia.")
else:
    print("Sin datos suficientes para el análisis.")
