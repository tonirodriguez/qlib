#!/usr/bin/env python3
"""walkforward_leverage_regime.py — ¿Compensa apalancar el TSMOM? ¿Y filtrar régimen?

Prueba el TSMOM20 long/cash con objetivos de volatilidad 25/40/60/80%, con y sin
filtro de régimen (BTC por encima de su media de 200 días, decidido con datos
hasta t-1). Sobre 2015-2026, año a año, con coste de 10 pb por operación y
coste de financiación del 8% anual sobre el apalancamiento por encima de 1x.

Sin reentrenamiento: todas las reglas son fijas y causales.

Uso: python walkforward_leverage_regime.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crypto.exp_causal_leak import CRYPTOS, START_DATE, END_DATE, load_raw
from crypto.backtest_tsmom_vs_sfm import trend_signal, run_long_cash, COST

OUT = Path(__file__).resolve().parent / "output" / "sfm_v8"
OUT.mkdir(parents=True, exist_ok=True)
DAYS = 365
FIN_RATE = 0.08          # coste anual de financiar el apalancamiento > 1x
VOL_WINDOW = 60


def lever_series(net: np.ndarray, target: float, regime: np.ndarray | None,
                 fin_rate: float = FIN_RATE):
    """Aplica vol targeting (y opcionalmente régimen) con financiación.

    - La volatilidad se estima con datos hasta t-1 (causal).
    - El apalancamiento se recorta a [0, 2]: máximo 2x.
    - Se cobra financiación sobre la parte que excede 1x.
    """
    s = pd.Series(net)
    rv = s.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(DAYS)
    lev = (target / rv).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(0.0, 2.0)
    if regime is not None:
        lev = lev * pd.Series(regime, index=s.index)
    lev = lev.to_numpy()
    fin = fin_rate / DAYS * np.maximum(lev - 1.0, 0.0)
    return lev * net - fin, lev


def stats(r: np.ndarray) -> dict:
    r = np.nan_to_num(np.asarray(r, dtype=float))
    if len(r) < 2 or r.std() == 0:
        return {"ret_pct": 0.0, "cagr_pct": 0.0, "sharpe": float("nan"),
                "dd_pct": 0.0, "calmar": 0.0, "t": float("nan"), "n": len(r)}
    eq = np.cumprod(1 + r)
    dd = float(np.min(eq / np.maximum.accumulate(eq) - 1))
    cagr = float(eq[-1] ** (DAYS / len(r)) - 1)
    return {
        "ret_pct": round((eq[-1] - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(float(r.mean() / r.std() * np.sqrt(DAYS)), 2),
        "dd_pct": round(dd * 100, 1),
        "calmar": round(cagr / (abs(dd) + 1e-9), 2),
        "t": round(float(r.mean() / r.std() * np.sqrt(len(r))), 2),
        "n": len(r),
    }


def main() -> int:
    prices = load_raw(CRYPTOS, START_DATE, END_DATE).dropna(how="all").ffill()
    rets = prices.pct_change().fillna(0.0)
    print(f"{prices.shape[0]} filas x {prices.shape[1]} coins | "
          f"{prices.index[0].date()} -> {prices.index[-1].date()}")

    sig = trend_signal(prices, 20)
    net, turnover = run_long_cash(prices, sig)
    net_a = net.to_numpy()

    # Régimen: BTC > SMA200, con decisión tomada a cierre de t-1
    btc_px = prices["btc"]
    btc_rets = rets["btc"]
    sma200 = btc_px.rolling(200).mean()
    regime = (btc_px > sma200).astype(float).shift(1).fillna(0.0).to_numpy()

    variants = [
        ("TSMOM20-vol25", 0.25, False),
        ("TSMOM20-vol40", 0.40, False),
        ("TSMOM20-vol60", 0.60, False),
        ("TSMOM20-vol80", 0.80, False),
        ("TSMOM20-vol25-reg", 0.25, True),
        ("TSMOM20-vol40-reg", 0.40, True),
        ("TSMOM20-vol60-reg", 0.60, True),
        ("TSMOM20-vol80-reg", 0.80, True),
    ]

    results = []
    series = {}
    for name, target, use_reg in variants:
        r, lev = lever_series(net_a, target, regime if use_reg else None)
        series[name] = pd.Series(r, index=prices.index)
        st = stats(r[r_mask := (prices.index.year >= 2016)])
        st["strategy"] = name
        st["avg_lev"] = round(float(np.nanmean(lev[prices.index.year >= 2016])), 2)
        st["max_lev"] = round(float(np.nanmax(lev)), 2)
        results.append(st)

    btc_stats = stats(btc_rets[btc_rets.index.year >= 2016].to_numpy())
    btc_stats["strategy"] = "BTC-BH"
    btc_stats["avg_lev"] = 1.0
    btc_stats["max_lev"] = 1.0
    results.append(btc_stats)

    print(f"\n{'='*104}")
    print(f"{'estrategia':<22} {'equity':>9} {'CAGR':>7} {'Sharpe':>7} {'DD%':>7} "
          f"{'Calmar':>7} {'t':>6} {'lev med':>8} {'años>BTC':>9}")
    print("=" * 104)
    for r in results:
        wins = sum(
            1 for y in sorted({d.year for d in prices.index})
            if y >= 2016 and stats(series.get(r["strategy"], pd.Series(dtype=float))[prices.index.year == y].to_numpy())["ret_pct"]
            > stats(btc_rets[btc_rets.index.year == y].to_numpy())["ret_pct"]
        ) if r["strategy"] in series else None
        w = f"{wins}/11" if wins is not None else "-"
        print(f"{r['strategy']:<22} {r['ret_pct']/100:>8.2f}x {r['cagr_pct']:>6.1f}% "
              f"{r['sharpe']:>7.2f} {r['dd_pct']:>6.1f}% {r['calmar']:>7.2f} "
              f"{r['t']:>+6.2f} {r['avg_lev']:>8.2f} {w:>9}")
    print("=" * 104)
    print(f"coste 10 pb por operación; financiación {FIN_RATE*100:.0f}% anual sobre lev>1; "
          f"apalancamiento máximo 2x")

    # detalle anual de las dos variantes de interés
    print(f"\n{'='*80}\nDETALLE ANUAL: vol25 vs vol60-reg vs BTC\n{'='*80}")
    print(f"{'año':>5} {'vol25':>9} {'vol60-reg':>11} {'BTC':>9} {'lev60reg':>9}")
    for y in sorted({d.year for d in prices.index}):
        if y < 2016:
            continue
        m = prices.index.year == y
        if m.sum() < 60:
            continue
        a = stats(series["TSMOM20-vol25"][m].to_numpy())["ret_pct"]
        b = stats(series["TSMOM20-vol60-reg"][m].to_numpy())["ret_pct"]
        c = stats(btc_rets[m].to_numpy())["ret_pct"]
        lev = series["TSMOM20-vol60-reg"][m]
        print(f"{y:>5} {a:>8.1f}% {b:>10.1f}% {c:>8.1f}%")

    path = OUT / "walkforward_leverage_regime_results.json"
    with open(path, "w") as f:
        json.dump({"cost_one_way": COST, "fin_rate": FIN_RATE,
                   "variants": results}, f, indent=2,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"\nresultados en {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
