#!/usr/bin/env python3
"""chart_compare_tsmom.py — gráfico de comparación: dónde está la ventaja real.

Tres paneles:
  1. Capital de 10.000 € (escala logarítmica) — el resultado final
  2. Drawdown a lo largo del tiempo — donde se ve la diferencia de verdad
  3. Sharpe móvil de 12 meses — cuándo la estrategia aporta

Uso: python chart_compare_tsmom.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crypto.exp_causal_leak import CRYPTOS, START_DATE, END_DATE, load_raw
from crypto.simulate_realistic import simulate, build_regime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPORTS = Path("/opt/data/investments/reports")
CAPITAL = 10_000.0
DAYS = 365

SERIES = [("vol40-breadth", 0.40, "breadth", "#1f77b4"),
          ("vol60-breadth", 0.60, "breadth", "#2ca02c"),
          ("BTC buy & hold", None, None, "#ff7f0e")]


def drawdown(eq: np.ndarray) -> np.ndarray:
    return eq / np.maximum.accumulate(eq) - 1.0


def rolling_sharpe(r: np.ndarray, window: int = 252) -> np.ndarray:
    s = pd.Series(r)
    m = s.rolling(window).mean()
    sd = s.rolling(window).std()
    return (m / sd * np.sqrt(DAYS)).to_numpy()


def main() -> int:
    prices = load_raw(CRYPTOS, START_DATE, END_DATE).dropna(how="all").ffill()
    prices = prices.replace(0.0, np.nan).ffill()
    rets = prices.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    idx = prices.index
    start = int(np.searchsorted(idx, pd.Timestamp("2016-01-01")))
    reg_breadth = build_regime(prices, "breadth")

    data = {}
    for name, target, reg, color in SERIES:
        if name == "BTC buy & hold":
            r = rets["btc"].to_numpy()
        else:
            r, _, _ = simulate(prices, rets, target, reg_breadth)
        eq = np.cumprod(1 + np.nan_to_num(r[start:]))
        data[name] = {"r": np.nan_to_num(r[start:]), "eq": eq, "color": color}

    x = idx[start:]
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), dpi=140, sharex=True)

    ax = axes[0]
    for name, _, _, color in SERIES:
        ax.plot(x, data[name]["eq"] * CAPITAL, label=name, color=color, linewidth=1.8)
    ax.set_yscale("log")
    ax.set_title("1. Capital de 10.000 € a lo largo del tiempo", fontsize=12, fontweight="bold")
    ax.set_ylabel("Capital (€, log)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper left", fontsize=10)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:,.0f}".replace(",", ".") + " €"))
    for name, _, _, color in SERIES:
        ax.annotate(f"{data[name]['eq'][-1]*CAPITAL:,.0f} €".replace(",", "."),
                    xy=(x[-1], data[name]["eq"][-1] * CAPITAL), xytext=(6, 0),
                    textcoords="offset points", color=color, fontsize=9, va="center")

    ax = axes[1]
    for name, _, _, color in SERIES:
        ax.plot(x, drawdown(data[name]["eq"]) * 100, label=name, color=color, linewidth=1.5)
    ax.set_title("2. Drawdown: aquí está la diferencia real", fontsize=12, fontweight="bold")
    ax.set_ylabel("Caída desde máximos (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower left", fontsize=10)
    ax.axhline(-41.3, color="#1f77b4", ls=":", lw=1, alpha=0.6)

    ax = axes[2]
    for name, _, _, color in SERIES:
        ax.plot(x, rolling_sharpe(data[name]["r"]), label=name, color=color, linewidth=1.5)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("3. Sharpe móvil de 12 meses", fontsize=12, fontweight="bold")
    ax.set_ylabel("Sharpe (ventana 12m)")
    ax.set_xlabel("Fecha")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=10)

    fig.suptitle("TSMOM20 vs BTC · 2016-2026 · simulación diaria con costes",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    out = REPORTS / "crypto_tsmom_comparacion_paneles.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"grafico: {out}")
    for name, _, _, _ in SERIES:
        eq = data[name]["eq"]
        print(f"  {name:<16} final {eq[-1]*CAPITAL:>12,.0f} EUR | DD {drawdown(eq).min()*100:>6.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())