#!/usr/bin/env python3
"""carry_paper_trading.py — paper trading diario del carry de funding.

ESTRATEGIA SEPARADA del paper trading del TSMOM (paper_trading_tsmom.py):
no comparte estado, libro ni directorio.

Sigue dos variantes, ambas PASIVAS (sin filtros ni histeresis, que la prueba
demostro que no aportan):
  carry-9       equiponderado en las 9 monedas
  carry-majors  equiponderado en BTC y ETH (mas liquidez y funding estable)

Rebalanceo mensual (el test demostro que la frecuencia apenas cambia el
resultado; mensual es lo que menos esfuerzo exige).

Cada dia: refresca los datos de Binance de forma incremental, calcula el
retorno del dia (funding cobrado + diferencia spot-perpetuo - costes) y anade
la fila al libro. Empieza con 10.000 EUR y no usa informacion futura.

Uso: python carry_paper_trading.py [--capital 10000] [--no-update]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carry_funding as cf

BASE = Path(__file__).resolve().parent / "output" / "carry"
PAPER = BASE / "paper_trading"
PAPER.mkdir(parents=True, exist_ok=True)
LEDGER = PAPER / "ledger.csv"
STATE = PAPER / "state.json"

VARIANTS = {
    "carry-9": cf.COINS,
    "carry-majors": ["btc", "eth"],
}


def _fetch_from(url: str, symbol: str, start_ms: int) -> dict:
    """Cierres diarios desde start_ms hasta la ultima vela cerrada."""
    out, cur = {}, start_ms
    end = int(pd.Timestamp.utcnow().normalize().timestamp() * 1000)
    while cur < end:
        data = cf._get(url, {"symbol": symbol, "interval": "1d", "limit": 1000,
                             "startTime": cur, "endTime": end})
        if not data:
            break
        for k in data:
            out[pd.Timestamp(k[0], unit="ms").normalize().tz_localize(None)] = float(k[4])
        if len(data) < 1000:
            break
        cur = data[-1][0] + 86400000
        time.sleep(0.1)
    return out


def _fetch_funding_from(symbol: str, start_ms: int) -> dict:
    out, cur = {}, start_ms
    end = int(pd.Timestamp.utcnow().timestamp() * 1000)
    while cur < end:
        data = cf._get(f"{cf.FAPI}/fundingRate", {"symbol": symbol, "limit": 1000,
                                                  "startTime": cur, "endTime": end})
        if not data:
            break
        for r in data:
            out[pd.Timestamp(r["fundingTime"], unit="ms").tz_localize(None)] = float(r["fundingRate"])
        if len(data) < 1000:
            break
        cur = data[-1]["fundingTime"] + 1
        time.sleep(0.1)
    return out


def update_coin(coin: str) -> None:
    """Actualiza de forma incremental los 3 CSV del cache de esa moneda."""
    sym = coin.upper() + "USDT"
    f_spot = cf.DATA / f"{coin}_spot.csv"
    f_perp = cf.DATA / f"{coin}_perp.csv"
    f_fund = cf.DATA / f"{coin}_funding.csv"

    if not f_spot.exists():
        cf.fetch_klines(cf.SPOT, sym).rename("close").to_csv(f_spot)
    if not f_perp.exists():
        cf.fetch_klines(f"{cf.FAPI}/klines", sym).rename("close").to_csv(f_perp)
    if not f_fund.exists():
        cf.fetch_funding(sym).rename("funding").to_csv(f_fund)

    def _next_day_ms(s: pd.Series) -> int:
        return int((s.index[-1] + pd.Timedelta(days=1)).tz_localize("UTC").timestamp() * 1000)

    for path, fn, col in ((f_spot, lambda: _fetch_from(cf.SPOT, sym,
                                                       _next_day_ms(pd.read_csv(f_spot, index_col=0, parse_dates=True).iloc[:, 0])),
                           "close"),
                          (f_perp, lambda: _fetch_from(f"{cf.FAPI}/klines", sym,
                                                       _next_day_ms(pd.read_csv(f_perp, index_col=0, parse_dates=True).iloc[:, 0])),
                           "close")):
        cur = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
        if int(pd.Timestamp.utcnow().normalize().timestamp() * 1000) <= \
                int((cur.index[-1] + pd.Timedelta(days=1)).tz_localize("UTC").timestamp() * 1000):
            continue
        new = fn()
        if new:
            add = pd.Series(new).sort_index()
            add = add[add.index > cur.index[-1]]
            if len(add):
                pd.concat([cur, add]).to_csv(path)

    cur_f = pd.read_csv(f_fund, index_col=0, parse_dates=True).iloc[:, 0]
    new_f = _fetch_funding_from(sym, int(cur_f.index[-1].timestamp() * 1000) + 1)
    if new_f:
        add = pd.Series(new_f).sort_index()
        add = add[add.index > cur_f.index[-1]]
        if len(add):
            pd.concat([cur_f, add]).to_csv(f_fund)


def build_panel(coins: list[str]) -> pd.DataFrame:
    """Panel diario con funding del dia, retorno spot y retorno perpetuo."""
    idx = None
    fund, spot, perp = {}, {}, {}
    for c in coins:
        df = cf.load_coin(c, refresh=False)
        idx = df.index if idx is None else idx.union(df.index)
        fund[c] = df["funding"]
        spot[c] = df["spot"]
        perp[c] = df["perp"]
    idx = idx.sort_values()
    F = pd.DataFrame({c: fund[c].reindex(idx) for c in coins})
    Sr = pd.DataFrame({c: spot[c].reindex(idx).pct_change() for c in coins})
    Pr = pd.DataFrame({c: perp[c].reindex(idx).pct_change() for c in coins})
    return F, Sr, Pr


def simulate(F: pd.DataFrame, Sr: pd.DataFrame, Pr: pd.DataFrame) -> pd.Series:
    """Retorno diario del carry pasivo con rebalanceo mensual."""
    basis = (Sr - Pr).fillna(0.0)
    Ff = F.fillna(0.0)
    avail = F.notna()
    n_coins = avail.sum(axis=1).clip(lower=1)
    w = avail.div(n_coins, axis=0).fillna(0.0)

    # rebalanceo: la cartera se fija el primer dia de cada mes y se mantiene
    keys = pd.Series(w.index.year.astype(str) + "-" + w.index.month.astype(str),
                     index=w.index)
    new_month = keys != keys.shift(1)
    held = pd.DataFrame(0.0, index=w.index, columns=w.columns)
    current = pd.Series(0.0, index=w.columns)
    for i, dt in enumerate(w.index):
        if bool(new_month.iloc[i]):
            current = w.loc[dt].copy()
        held.loc[dt] = current

    gross = (held * (Ff + basis)).sum(axis=1)
    turnover = held.diff().abs().sum(axis=1).fillna(0.0)
    cost = cf.COST_LEG * 2 * turnover
    return gross - cost, held


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=10_000.0)
    ap.add_argument("--no-update", action="store_true")
    args = ap.parse_args()

    print("Paper trading · carry de funding (long spot + short perpetuo)")
    if not args.no_update:
        for c in cf.COINS:
            try:
                update_coin(c)
            except Exception as e:
                print(f"  ⚠️  {c}: no se pudo refrescar ({type(e).__name__})")

    F, Sr, Pr = build_panel(cf.COINS)
    rets, held = simulate(F, Sr, Pr)
    today = rets.index[-1]

    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    start = prev.get("start_date", str(today.date()))
    print(f"  datos hasta {today.date()} | paper trading desde {start}")

    rows, state = [], {}
    for name, coins in VARIANTS.items():
        cols = [c for c in coins if c in held.columns]
        r = rets.copy()
        # reescala al universo de la variante: recomputa con sus monedas
        Fi, Si, Pi = F[cols], Sr[cols], Pr[cols]
        r, h = simulate(Fi, Si, Pi)
        m = r.index > pd.Timestamp(start)
        cum = float(np.prod(1.0 + np.nan_to_num(r[m].to_numpy()))) if m.any() else 1.0
        equity = args.capital * cum
        w = {c: round(float(h.iloc[-1][c]), 4) for c in cols
             if abs(h.iloc[-1][c]) > 1e-6}
        funding_bps = float(Fi.iloc[-1].sum()) * 10_000
        rows.append({
            "date": str(today.date()), "strategy": name,
            "equity_eur": round(equity, 2),
            "daily_ret_pct": round(float(r.iloc[-1]) * 100, 4),
            "funding_today_bps": round(funding_bps, 2),
            "n_coins": len(w),
            "positions": json.dumps(w, ensure_ascii=False),
        })
        state[name] = {"coins": coins, "rebalance": "mensual",
                       "equity_eur": round(equity, 2),
                       "positions": w, "funding_today_bps": round(funding_bps, 2)}

    new = pd.DataFrame(rows)
    if LEDGER.exists():
        old = pd.read_csv(LEDGER)
        merged = pd.concat([old, new]).drop_duplicates(["date", "strategy"], keep="last")
        merged = merged.sort_values(["date", "strategy"])
    else:
        merged = new
    merged.to_csv(LEDGER, index=False)
    STATE.write_text(json.dumps({"capital": args.capital, "start_date": start,
                                 "as_of": str(today.date()), "strategies": state},
                                indent=2, ensure_ascii=False))

    print(f"\nLibro: {LEDGER}  ({len(merged)} filas)")
    for r in rows:
        print(f"  {r['strategy']}")
        print(f"    capital: {r['equity_eur']:,.2f} € | día {r['daily_ret_pct']:+.4f}% "
              f"| funding hoy {r['funding_today_bps']:+.2f} pb | {r['n_coins']} monedas")
        print(f"    {r['positions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())