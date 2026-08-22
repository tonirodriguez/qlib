"""FASE C — Combinar momentum 120d + PEAD y validar IC out-of-sample.

Objetivo: comprobar si el combo de dos señales ortogonales (momentum de precio +
sorpresa de earnings) da mejor IC que cada una por separado.

Señal 1 (momentum 120d): de precios de Qlib.
Señal 2 (PEAD): sorpresa de earnings, forward-fill entre trimestres.

La combinación: z_score(momentum) + λ · z_score(PEAD), con λ optimizado simple.
Se mide el IC (correlación señal → retorno futuro) de cada combo.
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
UNIVERSE = "sp500_liquid"
MOM_W = 120
FWD = int(sys.argv[1]) if len(sys.argv) > 1 else 20

qlib.init(provider_uri=QLIB_URI, region='us')


def get_universe():
    inst = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt"
    tk = []
    with open(inst) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t: tk.append(t)
    return tk


def main():
    tickers = get_universe()
    # Precios
    close = D.features(tickers, ["$close", "$factor"], start_time="2018-01-01",
                       end_time="2100-12-31", freq="day")
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    prices = (c / f).sort_index()

    # Señal 1: momentum 120d
    mom = prices / prices.shift(MOM_W) - 1

    # Señal 2: PEAD (sorpresa) — cargar datos de earnings
    ear_file = "/opt/data/qlib/work/estrategias/pead_earnings_data.csv"
    ear = pd.read_csv(ear_file)
    # Construir serie temporal de sorpresa por ticker (a partir de reportedDate)
    ear["date"] = pd.to_datetime(ear["reported_ts"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
    # Serie por ticker-fecha de sorpresa
    pead = ear.set_index(["date", "ticker"])["surprise_pct"].sort_index()

    # Reindexar a la grid de precios (fecha × ticker), forward-fill la sorpresa entre trimestres
    grid = mom.iloc[:, :].copy()
    pead_grid = pd.Series(index=grid.index, dtype=float)
    # Construir DataFrame de PEAD reindexado
    pead_df = pead.unstack(level=0).T  # tickers como columns, fechas como index
    pead_df = pead_df.reindex(grid.index).ffill()
    # Alinear tickers
    for t in grid.columns:
        if t in pead_df.columns:
            grid[f"pead_{t}"] = pead_df[t].values
    print(f"PEAD integrado: {grid['pead_'+tickers[0]].notna().sum() if tickers[0] in grid.columns else 0} filas con sorpresa para {tickers[0]}")

    # --- Medir IC de cada señal por separado y del combo ---
    # Retorno futuro
    fwd_ret = prices.shift(-FWD) / prices - 1

    # Construir dataset largo (ticker, fecha)
    rows = []
    for t in grid.columns:
        if not t.startswith("pead_"):
            m = mom[t].dropna()
            p = grid.get(f"pead_{t}")
            r = fwd_ret[t]
            peak = p.dropna() if p is not None else None
            tmp = pd.DataFrame({"mom": m, "fwd": r})
            if peak is not None:
                tmp["pead"] = peak.reindex(tmp.index)
            tmp["ticker"] = t
            rows.append(tmp.reset_index())
    df = pd.concat(rows, ignore_index=True)
    df["date"] = pd.to_datetime(df["datetime"])
    df["year"] = df["date"].dt.year

    # z-scores
    for col in ["mom", "pead"]:
        if col in df.columns:
            df[col + "_z"] = df.groupby("date")[col].transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    df["combo"] = df["mom_z"] + 1.0 * df["pead_z"]

    print("\n" + "="*60)
    print("📊 IC POR SEÑAL Y POR AÑO (retorno futuro {FWD}d)".replace("{FWD}", str(FWD)))
    print("="*60)
    for signal in ["mom_z", "pead_z", "combo"]:
        if signal not in df.columns:
            continue
        ic_year = df.groupby("year").apply(lambda g: g[signal].corr(g["fwd"]))
        ic_overall = df[signal].corr(df["fwd"])
        print(f"\n  {signal}:")
        print(f"    IC total: {ic_overall:+.4f}")
        print(f"    IC por año: {[round(v,4) for v in ic_year.values]}")
        print(f"    IC medio anual: {ic_year.mean():+.4f}")

if __name__ == "__main__":
    main()
