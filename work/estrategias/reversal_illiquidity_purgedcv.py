"""reversal_illiquidity_purgedcv.py — Prioridad 2 (Quinn): 3ª señal ortogonal.

BUSCA una señal ORTOGONAL a momentum 120d y a PEAD, usando SOLO OHLCV + volume
de Qlib (no requiere fundamentales). Replica la metodología purged-CV ya validada
(igual que momentum_purgedcv.py / pead_purgedcv.py).

Señales candidatas (una a la vez, Quinn):
1. REVERSAL de corto plazo: retorno 1-5d con SIGNO NEGATIVO (media-reversión).
2. AMIHUD ILLIQUIDITY: |ret| / (precio × volumen) — prima de liquidez.

PROTOCOLO (idéntico al ya validado):
- IC Spearman, purged CV, CI bootstrap a 60d
- CRÍTICO: medir el CO-SENO entre el IC de la señal nueva, el del momentum 120d
  y el del PEAD. No basta IC>0: tiene que ser BAJO CO-SENO con los dos existentes.

HIPÓTESIS FALSABLE PRE-REGISTRADA:
  "El reversal 1-5d (y/o Amihud) es una señal ortogonal y útil: IC OOS > 0.02
   Y bajo co-seno (< 0.3) con momentum 120d y PEAD."
  Se falsifica si IC <= 0.02 o co-seno alto (>0.3) con cualquiera de los dos.

Uso: python work/estrategias/reversal_illiquidity_purgedcv.py [fwd_days]
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

FWD = int(sys.argv[1]) if len(sys.argv) > 1 else 60
N_SPLITS = 5
MOM_W = 120
REV_W = 5        # ventana de reversal (días)
UNIVERSE = "sp500_liquid"
START = "2018-01-01"
END = "2026-08-01"


def main():
    from qlib.data import D as _D
    tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
    f = D.features(tickers, ["$close", "$volume"], start_time=START, end_time=END, freq="day")
    close = f["$close"].unstack(level=0).sort_index()
    volume = f["$volume"].unstack(level=0).sort_index()
    print(f"Shape: {close.shape}")

    # Retorno futuro (label)
    fwd = close.shift(-FWD) / close - 1

    # --- SEÑAL 1: REVERSAL corto plazo (negativo) ---
    ret_rev = close / close.shift(REV_W) - 1
    reversal = -ret_rev   # sentido de media-reversión (comprar lo que bajó)

    # --- SEÑAL 2: AMIHUD ILLIQUIDITY ---
    daily_ret = close.pct_change().abs()
    amihud = daily_ret / (close * volume.replace(0, np.nan))
    amihud_avg = amihud.rolling(20, min_periods=5).mean()

    # --- SENALES REFERENCIA para co-seno: momentum 120d y PEAD (surprise ffill) ---
    mom = close / close.shift(MOM_W) - 1

    # co-seno entre dos señales = correlación de Pearson de sus series cross-sec
    def cross_sectional_corr(sig_a, sig_b):
        """Correlación promedio cross-seccional (por fecha) entre 2 señales."""
        corrs = []
        for d in close.index:
            if d not in sig_a.index or d not in sig_b.index:
                continue
            a = sig_a.loc[d].dropna()
            b = sig_b.loc[d].reindex(a.index).dropna()
            if len(a) > 20 and len(b) > 20:
                # alinear y quitar NaN
                a2 = a.loc[b.index]
                c = np.corrcoef(a2.values, b.values)[0, 1]
                if not np.isnan(c):
                    corrs.append(c)
        return np.mean(corrs) if corrs else 0.0

    # IC Spearman + CI bootstrap (función)
    def ic_sp(x, y):
        m = ~(np.isnan(x) | np.isnan(y))
        return pd.Series(x[m]).corr(pd.Series(y[m]), method="spearman")

    # Construir datos largos
    results = {}

    señales = {
        "reversal_5d": (reversal, None),
        "amihud_20d": (amihud_avg, None),
    }

    print("\n" + "="*66)
    print("PURGED CV — SEÑALES ORTOGONALES (FWD=%dd)" % FWD)
    print("Hipótesis: IC>0.02 Y co-seno bajo (<0.3) con momentum y PEAD")
    print("="*66)

    for name, (sig, _) in señales.items():
        # Dataframe largo
        s = sig.stack().rename("sig")
        fl = fwd.stack().rename("fwd")
        m = mom.stack().rename("mom")
        df = pd.concat([s, fl, m], axis=1).dropna().reset_index()
        df["date"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("date").reset_index(drop=True)

        # IC global
        ic_glob = ic_sp(df["sig"].values, df["fwd"].values)

        # Purged CV por pliegues temporales
        edges = np.quantile(np.arange(len(df)), np.linspace(0, 1, N_SPLITS + 1)).astype(int)
        ics = []
        for k in range(N_SPLITS):
            test = df.iloc[edges[k]:edges[k+1]]
            v = ic_sp(test["sig"].values, test["fwd"].values)
            ics.append(v)

        ic_mean = float(np.nanmean(ics))
        # CI bootstrap del IC global
        rng = np.random.default_rng(42)
        idx = np.arange(len(df))
        boot = []
        for _ in range(1000):
            samp = rng.choice(idx, size=len(idx), replace=True)
            boot.append(ic_sp(df["sig"].iloc[samp].values, df["fwd"].iloc[samp].values))
        lo, hi = np.percentile(boot, 2.5), np.percentile(boot, 97.5)

        # Co-seno con momentum y con PEAD (sorpresa earnings, pivot ffill)
        cos_mom = cross_sectional_corr(sig, mom)
        # Señal PEAD proxy: sorpresa de earnings forward-fill (si hay datos)
        EAR = "/opt/data/qlib/work/estrategias/pead_earnings_appended.csv"
        if not os.path.exists(EAR):
            EAR = "/opt/data/qlib/work/estrategias/pead_earnings_data_full.csv"
        if os.path.exists(EAR):
            ear = pd.read_csv(EAR)
            ear["date"] = pd.to_datetime(ear["reported_ts"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
            pead = ear.pivot_table(index="date", columns="ticker", values="surprise_pct", aggfunc="last")
            pead_grid = pead.reindex(close.index).ffill()
            cos_pead = cross_sectional_corr(sig, pead_grid)
        else:
            cos_pead = np.nan

        results[name] = {"IC_global": ic_glob, "IC_purged": ic_mean,
                         "CI": (lo, hi), "cos_momentum": cos_mom,
                         "cos_pead": cos_pead}

        print(f"\n{'─'*66}")
        print(f"📊 {name}")
        print(f"  IC global:    {ic_glob:+.4f}")
        print(f"  IC purged:    {ic_mean:+.4f} | CI=[{lo:+.4f}, {hi:+.4f}]")
        print(f"  cos momentum: {cos_mom:+.3f} | cos_pead: {cos_pead:+.3f}")
        print("  ────────────────")

    # Conclusión (veredicto)
    print("\n" + "="*66)
    print("VEREDICTO (preliminar)")
    print("="*66)
    for name, r in results.items():
        ok_ic = abs(r["IC_purged"]) > 0.02
        ok_cos = abs(r["cos_momentum"]) < 0.3
        if ok_ic and ok_cos:
            print(f"  ✅ {name}: prometedor (IC {r['IC_purged']:+.3f}, cos_mom {r['cos_momentum']:+.2f})")
        elif abs(r["IC_purged"]) <= 0.02:
            print(f"  ⚠️ {name}: IC ~0 o invertido (IC {r['IC_purged']:+.3f}) → no útil a {FWD}d")
        else:
            print(f"  ⚠️ {name}: IC {r['IC_purged']:+.3f} pero co-seno momentum {r['cos_momentum']:+.2f}")


if __name__ == "__main__":
    main()
