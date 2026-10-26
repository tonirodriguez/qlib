#!/usr/bin/env python3
"""paper_trading_tsmom.py — paper trading diario del TSMOM20 con régimen.

Estrategia seguida (nombrada en el informe de backtest):
  - vol40-breadth  (opción recomendada: objetivo de volatilidad 40% + amplitud)
  - vol60-breadth  (versión agresiva, mismo motor)

Cada día:
  1. Refresca los precios de cierre desde la API pública de Binance (sin key).
  2. Recalcula de forma determinista la curva de capital con los datos
     disponibles hasta hoy (sin usar información futura).
  3. Añade al libro de paper trading (`output/paper_trading/ledger.csv`) la fila
     nueva con capital, retorno del día y posiciones objetivo para el día
     siguiente.

Idempotente: si un día ya está en el libro, no se duplica.

Uso: python paper_trading_tsmom.py [--capital 10000] [--no-update]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crypto.exp_causal_leak import CRYPTOS, START_DATE, END_DATE, load_raw

OUT = Path(__file__).resolve().parent / "output" / "sfm_v8"
LEDGER_DIR = Path(__file__).resolve().parent / "output" / "paper_trading"
LEDGER_DIR.mkdir(parents=True, exist_ok=True)
LEDGER = LEDGER_DIR / "ledger.csv"
STATE = LEDGER_DIR / "state.json"

DAYS = 365
COST = 0.001
FIN_RATE = 0.08
VOL_WINDOW = 60
MAX_LEV = 2.0
STRATEGIES = [("vol40-breadth", 0.40, "breadth"), ("vol60-breadth", 0.60, "breadth")]
BINANCE = "https://api.binance.com/api/v3/klines"


def binance_closes(symbol: str, start_ms: int, end_ms: int) -> pd.Series:
    """Cierres diarios de Binance entre dos timestamps (ms)."""
    out = {}
    cur = start_ms
    while cur < end_ms:
        q = urllib.parse.urlencode({
            "symbol": symbol, "interval": "1d", "limit": 1000,
            "startTime": cur, "endTime": end_ms})
        with urllib.request.urlopen(f"{BINANCE}?{q}", timeout=20) as r:
            data = json.loads(r.read().decode())
        if not data:
            break
        for k in data:
            ts = pd.Timestamp(k[0], unit="ms").normalize()
            out[ts] = float(k[4])
        if len(data) < 1000:
            break
        cur = data[-1][0] + 86400000
    return pd.Series(out).sort_index()


def refresh_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Añade los cierres nuevos de Binance al histórico de Qlib."""
    last = df.index[-1]
    start_ms = int((last + pd.Timedelta(days=1)).tz_localize("UTC").timestamp() * 1000)
    # solo velas YA CERRADAS: el inicio de hoy UTC, no la vela en curso
    end_ms = int(pd.Timestamp.utcnow().normalize().timestamp() * 1000)
    if start_ms >= end_ms:
        print("  datos ya al día, sin refresco")
        return df
    added = 0
    for c in df.columns:
        try:
            s = binance_closes(f"{c.upper()}USDT", start_ms, end_ms)
        except Exception as e:  # red o símbolo no listado
            print(f"  ⚠️  {c}: no se pudo refrescar ({type(e).__name__})")
            continue
        if s.empty:
            continue
        s.index = s.index.tz_localize(None)
        s = s[s.index > last]
        for ts, px in s.items():
            df.loc[ts, c] = px
            added += 1
    print(f"  {added} cierres nuevos añadidos (hasta {df.index[-1].date()})")
    return df.sort_index()


def build_regime(prices: pd.DataFrame, kind: str) -> np.ndarray:
    if kind == "btc":
        px = prices["btc"]; ma = px.rolling(200).mean()
        r = (px > ma).astype(float)
    elif kind == "breadth":
        ma50 = prices.rolling(50).mean()
        r = ((prices > ma50).sum(axis=1) / prices.shape[1] >= 0.5).astype(float)
    else:
        return np.ones(len(prices))
    return r.shift(1).fillna(0.0).to_numpy()


def run(prices: pd.DataFrame, target: float, regime: np.ndarray):
    """Devuelve (equity, retornos diarios, posiciones) con la lógica del backtest."""
    rets = (prices.pct_change()
            .replace([np.inf, -np.inf], 0.0).fillna(0.0))
    mom = ((prices / prices.shift(20) - 1.0) > 0).fillna(False).to_numpy()
    rr = rets.to_numpy()
    n, k = prices.shape
    equity = np.ones(n)
    daily = np.zeros(n)
    positions = np.zeros((n, k))
    unlev_hist: list[float] = []
    pos_prev = np.zeros(k)
    eq = 1.0
    for t in range(21, n - 1):
        active = mom[t]
        base = active.astype(float) / active.sum() if active.sum() else np.zeros(k)
        if len(unlev_hist) >= VOL_WINDOW:
            rv = np.std(unlev_hist[-VOL_WINDOW:]) * np.sqrt(DAYS)
            lev = 0.0 if not np.isfinite(rv) or rv <= 0 else min(target / rv, MAX_LEV)
        else:
            lev = 0.0
        pos = base * lev * regime[t]
        turnover = np.abs(pos - pos_prev).sum()
        fin = FIN_RATE / DAYS * max(pos.sum() - 1.0, 0.0)
        pnl = float(np.dot(pos, rr[t + 1])) - COST * turnover - fin
        unlev_hist.append(float(np.dot(base, rr[t + 1])))
        eq *= 1.0 + pnl
        if pnl <= -1.0 or eq <= 0:
            eq = 0.0
        equity[t + 1] = eq
        daily[t + 1] = pnl
        positions[t + 1] = pos
        pos_prev = pos
    return equity, daily, positions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=10_000.0)
    ap.add_argument("--no-update", action="store_true")
    args = ap.parse_args()

    print(f"Paper trading TSMOM20 · capital {args.capital:,.0f} €".replace(",", "."))
    prices = load_raw(CRYPTOS, START_DATE, END_DATE).dropna(how="all").ffill()
    prices = prices.replace(0.0, np.nan).ffill()
    print(f"  histórico Qlib: {prices.shape[0]} filas hasta {prices.index[-1].date()}")
    if not args.no_update:
        prices = refresh_prices(prices)
    assert prices.iloc[-1].notna().sum() > 0

    regimes = {k: build_regime(prices, k) for k in ("breadth", "btc", "none")}
    today = prices.index[-1]

    # fecha de arranque del paper trading: se fija la primera vez que se corre
    prev_state = json.loads(STATE.read_text()) if STATE.exists() else {}
    start_date = prev_state.get("start_date", str(today.date()))
    print(f"  paper trading desde {start_date}" if start_date != str(today.date())
          else f"  arranque del paper trading hoy ({start_date})")

    rows = []
    state = {}
    for name, target, reg in STRATEGIES:
        eq, daily, pos = run(prices, target, regimes[reg])
        # capital acumulado SOLO desde la fecha de arranque (cuenta nueva)
        m = prices.index > pd.Timestamp(start_date)
        cum = float(np.prod(1.0 + np.nan_to_num(daily[m]))) if m.any() else 1.0
        equity_eur = args.capital * cum
        # peso de cada moneda hoy (posición objetivo para mañana)
        w = {c: round(float(pos[-1][i]), 4) for i, c in enumerate(prices.columns)
             if abs(pos[-1][i]) > 1e-6}
        lev = round(float(pos[-1].sum()), 3)
        cash = round(1.0 - lev, 3)
        last_ret = float(daily[-1]) * 100
        rows.append({
            "date": str(today.date()), "strategy": name,
            "equity_eur": round(equity_eur, 2),
            "daily_ret_pct": round(last_ret, 3),
            "exposure": lev, "cash": cash, "positions": json.dumps(w, ensure_ascii=False),
        })
        state[name] = {"target_vol": target, "regime": reg,
                       "equity_eur": round(equity_eur, 2),
                       "positions_next": w, "exposure": lev, "cash": cash}

    # append idempotente
    new = pd.DataFrame(rows)
    if LEDGER.exists():
        old = pd.read_csv(LEDGER)
        merged = pd.concat([old, new]).drop_duplicates(["date", "strategy"], keep="last")
        merged = merged.sort_values(["date", "strategy"])
    else:
        merged = new
    merged.to_csv(LEDGER, index=False)
    STATE.write_text(json.dumps({"capital": args.capital, "start_date": start_date,
                                 "as_of": str(today.date()), "strategies": state},
                                indent=2, ensure_ascii=False))

    print(f"\nLibro: {LEDGER}  ({len(merged)} filas)")
    for r in rows:
        pos = r["positions"] if r["positions"] != "{}" else "sin posiciones (100% efectivo)"
        print(f"  {r['strategy']}")
        print(f"    capital: {r['equity_eur']:,.2f} € | día {r['daily_ret_pct']:+.2f}% "
              f"| exposición {r['exposure']:.2f} | efectivo {r['cash']:.2f}")
        print(f"    {pos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())