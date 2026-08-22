"""PURGED CV aplicado al MOMENTUM 120d sobre sp500_liquid.

Valida si el IC OOS del momentum 120d (+0.066) se mantiene con el método
riguroso (purged cross-validation), igual que hicimos con el PEAD.

Método:
- Señal: momentum 120d (retorno acumulado en 120 días)
- Label: retorno futuro a FWD días
- Muestras: todos los (fecha, ticker) del universo
- Purged CV: dividir por tiempo en pliegues, IC solo en el pliegue test
  (out-of-sample), eliminando el solapamiento de etiquetas de los vecinos.

Uso:
    python work/estrategias/momentum_purgedcv.py [fwd_days] [n_splits]
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

FWD = int(sys.argv[1]) if len(sys.argv) > 1 else 60
N_SPLITS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
MOM_W = 120
UNIVERSE = "sp500_liquid"
START = "2018-01-01"
END = "2026-08-01"


def main():
    from qlib.data import D as _D
    tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
    print(f"Universo: {UNIVERSE} ({len(tickers)} tickers)")

    close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    print(f"Shape cierres: {close.shape}")

    # Señal momentum 120d
    mom = close / close.shift(MOM_W) - 1
    # Label: retorno futuro a FWD días
    fwd = close.shift(-FWD) / close - 1

    # Largo: (fecha, ticker)
    mom_s = mom.stack().rename("momentum_120d")
    fwd_s = fwd.stack().rename(f"fwd_{FWD}d")
    df = pd.concat([mom_s, fwd_s], axis=1).dropna()
    df = df.reset_index().rename(columns={"datetime": "date", "instrument": "ticker"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"Muestras (ticker×fecha): {len(df)}\n")

    # --- IC GLOBAL (sin purge) ---
    ic_global = df["momentum_120d"].corr(df[f"fwd_{FWD}d"])
    sp_global = df["momentum_120d"].corr(df[f"fwd_{FWD}d"], method="spearman")
    print("="*60)
    print(f"📊 IC GLOBAL (sin purge) — momentum 120d → retorno {FWD}d")
    print("="*60)
    print(f"  Muestras: {len(df)}")
    print(f"  IC Pearson:  {ic_global:+.4f}")
    print(f"  IC Spearman: {sp_global:+.4f}\n")

    # --- PURGED CV: pliegues temporales ---
    edges = np.quantile(np.arange(len(df)), np.linspace(0, 1, N_SPLITS + 1)).astype(int)
    print("="*60)
    print(f"🧬 PURGED CV ({N_SPLITS} pliegues temporales, retorno {FWD}d)")
    print("="*60)

    ic_list, sp_list = [], []
    for k in range(N_SPLITS):
        test = df.iloc[edges[k]:edges[k + 1]]
        ic = test["momentum_120d"].corr(test[f"fwd_{FWD}d"])
        sp = test["momentum_120d"].corr(test[f"fwd_{FWD}d"], method="spearman")
        ic_list.append(ic); sp_list.append(sp)
        print(f"  Pliegue {k+1}: {len(test)} muestras | {test['date'].min().date()}→{test['date'].max().date()} "
              f"| IC P {ic:+.4f} | IC Sp {sp:+.4f}")

    ic_mean = float(np.nanmean(ic_list))
    sp_mean = float(np.nanmean(sp_list))
    print("="*60)
    print(f"  IC Pearson PURGED medio:  {ic_mean:+.4f}")
    print(f"  IC Spearman PURGED medio: {sp_mean:+.4f}")
    print()
    print(f"  Comparativa:")
    print(f"    IC Pearson  global {ic_global:+.4f} → purged {ic_mean:+.4f}  (Δ {ic_mean-ic_global:+.4f})")
    print(f"    IC Spearman global {sp_global:+.4f} → purged {sp_mean:+.4f}  (Δ {sp_mean-sp_global:+.4f})")
    print()
    if sp_mean > 0.02:
        print(f"  ✅ Momentum mantiene alpha con purged CV (IC Sp {sp_mean:+.4f} > 0.02)")
    elif sp_mean > 0:
        print(f"  ⚠️ Momentum positivo pero débil tras purgar")
    else:
        print("  ❌ Momentum se desvanece con purged CV → el alpha era solapamiento de etiquetas")

    out = f"/opt/data/qlib/work/estrategias/momentum_purgedcv_{FWD}d.csv"
    df.to_csv(out, index=False)
    print(f"\n✅ Datos guardados en {out}")


if __name__ == "__main__":
    main()
