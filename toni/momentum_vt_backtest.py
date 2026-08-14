"""Backtest momentum 120d + VOL-TARGETING sobre sp500_liquid, con costes IB.

Combina el hallazgo (momentum 120d) con la gestión de riesgo (vol-targeting):
la estrategia reduce la exposición cuando la volatilidad del mercado sube,
mitigando el momentum-crash (2020/2022).

Uso:
    python toni/momentum_vt_backtest.py [universo] [topk] [mom_window] [vol_target]
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:////opt/data/qlib/qlib_work/mlflow.db"
import sys, numpy as np, pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

UNIVERSE = sys.argv[1] if len(sys.argv) > 1 else "sp500_liquid"
TOPK = int(sys.argv[2]) if len(sys.argv) > 2 else 30
MOM_W = int(sys.argv[3]) if len(sys.argv) > 3 else 120
VOL_TARGET = float(sys.argv[4]) if len(sys.argv) > 4 else 0.20
START = "2018-01-01"; END = "2026-08-01"

IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

print(f"Universo: {UNIVERSE} | topk={TOPK} | momentum={MOM_W}d | vol_target={VOL_TARGET}")

from qlib.data import D as _D
tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
close = close["$close"].unstack(level=0).sort_index()

# Señal momentum
mom_signal = close / close.shift(MOM_W) - 1
sig = mom_signal.stack().dropna()
sig.name = "momentum"
sig = sig.reset_index()
sig["datetime"] = pd.to_datetime(sig["datetime"])
sig = sig.set_index(["datetime", "instrument"])["momentum"].sort_index()
print(f"Señal: {len(sig)} puntos")

# Estrategia con vol-targeting
strategy = {
    "class": "VolTargetTopkStrategy",
    "module_path": "toni.vol_target_strategy",
    "kwargs": {
        "signal": sig,
        "topk": TOPK,
        "n_drop": 5,
        "only_tradable": True,
        "hold_thresh": 20,
        "vol_target": VOL_TARGET,
        "vol_window": 120,
        "min_risk_degree": 0.3,
        "max_risk_degree": 1.0,
        "benchmark": "^NDX",
    },
}
executor = {
    "class": "SimulatorExecutor",
    "module_path": "qlib.backtest.executor",
    "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
}

from qlib.backtest import backtest
report_normal, indicator = backtest(
    start_time="2022-01-01", end_time="2026-08-07",
    strategy=strategy, executor=executor,
    benchmark="^NDX", account=100000, exchange_kwargs=IB,
)

freq_key = list(report_normal.keys())[0]
df = report_normal[freq_key][0]
pv = df["account"].values
bv = df["bench"].values

port_ret = pd.Series(pv).pct_change().dropna().values
mean_ann = float(np.mean(port_ret)) * 52
vol_ann = float(np.std(port_ret)) * np.sqrt(52)
cum = np.cumprod(1 + port_ret)
dd = cum / np.maximum.accumulate(cum) - 1
max_dd = float(dd.min())
sharpe = mean_ann / vol_ann if vol_ann else np.nan

print("\n" + "="*56)
print(f"📊 MOMENTUM {MOM_W}d + VOL-TARGETING ({VOL_TARGET}) — {UNIVERSE}")
print("="*56)
print(f"  Valor final: ${pv[-1]:,.0f} (inicial ${pv[0]:,.0f})")
print(f"  Retorno anualizado ABS: {mean_ann*100:+.2f}%")
print(f"  Volatilidad anual:      {vol_ann*100:.2f}%")
print(f"  Max drawdown ABS:       {max_dd*100:.2f}%")
print(f"  Sharpe ABS:             {sharpe:.3f}")
