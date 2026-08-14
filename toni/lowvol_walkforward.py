"""Walk-forward del factor LOW-VOLATILIDAD sobre sp500_liquid, para combinar con momentum.

Señal de low-vol: retorno esperado inverso a la volatilidad pasada. Se usa la
volatilidad (desviación estándar de retornos en una ventana) como factor; si low-vol
tiene alpha (IC positivo), combinarlo con momentum (que es ortogonal) mejora el Sharpe.

Mide IC de (volatilidad inversa) contra retorno futuro. NOTA: aquí "low-vol" como
factor transversal significa que las acciones de MENOR volatilidad tienden a rendir
más (IC negativo de vol vs retorno futuro = las de menor vol sobre-performan).
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
import sys, numpy as np, pandas as pd
import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

UNIVERSE = sys.argv[1] if len(sys.argv) > 1 else "sp500_liquid"
FWD = int(sys.argv[2]) if len(sys.argv) > 2 else 120
START = "2018-01-01"; END = "2026-08-01"

from qlib.data import D as _D
tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
print(f"Universo: {UNIVERSE} ({len(tickers)} tickers) | label {FWD}d")

close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
close = close["$close"].unstack(level=0).sort_index()

# Retornos diarios
ret = close.pct_change()
# Volatilidad en ventana de 120 días (anualizada implícita al ordenar)
vol = ret.rolling(120).std()

# Señal low-vol: volatilidad (más fiel al factor original Frazzini-Pedersen)
# IC de vol vs retorno futuro. Si es NEGATIVO -> las de menor vol sobre-performan (low-vol funciona)
fwd_ret = close.shift(-FWD) / close - 1

v = vol.stack(dropna=False).rename("vol")
f = fwd_ret.stack(dropna=False).rename("fwd")
df = pd.concat([v, f], axis=1).reset_index()
df["datetime"] = pd.to_datetime(df["datetime"])
df["year"] = df["datetime"].dt.year
df = df.dropna()

print("\nIC (volatilidad -> retorno futuro) por año:")
print("  (NEGATIVO = low-vol funciona: las de menos vol rinden mas)")
ics = {}
for year in sorted(df["year"].unique()):
    y = df[df["year"] == year]
    if len(y) < 100: continue
    ic = y["vol"].corr(y["fwd"])
    ics[year] = ic
    # Long-short: decil bajo vol vs alto vol
    y["pct"] = y.groupby("datetime")["vol"].rank(pct=True)
    low = y[y["pct"] <= 0.2]["fwd"].mean()
    high = y[y["pct"] >= 0.8]["fwd"].mean()
    print(f"  {year}: IC vol->fwd {ic:+.4f} | L/S (low-vol vs high-vol): {(low-high)*100:+.2f}%")

mean_ic = np.mean(list(ics.values()))
print(f"\nIC medio de vol: {mean_ic:+.4f}")
if mean_ic < -0.01:
    print("✅ Low-vol funciona: la volatilidad inversa tiene alpha (las de menor vol sobre-performan)")
    print("   Combinar con momentum deberia mejorar el Sharpe (son ortogonales)")
elif mean_ic < 0:
    print("⚠️ Low-vol positivo pero debil")
else:
    print("❌ Low-vol no da alpha en este universo/frecuencia (IC positivo = high-vol sobre-performa)")
