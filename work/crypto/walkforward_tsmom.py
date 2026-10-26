#!/usr/bin/env python3
"""walkforward_tsmom.py — ¿Aguanta el trend following fuera del último ciclo?

Evalúa TSMOM20 con vol targeting 25% y 40% año a año sobre 2015-2026, con la
señal calculada siempre con datos hasta t-1 (causal) y coste de 10 pb por
operación sobre el turnover. Compara con BTC buy & hold en cada año y en
ventanas móviles de 3 años.

No hay reentrenamiento: la regla es fija. Lo que se mide es la estabilidad del
resultado entre regímenes, no la capacidad de ajustar parámetros al pasado.

Uso: python walkforward_tsmom.py
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
from crypto.backtest_tsmom_vs_sfm import trend_signal, run_long_cash, vol_target, COST
from crypto.research_utils import performance_metrics

OUT = Path(__file__).resolve().parent / "output" / "sfm_v8"
OUT.mkdir(parents=True, exist_ok=True)
TRADING_DAYS = 365


def stats(ret: np.ndarray) -> dict:
    r = np.nan_to_num(np.asarray(ret, dtype=float))
    if len(r) < 2 or r.std() == 0:
        return {"ret_pct": 0.0, "sharpe": float("nan"), "dd_pct": 0.0, "n": len(r)}
    eq = np.cumprod(1 + r)
    dd = float(np.min(eq / np.maximum.accumulate(eq) - 1))
    return {
        "ret_pct": round((eq[-1] - 1) * 100, 2),
        "sharpe": round(float(r.mean() / r.std() * np.sqrt(TRADING_DAYS)), 2),
        "dd_pct": round(dd * 100, 1),
        "n": len(r),
    }


def main() -> int:
    print("Cargando datos crudos desde Qlib...")
    prices = load_raw(CRYPTOS, START_DATE, END_DATE).dropna(how="all").ffill()
    print(f"  {prices.shape[0]} filas x {prices.shape[1]} coins | "
          f"{prices.index[0].date()} -> {prices.index[-1].date()}")

    rets = prices.pct_change().fillna(0.0)
    btc = rets["btc"]

    sig20 = trend_signal(prices, 20)
    net, turnover = run_long_cash(prices, sig20)
    net25, lev25 = vol_target(net.to_numpy(), 0.25)
    net40, lev40 = vol_target(net.to_numpy(), 0.40)

    s25 = pd.Series(net25, index=prices.index)
    s40 = pd.Series(net40, index=prices.index)

    years = sorted({d.year for d in prices.index})
    # el primer año completo con historia suficiente para vol targeting
    years = [y for y in years if y >= 2016]

    rows = []
    for y in years:
        mask = prices.index.year == y
        if mask.sum() < 60:
            continue
        a = stats(s25[mask].to_numpy())
        b = stats(s40[mask].to_numpy())
        c = stats(btc[mask].to_numpy())
        rows.append({
            "year": y,
            "tsmom25_ret_pct": a["ret_pct"], "tsmom25_sharpe": a["sharpe"],
            "tsmom25_dd_pct": a["dd_pct"],
            "tsmom40_ret_pct": b["ret_pct"], "tsmom40_sharpe": b["sharpe"],
            "tsmom40_dd_pct": b["dd_pct"],
            "btc_ret_pct": c["ret_pct"], "btc_sharpe": c["sharpe"],
            "btc_dd_pct": c["dd_pct"],
            "beat_btc": a["ret_pct"] > c["ret_pct"],
        })

    print(f"\n{'='*96}")
    print(f"{'año':>5} {'TSM25%':>9} {'Sh':>5} {'DD%':>7} | "
          f"{'TSM40%':>9} {'Sh':>5} {'DD%':>7} | {'BTC':>9} {'Sh':>5} {'DD%':>7} | gana")
    print("=" * 96)
    for r in rows:
        print(f"{r['year']:>5} {r['tsmom25_ret_pct']:>8.1f}% {r['tsmom25_sharpe']:>5.2f} "
              f"{r['tsmom25_dd_pct']:>6.1f}% | {r['tsmom40_ret_pct']:>8.1f}% "
              f"{r['tsmom40_sharpe']:>5.2f} {r['tsmom40_dd_pct']:>6.1f}% | "
              f"{r['btc_ret_pct']:>8.1f}% {r['btc_sharpe']:>5.2f} {r['btc_dd_pct']:>6.1f}% | "
              f"{'sí' if r['beat_btc'] else 'NO'}")

    # ── agregados ────────────────────────────────────────────────────
    mask_all = prices.index.year >= 2016
    full25 = stats(s25[mask_all].to_numpy())
    full40 = stats(s40[mask_all].to_numpy())
    fullbtc = stats(btc[mask_all].to_numpy())
    wins = sum(r["beat_btc"] for r in rows)

    print("\n" + "=" * 96)
    print(f"PERIODO COMPLETO 2016-2026 ({mask_all.sum()} sesiones)")
    print(f"  TSMOM20-vol25 : {full25['ret_pct']:>8.1f}% acumulado | Sharpe {full25['sharpe']:.2f} "
          f"| DD {full25['dd_pct']:.1f}%")
    print(f"  TSMOM20-vol40 : {full40['ret_pct']:>8.1f}% acumulado | Sharpe {full40['sharpe']:.2f} "
          f"| DD {full40['dd_pct']:.1f}%")
    print(f"  BTC buy & hold: {fullbtc['ret_pct']:>8.1f}% acumulado | Sharpe {fullbtc['sharpe']:.2f} "
          f"| DD {fullbtc['dd_pct']:.1f}%")
    print(f"  años batiendo a BTC: {wins}/{len(rows)}")

    # ── ventanas móviles de 3 años ──────────────────────────────────
    roll = []
    for start in years:
        end = start + 2
        if end not in years:
            continue
        m = (prices.index.year >= start) & (prices.index.year <= end)
        a = stats(s25[m].to_numpy())
        c = stats(btc[m].to_numpy())
        roll.append({"window": f"{start}-{end}", "tsmom25_ret_pct": a["ret_pct"],
                     "tsmom25_sharpe": a["sharpe"], "tsmom25_dd_pct": a["dd_pct"],
                     "btc_ret_pct": c["ret_pct"], "beat_btc": a["ret_pct"] > c["ret_pct"]})

    print(f"\n{'='*60}\nVENTANAS MÓVILES DE 3 AÑOS\n{'='*60}")
    for r in roll:
        print(f"  {r['window']}  TSM {r['tsmom25_ret_pct']:>7.1f}%  Sharpe {r['tsmom25_sharpe']:>5.2f}"
              f"  DD {r['tsmom25_dd_pct']:>6.1f}%  |  BTC {r['btc_ret_pct']:>7.1f}%  "
              f"{'gana' if r['beat_btc'] else 'pierde'}")

    out = {
        "window": {"start": "2016-01-01", "end": str(prices.index[-1].date())},
        "cost_one_way": COST,
        "by_year": rows,
        "full_period": {"tsmom25": full25, "tsmom40": full40, "btc": fullbtc,
                        "years_beat_btc": wins, "n_years": len(rows)},
        "rolling_3y": roll,
    }
    path = OUT / "walkforward_tsmom_results.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"\nresultados en {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
