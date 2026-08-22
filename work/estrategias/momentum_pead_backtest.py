"""Backtest combinado: PEAD + momentum 120d sobre sp500_liquid, con costes IB.

Compara la estrategia combinada (momentum + sorpresa de earnings) contra la de
solo momentum. La señal combinada es: z_score(momentum_120d) + LAMBDA*z_score(PEAD).

La señal PEAD se construye a partir de la sorpresa de earnings (surprise_pct),
forward-fill entre trimestres por ticker.

Uso:
    python work/estrategias/momentum_pead_backtest.py [universo] [topk] [lambda_pead]
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
LAMBDA_PEAD = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
MOM_W = 120
START = "2018-01-01"
END = "2026-08-01"

# Datos de earnings (sorpresa por ticker-trimestre) de la Fase A
EAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pead_earnings_data.csv")

IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

print(f"Universo: {UNIVERSE} | topk={TOPK} | momentum={MOM_W}d | lambda_pead={LAMBDA_PEAD}")


def get_universe():
    from qlib.data import D as _D
    return _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)


def zscore(df, axis=0):
    # CORRECTO para este caso: normalizar por COLUMNA (cada ticker) de forma tolerante a NaN.
    # El axis=1 (por fila/fecha) anulaba la señal con los NaN del shift inicial.
    return (df - df.mean(axis=axis)) / (df.std(axis=axis, ddof=0))


def main():
    tickers = get_universe()
    print(f"Tickers: {len(tickers)}")

    # ---- Señal momentum ----
    close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    mom = close / close.shift(MOM_W) - 1

    # ---- Señal PEAD (sorpresa earnings, forward-fill por ticker) ----
    pead_df = None
    if os.path.exists(EAR_FILE):
        ear = pd.read_csv(EAR_FILE)
        # fecha del anuncio
        ear["date"] = pd.to_datetime(ear["reported_ts"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
        # pivot: index=fecha, columns=ticker, values=surprise
        pead = ear.pivot_table(index="date", columns="ticker", values="surprise_pct", aggfunc="last")
        # reindexar a la misma grid de fechas que momentum y forward-fill
        grid_idx = close.index
        pead_grid = pead.reindex(grid_idx).ffill()
        pead_df = pead_grid
        print(f"PEAD: {ear.shape[0]} eventos, {len(pead_df.columns)} tickers con sorpresa")
    else:
        print(f"⚠️ No hay datos de earnings ({EAR_FILE}). La señal PEAD será 0.")

    # ---- Combinar: señales z-score alineadas ----
    mom_z = zscore(mom, axis=0)
    sig = mom_z.copy()
    if pead_df is not None:
        pead_z = zscore(pead_df, axis=0)
        # alinear columnas con el universo
        sig = mom_z + LAMBDA_PEAD * pead_z.reindex(columns=mom_z.columns).fillna(0)
    else:
        sig = mom_z

    # Convertir a Series de Qlib (MultiIndex datetime, instrument)
    sig_s = sig.stack().dropna()
    sig_s.name = "combo"
    sig_s = sig_s.reset_index()
    # el stack produce (datetime, instrument) — verificar nombre de columnas
    sig_s.columns = ["datetime", "instrument", "combo"] if sig_s.shape[1] == 3 else sig_s.columns
    sig_s["datetime"] = pd.to_datetime(sig_s["datetime"])
    sig_s = sig_s.set_index(["datetime", "instrument"])["combo"].sort_index()
    print(f"Señal combinada construida: {len(sig_s)} puntos")

    # ---- Backtest con Qlib ----
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

    print("\n" + "="*56)
    print(f"📊 BACKTEST MOMENTUM {MOM_W}d + PEAD (λ={LAMBDA_PEAD}) — {UNIVERSE} (topk {TOPK})")
    print("="*56)
    print(f"  Valor final: ${pv[-1]:,.0f} (inicial ${pv[0]:,.0f})")
    print(f"  Retorno anualizado ABS: {mean_ann*100:+.2f}%")
    print(f"  Volatilidad anual:      {vol_ann*100:.2f}%")
    print(f"  Max drawdown ABS:       {max_dd*100:.2f}%")
    print(f"  Sharpe ABS:             {sharpe:.3f}")
    print(f"  Exceso anualizado:      {exc_ann*100:+.2f}% (vs ^NDX)")
    print(f"  Information Ratio:      {ir:.3f}")


if __name__ == "__main__":
    main()
