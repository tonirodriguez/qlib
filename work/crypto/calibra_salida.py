"""calibra_salida.py — Calibra la SALIDA del régimen-switch v2.

Barre la clave de salida por TENDENCIA ROTA (under_ma_days) combinada con exit_dd=0.30
(ATH global), reportando edge vs USDT en las 4 ventanas. Objetivo: proteger GIRO 2022
(crash) y BASE 2025 (declive lento) SIN sacrificar BULL 2021 y RALLY 2024.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np  # noqa
import pandas as pd  # noqa

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


def eval_window(price, start, end, under_ma_days, ma_win=75, exit_dd=0.30):
    p = price[(price.index >= pd.Timestamp(start, tz="UTC")) & (price.index <= pd.Timestamp(end, tz="UTC"))]
    sig = regime_signal_v2(p, vital_dd=0.30, exit_dd=exit_dd, ma_win=ma_win, under_ma_days=under_ma_days)
    val, n_trades, _ = simulate_switch(p, sig, initial_usd=INITIAL_USD)
    ret = (val / INITIAL_USD - 1) * 100
    usdt = ((1 + CASH_YIELD_APY) ** (len(p) / 365.0) - 1) * 100
    return {"ret": round(ret, 1), "edge": round(ret - usdt, 1), "trades": n_trades, "long": int(sig.sum())}


def main():
    price = load_proxy()
    header = " | ".join(f"{n:<16}" for n in WINDOWS)
    print(f"{'underMA':<8}| {header}")
    print("(formato: ret/edge-a-USDT/tr/trades/L-long)"
          "  [exit_dd=0.30, ma_win=75, vital_dd=0.30]")
    for umd in (3, 5, 7, 10, 15, 20, 30):
        cells = []
        for _, (s, e) in WINDOWS.items():
            r = eval_window(price, s, e, umd)
            cells.append(f"ret{r['ret']:>6}/e{r['edge']:>+5}/tr{r['trades']:>3}/L{r['long']:>3}")
        print(f"{umd:<8}| " + " | ".join(f"{c:<20}" for c in cells))


if __name__ == "__main__":
    main()