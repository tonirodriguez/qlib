"""vol_gate_test.py — Semana 5: validar el vol-gating contra momentum puro.

Usa el MOTOR DE BACKTEST DE QLIB (fiable) para comparar:
- momentum 120d puro (topk 30)
- momentum 120d + vol-gate (varios umbrales del grid guardado)

Cómo aplica el gate: multiplicar TODA la señal de momentum por el nivel de
gate por fecha (1.0 en calma, 0.5 en vol alta, 0.0 en vol muy alta). Así el
TopkDropout reduce/disminuye la exposición del momentum cuando la vol es alta.

Grid guardado: P70/P75/P80 (umbral P75 del percentil de vol).

Criterio de promoción (Quinn): mejorar Sharpe neto o reducir >=20% max-DD,
robusto en TODOS los umbrales (no overfit a uno).

Uso: python work/estrategias/vol_gate_test.py
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

UNIVERSE = "sp500_liquid"
MOM_W = 120
TOPK = 30
START = "2018-01-01"
END = "2026-08-01"

IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

IOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, IOD)
import vol_gate as vg


def run_backtest(sig_series, name):
    """Corre el backtest Qlib de la señal dada y devuelve métricas."""
    from qlib.backtest import backtest
    strategy = {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {"signal": sig_series, "topk": TOPK, "n_drop": 5,
                   "only_tradable": True, "hold_thresh": 20},
    }
    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
    }
    report, indicator = backtest(
        start_time="2022-01-01", end_time="2026-08-07",
        strategy=strategy, executor=executor,
        benchmark="^NDX", account=100000, exchange_kwargs=IB,
    )
    freq_key = list(report.keys())[0]
    df = report[freq_key][0]
    pv = df["account"].values
    port_ret = pd.Series(pv).pct_change().dropna().values
    mean_ann = float(np.mean(port_ret)) * 52
    vol = float(np.std(port_ret)) * np.sqrt(52)
    sharpe = mean_ann / vol if vol else np.nan
    cum = np.cumprod(1 + port_ret)
    dd = cum / np.maximum.accumulate(cum) - 1
    maxdd = float(dd.min())
    # turnover aprox (cambio en el número de posiciones)
    return {"name": name, "sharpe": sharpe, "maxdd": maxdd, "anual": mean_ann}


def main():
    from qlib.data import D as _D
    tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)
    close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
    close = close["$close"].unstack(level=0).sort_index()

    mom = close / close.shift(MOM_W) - 1
    print(f"Momentum: {mom.shape}")

    # Convertir a Series Qlib (MultiIndex datetime, instrument) — la señal base
    def to_qlib(sig_df):
        s = sig_df.stack().dropna()
        s = s.reset_index()
        s.columns = ["datetime", "instrument", "signal"] if s.shape[1] == 3 else s.columns
        s["datetime"] = pd.to_datetime(s["datetime"])
        return s.set_index(["datetime", "instrument"])["signal"].sort_index()

    # mercado para vol-gate (promedio del universo)
    market = close.mean(axis=1)

    results = []
    # Momentum puro (gate=1)
    base_sig = to_qlib(mom)
    results.append(run_backtest(base_sig, "momentum puro"))

    # Momentum + gate en el grid
    for p75, p90 in [(0.70, 0.85), (0.75, 0.90), (0.80, 0.95)]:
        gate = vg.gate_series_gated(market, p75=p75, p90=p90)
        # multiplicar la señal por el gate (alineado por fecha)
        gate_col = gate.reindex(close.index).ffill().fillna(1.0)
        sig_gated = mom.multiply(gate_col, axis=0)
        sig_s = to_qlib(sig_gated)
        results.append(run_backtest(sig_s, f"mom+gate P{int(p75*100)}"))

    # ---- Tabla ----
    print("\n" + "="*60)
    print("VOL-GATE TEST (motor Qlib): momentum puro vs momentum + gate")
    print("="*60)
    print(f"{'Estrategia':18}{'Sharpe':>8}{'MaxDD':>9}{'Anual':>9}")
    print("-"*60)
    for r in results:
        print(f"{r['name']:18}{r['sharpe']:>8.3f}{r['maxdd']:>9.1%}{r['anual']:>9.1%}")

    # ---- Criterio de promoción ----
    base = results[0]
    gates = results[1:]
    mej_sharpe = sum(1 for r in gates if r["sharpe"] > base["sharpe"])
    mej_dd = sum(1 for r in gates if r["maxdd"] <= base["maxdd"] * 0.80)
    print("\nCRITERIO DE PROMOCIÓN (Quinn):")
    print(f"  Gates que mejoran Sharpe:  {mej_sharpe}/{len(gates)}")
    print(f"  Gates que reducen ≥20% DD: {mej_dd}/{len(gates)}")
    if mej_sharpe == len(gates) or mej_dd == len(gates):
        print("  ✅ ROBUSTO → promover vol-gating")
    elif mej_sharpe > len(gates) / 2:
        print("  ⚠️ Mejora parcial → promover con cautela")
    else:
        print("  ❌ No robusto → no promover (usar rule simple sola)")


if __name__ == "__main__":
    main()
