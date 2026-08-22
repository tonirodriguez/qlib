"""Backtest de la ESTRATEGIA 2: momentum 120d + FILTRO PEAD negativo.

A diferencia de momentum_pead_backtest.py (que SUMABA z-scores), este script
implementa el FILTRO: la señal es momentum puro, pero los tickers cuya ÚLTIMA
sorpresa de earnings conocida (point-in-time, reported_ts <= fecha) es < umbral
se excluyen del topk (se les fuerza una señal muy baja para que TopkDropout
los elimine y tome los siguientes del ranking).

Esto valida la estrategia 2 (que está en paper-trading) con backtest OOS.

Uso:
    python work/estrategias/momentum_pead_filter_backtest.py [universo] [topk] [umbral]
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
SUE_PEAD_THRESHOLD = float(sys.argv[3]) if len(sys.argv) > 3 else -5.0
MOM_W = 120
START = "2018-01-01"
END = "2026-08-01"

# Datos de earnings: historial append-only (point-in-time) si existe
EAR_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pead_earnings_appended.csv")
EAR_FULL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pead_earnings_data_full.csv")
if os.path.exists(EAR_APP):
    EAR_FILE = EAR_APP
elif os.path.exists(EAR_FULL):
    EAR_FILE = EAR_FULL
else:
    EAR_FILE = None

IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

print(f"Universo: {UNIVERSE} | topk={TOPK} | momentum={MOM_W}d | filtro PEAD umbral={SUE_PEAD_THRESHOLD}%")


def get_universe():
    from qlib.data import D as _D
    return _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)


def main():
    tickers = get_universe()
    print(f"Tickers: {len(tickers)}")

    # ---- Señal momentum ----
    close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    mom = close / close.shift(MOM_W) - 1

    # ---- Señal PEAD filtrada (sorpresa earnings, point-in-time) ----
    surprise_grid = None
    if EAR_FILE:
        ear = pd.read_csv(EAR_FILE)
        ear["date"] = pd.to_datetime(ear["reported_ts"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
        # pivot: index=fecha, columns=ticker, values=surprise (última por fecha/ticker)
        pead = ear.pivot_table(index="date", columns="ticker", values="surprise_pct", aggfunc="last")
        # reindexar a la grid de fechas y rellenar con la última sorpresa conocida
        # PERO point-in-time: no forward-fill en el futuro (solo sorpresas ya reportadas <= fecha)
        surprise_grid = pead.reindex(close.index).ffill()
        print(f"PEAD: {ear.shape[0]} eventos, {len(pead.columns)} tickers con sorpresa")
    else:
        print("⚠️ No hay datos de earnings. Estrategia sin filtro (momentum puro).")

    # ---- Señal final: momentum, con filtro PEAD negativo ----
    # Señal = momentum puro. Para tickers con sorpresa < umbral, forzamos señal muy baja.
    sig = mom.copy()
    n_filtered = 0
    if surprise_grid is not None:
        pead_thresh = surprise_grid < SUE_PEAD_THRESHOLD  # DataFrame bool, válido donde hay sorpresa
        # Solo filtrar donde tenemos sorpresa negativa de earnings
        sig = sig.where(~pead_thresh.reindex(index=sig.index, columns=sig.columns).fillna(False), -1e9)
        n_filtered = int(pead_thresh.sum().sum())
    print(f"Puntos filtrados por PEAD negativo: {n_filtered}")

    # Convertir a Series de Qlib
    sig_s = sig.stack().dropna()
    sig_s.name = "mom_pead_filter"
    sig_s = sig_s.reset_index()
    sig_s.columns = ["datetime", "instrument", "seed"] if sig_s.shape[1] == 3 else sig_s.columns
    # el nombre de la 3ª col puede variar; fijarlo
    col3 = sig_s.columns[2]
    sig_s = sig_s.rename(columns={col3: "mom_pead_filter"})
    sig_s["datetime"] = pd.to_datetime(sig_s["datetime"])
    sig_s = sig_s.set_index(["datetime", "instrument"])["mom_pead_filter"].sort_index()
    print(f"Señal construida: {len(sig_s)} puntos")

    # ---- Backtest ----
    from qlib.backtest import backtest
    strategy = {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {"signal": sig_s, "topk": TOPK, "n_drop": 5, "only_tradable": True, "hold_thresh": 20},
    }
    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
    }
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
    bench_ret = pd.Series(bv).pct_change().dropna().values
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

    print("\n" + "="*60)
    print(f"📊 BACKTEST MOMENTUM {MOM_W}d + FILTRO PEAD (umbral {SUE_PEAD_THRESHOLD}%)")
    print("="*60)
    print(f"  Valor final: ${pv[-1]:,.0f} (inicial ${pv[0]:,.0f})")
    print(f"  Retorno anualizado ABS: {mean_ann*100:+.2f}%")
    print(f"  Volatilidad anual:      {vol_ann*100:.2f}%")
    print(f"  Max drawdown ABS:       {max_dd*100:.2f}%")
    print(f"  Sharpe ABS:             {sharpe:.3f}")
    print(f"  Exceso anualizado:      {exc_ann*100:+.2f}% (vs ^NDX)")
    print(f"  Information Ratio:      {ir:.3f}")
    print(f"\n  (Comparator: momentum puro = Sharpe ~1.0, +18-21% anual, DD ~-19%)")
    print(f"  (Puntos excluidos por el filtro PEAD: {n_filtered})")


if __name__ == "__main__":
    main()
