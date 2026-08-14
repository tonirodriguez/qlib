"""Backtest de la señal de momentum 120d sobre sp500_liquid, con costes IB.

Hallazgo base: momentum 120d + label 120d da IC OOS +0.066 en universo amplio.
Este script construye la señal de momentum (retorno acumulado 120 días) y la
ejecuta con TopkDropoutStrategy, rebalanceo mensual, costes Interactive Brokers.

Uso:
    python work/estrategias/momentum_backtest.py [universo] [topk] [mom_window]
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:////opt/data/qlib/work/qlib_work/mlflow.db"
import sys, numpy as np, pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

UNIVERSE = sys.argv[1] if len(sys.argv) > 1 else "sp500_liquid"
TOPK = int(sys.argv[2]) if len(sys.argv) > 2 else 30
MOM_W = int(sys.argv[3]) if len(sys.argv) > 3 else 120
START = "2018-01-01"
END = "2026-08-01"

# Costes Interactive Brokers (round-trip ~0.10%)
IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

print(f"Universo: {UNIVERSE} | topk={TOPK} | momentum={MOM_W}d")

# Resolver universo
from qlib.data import D as _D
tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
print(f"Tickers: {len(tickers)}")

# Cargar cierres y construir señal de momentum (retorno acumulado MOM_W días)
close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
close = close["$close"].unstack(level=0).sort_index()

# Señal momentum: retorno acumulado en la ventana (a fecha t)
mom_signal = close / close.shift(MOM_W) - 1
# En el backtest usamos la señal conocida a fecha t para decidir el rebalanceo
# (TopkDropoutStrategy usa la señal del dia previo via shift interno)

# Convertir a Series de Qlib (index MultiIndex datetime, instrument tras stack())
sig = mom_signal.stack().dropna()
sig.name = "momentum"
sig = sig.reset_index()
sig["datetime"] = pd.to_datetime(sig["datetime"])
sig = sig.set_index(["datetime", "instrument"])["momentum"]
sig = sig.sort_index()
print(f"Señal construida: {len(sig)} puntos | rango {sig.index.get_level_values(0).min()} → {sig.index.get_level_values(0).max()}")

# Backtest con Qlib
from qlib.backtest import backtest
from qlib.utils import init_instance_by_config

strategy = {
    "class": "TopkDropoutStrategy",
    "module_path": "qlib.contrib.strategy",
    "kwargs": {
        "signal": sig,
        "topk": TOPK,
        "n_drop": 5,
        "only_tradable": True,
        "hold_thresh": 20,
    },
}
executor = {
    "class": "SimulatorExecutor",
    "module_path": "qlib.backtest.executor",
    "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
}

report_normal, indicator = backtest(
    start_time="2022-01-01",
    end_time="2026-08-07",
    strategy=strategy,
    executor=executor,
    benchmark="^NDX",
    account=100000,
    exchange_kwargs=IB,
)

# Reporte
freq_key = list(report_normal.keys())[0]
df = report_normal[freq_key][0]
pv = df["account"].values
bv = df["bench"].values

port_ret = pd.Series(pv).pct_change().dropna().values
bench_ret = pd.Series(bv).pct_change().dropna().values
n = len(pv) / 52  # ~4.6 años
mean_ann = float(np.mean(port_ret)) * 52
vol_ann = float(np.std(port_ret)) * np.sqrt(52)
cum = np.cumprod(1 + port_ret)
dd = cum / np.maximum.accumulate(cum) - 1
max_dd = float(dd.min())
sharpe = mean_ann / vol_ann if vol_ann else np.nan
cum_b = np.cumprod(1 + bench_ret)
excess = port_ret - bench_ret
exc_ann = float(np.mean(excess)) * 52
ir = exc_ann / (float(np.std(excess)) * np.sqrt(52)) if np.std(excess) else np.nan

print("\n" + "="*56)
print(f"📊 BACKTEST MOMENTUM {MOM_W}d — {UNIVERSE} (topk {TOPK})")
print("="*56)
print(f"  Valor final: ${pv[-1]:,.0f} (inicial ${pv[0]:,.0f})")
print(f"  Retorno anualizado ABS: {mean_ann*100:+.2f}%")
print(f"  Volatilidad anual:      {vol_ann*100:.2f}%")
print(f"  Max drawdown ABS:       {max_dd*100:.2f}%")
print(f"  Sharpe ABS:             {sharpe:.3f}")
print(f"  Exceso anualizado:      {exc_ann*100:+.2f}% (vs ^NDX)")
print(f"  Information Ratio:      {ir:.3f}")
print(f"  Benchmark ret:          {((1+cum_b[-1])**(1/4.6)-1)*100:+.2f}%")
