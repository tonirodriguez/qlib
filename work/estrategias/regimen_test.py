"""regimen_test.py — Semana 3-4 del plan de Quinn.

Demuestra (o descarta) con RIGOR la dependencia de régimen del momentum 120d:

1. Pre-registra la hipótesis falsable (ANTES de correr).
2. Calcula el IC del momentum condicionado por ESTADO (vol_pct, drawdown120)
   usando la serie de estados generada por extract_estados.py.
3. Bootstrap de CI (percentiles 2.5-97.5) para ver si los estados "se distinguen".
4. Regresión de interacción OLS (statsmodels) para ver si el estado modula el IC
   significativamente, y contraste régimen vs decaimiento (término temporal).

Uso:
    python work/estrategias/regimen_test.py [fwd_days]
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

FWD = int(sys.argv[1]) if len(sys.argv) > 1 else 60
MOM_W = 120
UNIVERSE = "sp500_liquid"
START = "2018-01-01"
END = "2026-08-01"
STATES_CSV = "/opt/data/qlib/work/estrategias/estados_mercado.csv"

# ------------------------------------------------------------------
# 0. HIPÓTESIS FALSABLE PRE-REGISTRADA (no mover tras ver el resultado)
# ------------------------------------------------------------------
# HIPÓTESIS: "El momentum 120d es dependiente del régimen: su IC es
# sistemáticamente MENOR (o negativo) en estados de estrés (vol alta /
# drawdown) que en calma."
#
# SE FALSIFICA si, con los CI bootstrap honestos, el IC condicionado a
# estados de estrés NO difiere sistemáticamente (en dirección y magnitud)
# del IC en calma — es decir, si los CI de ambos estados se solapan, o si
# el coeficiente de interacción en la regresión no es significativo.
# ------------------------------------------------------------------

print("="*70)
print("REGIMEN TEST — Momentum 120d dependiente de régimen?  (FWD=%dd)" % FWD)
print("HIPÓTESIS PRE-REGISTRADA: el momentum rinde MENOS en estrés (vol/drawdown).")
print("CRITERIO FALSABLE: si los CI de estrés y calma se solapan → NO se distingue.")
print("="*70)


def main():
    # --- Datos ---
    from qlib.data import D as _D
    tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
    close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
    close = close["$close"].unstack(level=0).sort_index()

    mom = (close / close.shift(MOM_W) - 1)
    fwd = (close.shift(-FWD) / close - 1)

    # Largo
    mom_s = mom.stack().rename("momentum")
    fwd_s = fwd.stack().rename("fwd")
    df = pd.concat([mom_s, fwd_s], axis=1).dropna().reset_index()
    # La columna temporal puede llamarse 'date' o 'datetime' tras el stack
    time_col = "date" if "date" in df.columns else "datetime"
    inst_col = "instrument" if "instrument" in df.columns else "ticker"
    df = df.rename(columns={time_col: "date", inst_col: "ticker"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # --- Estados ---
    states = pd.read_csv(STATES_CSV, parse_dates=["datetime"])
    states = states.set_index("datetime")
    # estados por fecha (vol_pct, drawdown120)
    df = df.merge(states[["vol_pct", "drawdown120"]], left_on="date", right_index=True, how="inner")
    df = df.dropna(subset=["momentum", "fwd", "vol_pct", "drawdown120"])
    print(f"Muestras con estado: {len(df)}")

    # --- IC condicionado por estado con CI bootstrap ---
    print("\n" + "="*70)
    print("IC DEL MOMENTUM POR ESTADO (con CI bootstrap 95%)")
    print("="*70)

    def ic_sp(x, y):
        return x.corr(y, method="spearman")

    def ic_ci(sub):
        vals = []
        rng = np.random.default_rng(42)
        idx = np.arange(len(sub))
        for _ in range(1000):
            samp = rng.choice(idx, size=len(idx), replace=True)
            v = ic_sp(sub["momentum"].iloc[samp], sub["fwd"].iloc[samp])
            vals.append(v)
        vals = np.array(vals)
        return np.percentile(vals, 2.5), np.percentile(vals, 97.5)

    # Calma vs estrés por vol_pct
    calma = df[df["vol_pct"] < 0.75]
    estres = df[df["vol_pct"] >= 0.75]
    for name, sub in [("CALMA (vol<0.75)", calma), ("ESTRÉS (vol>=0.75)", estres)]:
        if len(sub) > 50:
            ic = ic_sp(sub["momentum"], sub["fwd"])
            lo, hi = ic_ci(sub)
            print(f"  {name}: n={len(sub):,} | IC_spearman={ic:+.4f} | CI=[{lo:+.4f}, {hi:+.4f}]")
        else:
            print(f"  {name}: n={len(sub)} (insuficiente)")

    # Alza vs drawdown
    alza = df[df["drawdown120"] == 0]
    dd = df[df["drawdown120"] == 1]
    for name, sub in [("ALZA (dd120=0)", alza), ("DRAWDOWN (dd120=1)", dd)]:
        if len(sub) > 50:
            ic = ic_sp(sub["momentum"], sub["fwd"])
            lo, hi = ic_ci(sub)
            print(f"  {name}: n={len(sub):,} | IC_spearman={ic:+.4f} | CI=[{lo:+.4f}, {hi:+.4f}]")
        else:
            print(f"  {name}: n={len(sub)} (insuficiente)")

    # --- Regresión de interacción (OLS via numpy para robustez) ---
    print("\n" + "="*70)
    print("REGRESIÓN DE INTERACCIÓN (¿el estado modula el IC?)")
    print("="*70)

    # IC por mes (para regresión a nivel de periodo, no de observación)
    df["ym"] = df["date"].dt.to_period("M")
    icm = df.groupby("ym", observed=True).apply(
        lambda g: pd.Series({
            "ic": ic_sp(g["momentum"], g["fwd"]),
            "vol_pct": g["vol_pct"].mean(),
            "drawdown120": g["drawdown120"].mean(),
        })
    ).dropna()

    icm = icm.reset_index(drop=True)
    icm["t"] = np.arange(len(icm))   # tiempo secuencial (0..N)
    print(f"Periodos con IC mensual: {len(icm)}")

    # Regresión: IC_m ~ alpha + beta1*vol_alta + beta2*drawdown + gamma*t
    # GDL simple con numpy (OLS)
    icm["vol_alta"] = (icm["vol_pct"] >= 0.75).astype(float)
    X = np.column_stack([
        np.ones(len(icm)),
        icm["vol_alta"].values,
        icm["drawdown120"].values,
        icm["t"].values / icm["t"].max(),   # tiempo normalizado
    ])
    y = icm["ic"].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    sigma2 = resid @ resid / dof
    cov = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    tstat = beta / se

    print(f"  Coef   b0(const) = {beta[0]:+.4f} (t={tstat[0]:+.2f})")
    print(f"  Coef   vol_alta  = {beta[1]:+.4f} (t={tstat[1]:+.2f})  <- régimen (vol)")
    print(f"  Coef   drawdown  = {beta[2]:+.4f} (t={tstat[2]:+.2f})  <- régimen (drawdown)")
    print(f"  Coef   tiempo    = {beta[3]:+.4f} (t={tstat[3]:+.2f})  <- decaimiento secular")
    print()
    # Veredicto preliminar
    sig_vol = abs(tstat[1]) > 1.96
    sig_dd = abs(tstat[2]) > 1.96
    sig_t = abs(tstat[3]) > 1.96
    neg_vol = beta[1] < 0
    print("  VEREDICTO (preliminar):")
    if sig_vol and neg_vol:
        print("  ✅ Vol alta reduce significativamente el IC → apoya RÉGIMEN (vol)")
    elif sig_dd and beta[2] < 0:
        print("  ✅ Drawdown reduce significativamente el IC → apoya RÉGIMEN (drawdown)")
    elif sig_t and beta[3] < 0:
        print("  ⚠️ Solo el tiempo es significativo y negativo → sugiere DECAIMIENTO secular, no régimen")
    else:
        print("  ⚖️ Sin coeficientes claramente significativos → no se puede afirmar régimen con rigor")

    print("\n  (Interpretación con cautela: n de periodos mensuales ~%d)" % len(icm))


if __name__ == "__main__":
    main()
