"""
sensibilidad_v8.py — Backtest de sensibilidad de la estrategia SFM v8.

Prueba combinaciones de ajustes sobre LAS MISMAS predicciones causales
(2025-01-01 -> 2026-08-30), todas CON costes Binance y CON yield del cash USDT:

  - umbral de entrada      (buy_threshold)
  - histeresis de salida    (sell_threshold < buy_threshold)
  - holding minimo          (min_holding_days)
  - numero de posiciones    (max_positions)

Genera las predicciones una sola vez y reutiliza simulate_portfolio con
distintos parametros. Guardo resultados en diagnostico_sensibilidad.json.

Uso: <python> work/crypto/sensibilidad_v8.py
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
from research_utils import performance_metrics  # noqa: E402
from research_utils import fit_clip_bounds, apply_clip_bounds  # noqa: E402
from sklearn.preprocessing import MinMaxScaler  # noqa: E402

START, END = bt.START, bt.END
LOOKBACK = bt.MODEL_PARAMS["lookback"]
YIELD = bt.CASH_YIELD_APY


def main():
    import qlib
    from qlib.config import REG_US
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)

    df_close = bt.load_closes()
    model = bt.load_model()

    # Generar predicciones causales UNA vez
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
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scaler = MinMaxScaler(feature_range=(-1, 1)); scaled = scaler.fit_transform(matrix)
        x = torch.tensor(scaled[-LOOKBACK:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred = model(x).numpy()[0]
        pred_days.append(day); pred_list.append(pred)
    print(f"Predicciones causales: {len(pred_days)} dias ({pred_days[0].date()} -> {pred_days[-1].date()})")

    # Configuraciones a probar
    configs = [
        # (nombre, buy_threshold, sell_threshold, min_holding, max_positions)
        # BASE replica el backtest original: compra score>0.025, vende score<0.015
        ("BASE (actual)",           0.025, 0.015, 0, 2),
        ("Histeresis sell=0.01",    0.025, 0.010, 0, 2),
        ("Histeresis sell=0.00",    0.025, 0.000, 0, 2),
        ("Histeresis sell=-0.01",   0.025, -0.010, 0, 2),
        ("Umbral sube a 0.04",      0.040, 0.015, 0, 2),
        ("Umbral sube a 0.06",      0.060, 0.015, 0, 2),
        ("Holding min 3d",          0.025, 0.015, 3, 2),
        ("Holding min 5d",          0.025, 0.015, 5, 2),
        ("Holding min 7d",          0.025, 0.015, 7, 2),
        ("Max posiciones 3",        0.025, 0.015, 0, 3),
        ("Max posiciones 4",        0.025, 0.015, 0, 4),
        ("Histeresis+Umbral+Hold",  0.040, 0.000, 3, 3),
        ("Hold 5d + histeresis",    0.035, 0.005, 5, 3),
    ]

    rows = []
    for name, buy, sell, hold, maxp in configs:
        curve, opers, interest = bt.simulate_portfolio(
            pred_days, pred_list, df_close,
            cash_yield_apy=YIELD,
            buy_threshold=buy,
            sell_threshold=sell,
            min_holding_days=hold,
            max_positions=maxp,
        )
        vals = np.array([v for _, v in curve])
        rets = np.diff(vals) / vals[:-1] if len(vals) > 1 else np.array([0.0])
        rets = np.insert(rets, 0, vals[0] / bt.INITIAL_CAPITAL_USD - 1)
        m = performance_metrics(rets)
        final_usd = float(vals[-1])
        ret_usd = (final_usd / bt.INITIAL_CAPITAL_USD - 1) * 100
        final_eur = final_usd / bt.EURUSD_END
        ret_eur = (final_eur / bt.INITIAL_CAPITAL_EUR - 1) * 100
        label_sell = sell if sell is not None else buy
        rows.append({
            "config": name,
            "buy_threshold": buy, "sell_threshold": label_sell,
            "min_holding_days": hold, "max_positions": maxp,
            "final_usd": round(final_usd, 2), "final_eur": round(final_eur, 2),
            "return_usd_pct": round(ret_usd, 2), "return_eur_pct": round(ret_eur, 2),
            "sharpe": round(m["sharpe"], 3), "sortino": round(m["sortino"], 3),
            "max_drawdown_pct": round(m["max_drawdown"] * 100, 2),
            "n_trades": len(opers), "interest_usd": round(interest, 2),
        })

    # Mostrar tabla ordenada por Sharpe
    print("\n" + "=" * 100)
    print(f"SENSIBILIDAD v8 (periodo {START} -> {END}, CON costes + yield {YIELD*100:.1f}% APY)")
    print("=" * 100)
    print(f"{'Config':28s} {'Buy':>6s} {'Sell':>6s} {'Hold':>5s} {'Pos':>4s} "
          f"{'RetUSD%':>8s} {'RetEUR%':>8s} {'Sharpe':>7s} {'MaxDD%':>7s} {'Trades':>6s}")
    print("-" * 100)
    for r in rows:
        sc = r["sell_threshold"] if r["sell_threshold"] is not None else r["buy_threshold"]
        print(f"{r['config']:28s} {r['buy_threshold']:6.3f} {sc:6.3f} {r['min_holding_days']:5d} "
              f"{r['max_positions']:4d} {r['return_usd_pct']:8.2f} {r['return_eur_pct']:8.2f} "
              f"{r['sharpe']:7.3f} {r['max_drawdown_pct']:7.2f} {r['n_trades']:6d}")

    # Mejor por Sharpe y por retorno
    best_sharpe = max(rows, key=lambda r: r["sharpe"])
    best_ret = max(rows, key=lambda r: r["return_usd_pct"])
    print("\n== Mejor por Sharpe:", best_sharpe["config"], f"({best_sharpe['sharpe']})")
    print("== Mejor por retorno USD:", best_ret["config"], f"({best_ret['return_usd_pct']}%)")

    # Guardar
    out = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "diagnostico_sensibilidad.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "periodo": f"{START} -> {END}",
        "costes_one_way_pct": round(bt.COST * 100, 3),
        "yield_apy": YIELD,
        "base": rows[0],
        "configs": rows,
        "best_sharpe": best_sharpe["config"],
        "best_return_usd": best_ret["config"],
    }, indent=2) + "\n", encoding="utf-8")
    print("\nGuardado:", out)


if __name__ == "__main__":
    main()