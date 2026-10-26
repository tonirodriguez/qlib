#!/usr/bin/env python3
"""simulate_realistic.py — simulador diario con liquidación y régimen ampliado.

Diferencias frente al backtest vectorizado anterior:
  - Se recorre día a día y se comprueba liquidación: si el retorno diario de la
    posición apalancada llega a -100%, la cuenta se da por perdida y se detiene.
  - El filtro de régimen puede ser BTC>SMA200 o amplitud del mercado (fracción
    de monedas por encima de su media de 50 días).
  - Los costes se cargan sobre el turnover real de la posición apalancada.

Variantes: vol40/vol60 con régimen BTC y con amplitud. Comparación contra BTC.

Uso: python simulate_realistic.py
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

OUT = Path(__file__).resolve().parent / "output" / "sfm_v8"
OUT.mkdir(parents=True, exist_ok=True)
DAYS = 365
COST = 0.001
FIN_RATE = 0.08
VOL_WINDOW = 60
MAX_LEV = 2.0


def build_regime(prices: pd.DataFrame, kind: str) -> np.ndarray:
    """Multiplicador de exposición 0/1, decidido con datos hasta t-1."""
    if kind == "btc":
        px = prices["btc"]
        ma = px.rolling(200).mean()
        r = (px > ma).astype(float)
    elif kind == "breadth":
        ma50 = prices.rolling(50).mean()
        r = (prices > ma50).sum(axis=1) / prices.shape[1]
        r = (r >= 0.5).astype(float)
    elif kind == "none":
        return np.ones(len(prices))
    else:
        raise ValueError(kind)
    return r.shift(1).fillna(0.0).to_numpy()


def simulate(prices: pd.DataFrame, rets: pd.DataFrame, target: float,
             regime: np.ndarray, cost: float = COST, fin_rate: float = FIN_RATE):
    """Simulación diaria con liquidación. Devuelve retornos netos por día."""
    n = len(prices)
    equity = 1.0
    rets_out = np.zeros(n)
    pos_prev = np.zeros(prices.shape[1])
    liquidated = False
    liq_day = None

    # señal TSMOM20 calculada con datos hasta t (se aplica desde t+1)
    mom = (prices / prices.shift(20) - 1.0) > 0
    mom = mom.fillna(False).to_numpy()
    px = prices.to_numpy()
    rr = rets.replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy()

    unlev_hist = []   # retornos de la cartera SIN apalancar, para estimar vol
    for t in range(21, n - 1):
        if liquidated:
            rets_out[t + 1] = 0.0
            continue

        active = mom[t]
        if active.sum() == 0:
            base = np.zeros(prices.shape[1])
        else:
            base = active.astype(float) / active.sum()

        # volatilidad de la cartera subyacente con datos hasta t (rompe el
        # arranque en frío: no depende del apalancamiento aplicado)
        if len(unlev_hist) >= VOL_WINDOW:
            rv = np.std(unlev_hist[-VOL_WINDOW:]) * np.sqrt(DAYS)
            lev = 0.0 if not np.isfinite(rv) or rv <= 0 else min(target / rv, MAX_LEV)
        else:
            lev = 0.0

        pos = base * lev * regime[t]

        turnover = np.abs(pos - pos_prev).sum()
        fin = fin_rate / DAYS * max(pos.sum() - 1.0, 0.0)
        # P&L del día siguiente con la posición tomada hoy
        pnl = float(np.dot(pos, rr[t + 1])) - cost * turnover - fin
        unlev_hist.append(float(np.dot(base, rr[t + 1])))
        rets_out[t + 1] = pnl
        equity *= 1.0 + pnl
        pos_prev = pos

        if pnl <= -1.0 or equity <= 0:
            liquidated = True
            liq_day = str(prices.index[t + 1].date())
            equity = 0.0
            break

    return rets_out, liquidated, liq_day


def stats(r: np.ndarray, start_idx: int) -> dict:
    v = np.nan_to_num(r[start_idx:])
    if len(v) < 2 or v.std() == 0:
        return {"ret_pct": 0.0, "cagr_pct": 0.0, "sharpe": float("nan"),
                "dd_pct": 0.0, "calmar": 0.0, "t": float("nan")}
    eq = np.cumprod(1 + v)
    dd = float(np.min(eq / np.maximum.accumulate(eq) - 1))
    cagr = float(eq[-1] ** (DAYS / len(v)) - 1) if eq[-1] > 0 else -1.0
    return {
        "ret_pct": round((eq[-1] - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(float(v.mean() / v.std() * np.sqrt(DAYS)), 2),
        "dd_pct": round(dd * 100, 1),
        "calmar": round(cagr / (abs(dd) + 1e-9), 2),
        "t": round(float(v.mean() / v.std() * np.sqrt(len(v))), 2),
    }


def main() -> int:
    prices = load_raw(CRYPTOS, START_DATE, END_DATE).dropna(how="all").ffill()
    prices = prices.replace(0.0, np.nan).ffill()
    rets = prices.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    start = int(np.searchsorted(prices.index, pd.Timestamp("2016-01-01")))
    print(f"{prices.shape[0]} filas x {prices.shape[1]} coins | "
          f"{prices.index[0].date()} -> {prices.index[-1].date()}")

    regimes = {"none": build_regime(prices, "none"),
               "btc": build_regime(prices, "btc"),
               "breadth": build_regime(prices, "breadth")}

    variants = [
        ("vol40-none", 0.40, "none"),
        ("vol60-none", 0.60, "none"),
        ("vol40-btc", 0.40, "btc"),
        ("vol60-btc", 0.60, "btc"),
        ("vol40-breadth", 0.40, "breadth"),
        ("vol60-breadth", 0.60, "breadth"),
    ]

    rows = []
    for name, target, reg in variants:
        r, liq, liq_day = simulate(prices, rets, target, regimes[reg])
        st = stats(r, start)
        st.update({"strategy": name, "target": target, "regime": reg,
                   "liquidated": liq, "liq_day": liq_day})
        rows.append(st)

    btc_r = rets["btc"].to_numpy()
    st = stats(btc_r, start)
    st.update({"strategy": "BTC-BH", "target": 1.0, "regime": "none",
               "liquidated": False, "liq_day": None})
    rows.append(st)

    # años batiendo a BTC
    years = sorted({d.year for d in prices.index if d.year >= 2016})
    for row in rows:
        row["years_beat_btc"] = None
    for name, target, reg in variants:
        r, _, _ = simulate(prices, rets, target, regimes[reg])
        wins = 0
        for y in years:
            m = np.array([d.year == y for d in prices.index])
            a = np.nan_to_num(r[m])
            b = np.nan_to_num(btc_r[m])
            if len(a) > 2 and (np.cumprod(1 + a)[-1] > np.cumprod(1 + b)[-1]):
                wins += 1
        for row in rows:
            if row["strategy"] == name:
                row["years_beat_btc"] = wins

    print(f"\n{'='*100}")
    print(f"{'estrategia':<18} {'equity':>9} {'CAGR':>7} {'Sharpe':>7} {'DD%':>7} "
          f"{'Calmar':>7} {'t':>6} {'años>BTC':>9} {'liquidada':>10}")
    print("=" * 100)
    for r in rows:
        w = f"{r['years_beat_btc']}/11" if r["years_beat_btc"] is not None else "-"
        print(f"{r['strategy']:<18} {r['ret_pct']/100:>8.2f}x {r['cagr_pct']:>6.1f}% "
              f"{r['sharpe']:>7.2f} {r['dd_pct']:>6.1f}% {r['calmar']:>7.2f} "
              f"{r['t']:>+6.2f} {w:>9} {('sí ' + str(r['liq_day'])) if r['liquidated'] else 'no':>10}")
    print("=" * 100)
    print("simulación diaria con comprobación de liquidación; coste 10 pb por operación")

    path = OUT / "simulate_realistic_results.json"
    with open(path, "w") as f:
        json.dump({"cost_one_way": COST, "fin_rate": FIN_RATE, "max_lev": MAX_LEV,
                   "rows": rows}, f, indent=2,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"\nresultados en {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
