"""
ic_short_term_sp500.py — IC de corto plazo (1d) sobre sp500_liquid en Qlib.

EJECUTAR EN MAC LOCAL (conda env 'finance', datos ~/.qlib/qlib_data/us_data).

Objetivo: diagnosticar si hay senal de corto plazo (retorno 1 dia) en acciones,
similar a la premisa de la estrategia SFM v8 (label 1d). Si el IC medio es debil
(|IC| < 0.005), la v8 tal cual NO tiene base en acciones.

Mide el Information Coefficient (rank-correlacion cross-seccional por fecha) entre
varios factores de corto plazo y el retorno FUTURO a 1 dia (t -> t+1).

Factores:
  - mom_1d / mom_5d / mom_20d   -> momentum de corto plazo
  - rev_1d                      -> reversal diario (-ret de ayer)
  - vol_20d                     -> volatilidad 20d

Referencia: el proyecto mide IC OOS +0.066 con momentum 120d en acciones (mas fuerte).
Aqui se busca si el horizonte CORTO tiene base.

Uso (Mac local, desde el repo):
  source activate finance
  python work/crypto/ic_short_term_sp500.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.config import REG_US
from qlib.data import D

# ---------------------------------------------------------------------------
# CONFIG (ajusta a tu entorno Mac)
# ---------------------------------------------------------------------------
QLIB_URI = "~/.qlib/qlib_data/us_data"   # dataset de acciones en el Mac
UNIVERSE_FILE = "work/estrategias/sp500_liquid.txt"  # universo (relativo al repo)

START = "2019-01-01"
END = "2026-08-30"
# ---------------------------------------------------------------------------


def ic_series(factor: pd.Series, fwd: pd.Series):
    """IC medio cross-seccional por fecha (rank corr factor vs forward)."""
    df = pd.DataFrame({"f": factor, "y": fwd}).dropna()
    ics = []
    for _, grp in df.groupby(level=0):
        if len(grp) < 10:
            continue
        ic = grp["f"].rank().corr(grp["y"].rank())
        if pd.notna(ic):
            ics.append(ic)
    return float(np.mean(ics)) if ics else np.nan, len(ics)


def main():
    qlib.init(provider_uri=QLIB_URI, region=REG_US, kernels=1)

    # Cargar tickers del universo sp500_liquid desde el archivo
    up = Path(UNIVERSE_FILE)
    if not up.exists():
        print(f"NO encuentro {up}. Ajusta UNIVERSE_FILE.")
        return
    tickers = [line.split()[0] for line in up.read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    print(f"Universo: {len(tickers)} tickers")

    # Cargar features de todos los tickers
    inst = tickers  # lista de instrumentos
    fields = ["$close", "$volume"]
    df = D.features(inst, fields, start_time=START, end_time=END, freq="day")

    close = df["$close"].unstack().sort_index()
    vol = df["$volume"].unstack().sort_index()

    ret_1d = close.pct_change()
    ret_5d = close.pct_change(5)
    ret_20d = close.pct_change(20)
    fwd_1d = ret_1d.shift(-1)  # retorno t -> t+1

    def to_long(sdf):
        return sdf.stack()

    factors = {
        "mom_1d": to_long(ret_1d),
        "mom_5d": to_long(ret_5d),
        "mom_20d": to_long(ret_20d),
        "rev_1d": to_long(-ret_1d),
        "vol_20d": to_long(ret_1d.rolling(20).std()),
    }
    fwd_long = to_long(fwd_1d)

    print(f"Periodo {START} -> {END}")
    print("IC medio cross-seccional (rank) factor vs retorno futuro 1d (t->t+1):")
    print("-" * 60)
    for name, fac in factors.items():
        ic, n = ic_series(fac.rename("f"), fwd_long.rename("y"))
        print(f"  {name:10s} IC={ic:+.4f}  (n_dias={n})")

    print("\nReferencia: IC OOS +0.066 con momentum 120d (hallazgo validado del proyecto).")
    print("Interpretacion: |IC| medio < 0.005 en horizontes 1d/5d -> el corto plazo es")
    print("debil y la SFM v8 tal cual (label 1d, alta rotacion) NO tendria base en acciones.")


if __name__ == "__main__":
    main()