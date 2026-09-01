"""
compare_top1_vs_multicur.py — Diagnostico: aislar por que el backtest no coincide con el training.

El training (top_k_results.json) reportaba Sharpe 2.74 con top1_long_returns SIN costes.
El backtest que hicimos opera multi-monedas CON costes.
Aqui evaluamos, sobre LAS MISMAS predicciones causales de 2025-01-01 -> 2026-08-30:

  A) top-1 long CON costes Binance   <- misma estrategia que el training, pero con costes
  B) multi-monedas (paper) CON costes <- el backtest ya hecho

Asi se ve si la diferencia vs el training es por (1) los costes, o (2) el modo multi-monedas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

import backtest_v8_2025 as bt  # noqa: E402
from research_utils import top1_long_returns, performance_metrics  # noqa: E402

CRYPTOS = bt.CRYPTOS
START = bt.START
END = bt.END
LOOKBACK = bt.MODEL_PARAMS["lookback"]

# Costes Binance usados en el backtest (fee + spread + slippage one-way)
COST = bt.TRANSACTION_COST + bt.HALF_SPREAD + bt.SLIPPAGE
BINANCE_COSTS = {
    "transaction_cost": bt.TRANSACTION_COST,
    "half_spread": bt.HALF_SPREAD,
    "slippage": bt.SLIPPAGE,
}


def main():
    from qlib.config import REG_US
    import qlib
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)

    df_close = bt.load_closes()
    model = bt.load_model()

    # Generar predicciones causales (igual que el backtest)
    pred_days, pred_list = [], []
    all_days = list(df_close.index)
    for i in range(LOOKBACK + 25, len(all_days)):
        day = all_days[i]
        if day < pd.Timestamp(START):
            continue
        if day > pd.Timestamp(END):
            break
        window = df_close.loc[:day]
        if len(window) < LOOKBACK + 5:
            continue
        matrix = bt.build_features_matrix(window)
        from research_utils import fit_clip_bounds, apply_clip_bounds
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scaler = __import__("sklearn.preprocessing", fromlist=["MinMaxScaler"]).MinMaxScaler(feature_range=(-1, 1))
        scaled = scaler.fit_transform(matrix)
        x = torch.tensor(scaled[-LOOKBACK:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred = model(x).numpy()[0]
        pred_days.append(day); pred_list.append(pred)

    dates = pred_days
    preds = np.array(pred_list)
    print(f"Predicciones: {len(dates)} dias ({dates[0].date()} -> {dates[-1].date()})")

    # Retornos realizados a t+1 por moneda
    ret_idx = df_close.pct_change()
    ret_matrix = np.zeros((len(dates), len(CRYPTOS)))
    for r, day in enumerate(dates):
        pos = df_close.index.get_loc(day) + 1
        if pos < len(df_close):
            for c_i, cname in enumerate(CRYPTOS):
                prev = df_close.iloc[pos - 1][cname.upper()]
                cur = df_close.iloc[pos][cname.upper()]
                ret_matrix[r, c_i] = (cur - prev) / prev if prev and prev == prev else 0.0

    # ---- A) top-1 CON costes ---- (misma estrategia que el training pero con costes)
    net_top1, pos_top1 = top1_long_returns(preds, ret_matrix, **BINANCE_COSTS)
    m_top1 = performance_metrics(net_top1)
    equity_top1 = bt.INITIAL_CAPITAL_USD * np.cumprod(1.0 + net_top1)
    final_usd_top1 = float(equity_top1[-1])

    # ---- B) multi-monedas CON costes (el backtest del paper) ----
    curve, opers, _ti = bt.simulate_portfolio(dates, pred_list, df_close)
    vals = np.array([v for _, v in curve])
    rets = np.diff(vals) / vals[:-1] if len(vals) > 1 else np.array([0.0])
    rets = np.insert(rets, 0, vals[0] / bt.INITIAL_CAPITAL_USD - 1)
    m_multi = performance_metrics(rets)
    final_usd_multi = float(vals[-1])

    print("\n" + "=" * 64)
    print("DIAGNOSTICO: training (Sharpe 2.74, top-1 SIN costes) vs variantes CON costes")
    print("=" * 64)
    # Referencia del training (top_k_results.json, test 2024-11->2026-08, SIN costes)
    print(f"{'Variante':42s} {'Sharpe':>8s} {'Equity USD':>12s} {'Ret USD%':>9s}")
    print("-" * 64)
    print(f"{'Training reportado (top-1, SIN costes)':42s} {'2.74':>8s} {bt.INITIAL_CAPITAL_USD*20:>12,.0f} {'~1900':>9s}")
    print(f"{'A) top-1 CON costes (== training pero c/costes)':42s} {m_top1['sharpe']:>8.2f} {final_usd_top1:>12,.0f} {(final_usd_top1/bt.INITIAL_CAPITAL_USD-1)*100:>8.1f}%")
    print(f"{'B) multi-moneda CON costes (el backtest del paper)':42s} {m_multi['sharpe']:>8.2f} {final_usd_multi:>12,.0f} {(final_usd_multi/bt.INITIAL_CAPITAL_USD-1)*100:>8.1f}%")
    print("-" * 64)
    print(f"coste one-way: {COST*100:.2f}%  |  operaciones top-1: {int((pos_top1[1:]!=pos_top1[:-1]).sum())}  |  operaciones multi: {len(opers)}")

    result = {
        "diagnostico": "top-1 CON costes (igual estrategia que training, pero costes Binance)",
        "top1": {
            "sharpe": round(m_top1["sharpe"], 3),
            "equity_final_usd": round(final_usd_top1, 2),
            "return_pct_usd": round((final_usd_top1 / bt.INITIAL_CAPITAL_USD - 1) * 100, 2),
            "max_drawdown_pct": round(m_top1["max_drawdown"] * 100, 2),
            "n_trades": int((pos_top1[1:] != pos_top1[:-1]).sum()),
        },
        "multi_moneda_con_costes": {
            "sharpe": round(m_multi["sharpe"], 3),
            "equity_final_usd": round(final_usd_multi, 2),
            "return_pct_usd": round((final_usd_multi / bt.INITIAL_CAPITAL_USD - 1) * 100, 2),
            "max_drawdown_pct": round(m_multi["max_drawdown"] * 100, 2),
            "n_trades": len(opers),
        },
        "referencia_training": {"sharpe": 2.74, "estrategia": "top-1 SIN costes", "equity_final": "20x"},
        "coste_one_way_pct": round(COST * 100, 3),
        "periodo": f"{dates[0].date()} -> {dates[-1].date()}",
    }
    out = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "diagnostico_top1_vs_multi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("\nGuardado:", out)


if __name__ == "__main__":
    main()