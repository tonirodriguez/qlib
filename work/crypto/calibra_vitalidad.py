"""calibra_vitalidad.py — Barrido del umbral de vitalidad del régimen-switch v2.

Evalúa regime_switch_v2 en 4 ventanas para distintos vital_dd, reportando edge vs USDT.
Objetivo: que la capa de vitalidad capture el bull ruidoso 2021 SIN perder el giro 2022.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from regime_switch_v2 import (  # noqa: E402
    CASH_YIELD_APY, INITIAL_USD, load_proxy, regime_signal_v2, simulate_switch,
)

WINDOWS = {
    "sel_bull2021": ("2020-11-01", "2021-11-30"),
    "sel_giro2022": ("2021-06-01", "2022-12-31"),
    "oos_rally2024": ("2024-01-01", "2024-12-31"),
    "oos_base2025": ("2025-01-01", "2026-08-30"),
}


def eval_window(price, start, end, vital_dd):
    p = price[(price.index >= pd.Timestamp(start, tz="UTC")) & (price.index <= pd.Timestamp(end, tz="UTC"))]
    sig = regime_signal_v2(p, vital_dd=vital_dd)
    val, n_trades, _ = simulate_switch(p, sig)
    ret = (val / INITIAL_USD - 1) * 100
    usdt = ((1 + CASH_YIELD_APY) ** (len(p) / 365.0) - 1) * 100
    days_long = int(sig.sum())
    return {"ret": round(ret, 1), "usdt": round(usdt, 1), "edge": round(ret - usdt, 1),
            "trades": n_trades, "dias_long": days_long, "dias": len(p)}


def main():
    price = load_proxy()
    header = " | ".join(f"{n:<14}" for n in WINDOWS)
    print(f"{'vital_dd':<9}| {header}")
    for vd in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        cells = []
        for name, (s, e) in WINDOWS.items():
            r = eval_window(price, s, e, vd)
            cells.append(f"ret{r['ret']:>6}/e{r['edge']:>5}/tr{r['trades']:>3}")
        print(f"{vd:<9}| " + " | ".join(f"{c:<14}" for c in cells))

    # Mejor por edge promedio OOS
    best = None
    for vd in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        edges = [eval_window(price, s, e, vd)["edge"] for _, (s, e) in WINDOWS.items()]
        score = sum(edges)  # sumar edges a USDT
        if best is None or score > best["score"]:
            best = {"vital_dd": vd, "score": round(score, 1), "edges": {n: eval_window(price, s, e, vd)["edge"] for n, (s, e) in WINDOWS.items()}}
    print(f"\nMEJOR por suma de edges: vital_dd={best['vital_dd']} (score {best['score']})")
    for n, e in best["edges"].items():
        print(f"   {n}: edge={e}")


if __name__ == "__main__":
    main()