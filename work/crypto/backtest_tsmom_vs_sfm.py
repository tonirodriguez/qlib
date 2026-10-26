#!/usr/bin/env python3
"""backtest_tsmom_vs_sfm.py — Trend following honesto vs SFM v8 vs buy & hold.

Misma ventana de test, mismo universo y mismos costes que exp_causal_leak.py:
  - 9 cryptos de Qlib, 2015-01-01 -> 2026-10-25
  - split 60/20/20 (train/val/test) idéntico
  - coste 10 pb por operación (una vía), cargado sobre el turnover real

Estrategias evaluadas SOLO en el test (nunca vistos):
  TSMOM20   long/cash por moneda si retorno 20d > 0, EW entre activas,
            vol targeting 25% anualizado con datos hasta t-1
  TSMOM50   ídem con media de 50 días (precio > MA50)
  TSMOM20-40 mismo TSMOM20 con objetivo de volatilidad 40%
  BTC-BH    buy & hold BTC
  EW-BH     buy & hold equiponderado de las 9 monedas

Uso: python backtest_tsmom_vs_sfm.py
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
from crypto.research_utils import performance_metrics

OUT = Path(__file__).resolve().parent / "output" / "sfm_v8"
OUT.mkdir(parents=True, exist_ok=True)
COST = 0.001          # 10 pb una vía
TARGET_VOL = 0.25
TARGET_VOL_HI = 0.40
VOL_WINDOW = 60
TRADING_DAYS = 365


def trend_signal(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """+1 si el retorno de `lookback` días es positivo, 0 si no."""
    ret = prices / prices.shift(lookback) - 1.0
    sig = (ret > 0).astype(float)
    sig[ret.isna()] = 0.0
    return sig


def run_long_cash(prices: pd.DataFrame, sig: pd.DataFrame, cost: float = COST):
    """Cartera long/cash equiponderada con coste sobre turnover.

    Devuelve retornos netos diarios y el turnover medio.
    """
    rets = prices.pct_change().fillna(0.0)
    n_active = sig.sum(axis=1).replace(0, np.nan)
    weights = sig.div(n_active, axis=0).fillna(0.0)      # EW entre activas
    gross = (weights.shift(1) * rets).sum(axis=1)        # señal en t-1 -> retorno t
    turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
    net = gross - cost * turnover
    return net, float(turnover.mean())


def vol_target(net: np.ndarray, target: float, window: int = VOL_WINDOW):
    """Escala la exposición para acercar la vol realizada al objetivo.

    La volatilidad se estima con datos hasta t-1 (causal) y el apalancamiento
    se recorta a [0, 1]: nunca se pide prestado.
    """
    s = pd.Series(net)
    rv = s.rolling(window).std().shift(1) * np.sqrt(TRADING_DAYS)
    lev = (target / rv).replace([np.inf, -np.inf], np.nan).clip(0.0, 1.0).fillna(0.0)
    return (s * lev).to_numpy(), lev.to_numpy()


def summarize(name: str, ret: np.ndarray, extra: dict | None = None) -> dict:
    m = performance_metrics(ret)
    r = np.nan_to_num(ret)
    t_stat = float(r.mean() / r.std() * np.sqrt(len(r))) if r.std() > 0 else float("nan")
    row = {
        "strategy": name,
        "equity": round(m["equity_final"], 3),
        "annual_pct": round(m["annualized_return"] * 100, 2),
        "sharpe": round(m["sharpe"], 3),
        "sortino": round(m["sortino"], 3),
        "max_dd_pct": round(m["max_drawdown"] * 100, 2),
        "calmar": round(m["calmar"], 3),
        "t_stat": round(t_stat, 2),
        "days": len(r),
    }
    if extra:
        row.update(extra)
    return row


def main() -> int:
    print("Cargando datos crudos desde Qlib...")
    prices = load_raw(CRYPTOS, START_DATE, END_DATE)
    prices = prices.dropna(how="all").ffill()
    print(f"  {prices.shape[0]} filas x {prices.shape[1]} coins")
    print(f"  {prices.index[0].date()} -> {prices.index[-1].date()}")

    n = len(prices)
    tr, va = int(n * 0.60), int(n * 0.80)
    test = prices.iloc[va:]
    print(f"  test: {test.index[0].date()} -> {test.index[-1].date()} ({len(test)} sesiones)")

    rows = []

    # ── TSMOM 20 y 50 ────────────────────────────────────────────────
    for lookback, target, label in [
        (20, TARGET_VOL, "TSMOM20-vol25"),
        (50, TARGET_VOL, "TSMOM50-vol25"),
        (20, TARGET_VOL_HI, "TSMOM20-vol40"),
    ]:
        # señal calculada con toda la serie; el recorte a test es posterior,
        # así que la señal en el primer día de test usa solo pasado (causal)
        sig = trend_signal(prices, lookback)
        net, turnover = run_long_cash(prices, sig)
        net_t = net.iloc[va:].to_numpy()
        net_v, lev = vol_target(net_t, target)
        active = (sig.iloc[va:].sum(axis=1) > 0).mean()
        rows.append(summarize(label, net_v, {
            "turnover_daily": round(turnover, 4),
            "pct_days_invested": round(float(active) * 100, 1),
            "avg_leverage": round(float(np.nanmean(lev)), 3),
        }))

    # ── Buy & hold ───────────────────────────────────────────────────
    rets = prices.pct_change().fillna(0.0)
    btc = rets["btc"].iloc[va:].to_numpy()
    ew = rets.mean(axis=1).iloc[va:].to_numpy()
    rows.append(summarize("BTC-BH", btc))
    rows.append(summarize("EW-BH", ew))

    # ── SFM v8 desde el JSON existente (misma ventana) ───────────────
    sfm_path = OUT / "exp_causal_leak_results.json"
    sfm = {}
    if sfm_path.exists():
        with open(sfm_path) as f:
            for r in json.load(f):
                sfm[r["variant"]] = r
        for v in ("A", "B", "C"):
            if v in sfm:
                r = sfm[v]
                rows.append({
                    "strategy": f"SFM-v8-{v}",
                    "equity": round(r["equity"], 3),
                    "annual_pct": None,
                    "sharpe": round(r["sharpe"], 2),
                    "max_dd_pct": round(r["max_dd_pct"], 1),
                    "t_stat": round(r["t_stat"], 2),
                    "ic_mean": round(r["ic_mean"], 4),
                    "days": r["n_test"],
                })

    print(f"\n{'='*92}")
    print(f"{'estrategia':<18} {'equity':>8} {'anual%':>8} {'Sharpe':>7} {'Sortino':>8} "
          f"{'DD%':>7} {'Calmar':>7} {'t-stat':>7}")
    print("=" * 92)
    for r in rows:
        ann = f"{r['annual_pct']:>7.2f}%" if r.get("annual_pct") is not None else "     n/d"
        print(f"{r['strategy']:<18} {r['equity']:>7.2f}x {ann} {r['sharpe']:>7.2f} "
              f"{r.get('sortino', float('nan')):>8.2f} {r['max_dd_pct']:>6.1f}% "
              f"{r.get('calmar', float('nan')):>7.2f} {r['t_stat']:>+7.2f}")
    print("=" * 92)
    print("coste 10 pb por operación, una vía; vol targeting recortado a [0,1]")
    print("SFM v8 anual% no disponible: el JSON guarda equity y Sharpe, no la serie")

    path = OUT / "tsmom_vs_sfm_results.json"
    with open(path, "w") as f:
        json.dump({"window": {"test_start": str(test.index[0].date()),
                              "test_end": str(test.index[-1].date()),
                              "sessions": len(test)},
                   "cost_one_way": COST,
                   "rows": rows}, f, indent=2)
    print(f"\nresultados en {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
