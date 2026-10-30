#!/usr/bin/env python3
"""carry_funding.py — estrategia de carry de funding (long spot + short perp).

ESTRATEGIA NUEVA Y SEPARADA del paper trading del TSMOM (paper_trading_tsmom.py).
No comparte estado ni libro: escribe en output/carry/.

Idea: en los perpetuos, el lado largo paga al corto cuando el funding es
positivo. Comprando spot y vendiendo el perpetuo del mismo activo se cobra ese
funding manteniendo el riesgo de precio cubierto.

P&L diario por moneda y unidad de notional:
    carry = funding_cobrado + (retorno_spot - retorno_perp) - costes

Datos (API pública de Binance, sin key):
  - funding:  fapi/v1/fundingRate   (cada 8 h, desde ~2019-09)
  - perp:     fapi/v1/klines  (1d)
  - spot:     api/v3/klines   (1d)

Variantes:
  siempre      — carry incondicional en las 9 monedas, equiponderado
  umbral       — solo si el funding medio de 3 días supera 0.005%/8h
  top3         — solo las 3 monedas con mayor funding medio de 3 días

Uso: python carry_funding.py [--refresh]
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

OUT = Path(__file__).resolve().parent / "output" / "carry"
DATA = OUT / "data"
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

COINS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
START = pd.Timestamp("2019-09-01")
COST_LEG = 0.001          # 10 pb por pata en cada entrada y salida
DAYS = 365
THRESHOLD = 0.00005       # 0.005% por periodo de 8h ~ 5.5% anualizado
LOOKBACK = 3

SPOT = "https://api.binance.com/api/v3/klines"
FAPI = "https://fapi.binance.com/fapi/v1"


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _get(url: str, params: dict) -> list:
    q = urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                f"{url}?{q}", headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    return []


def fetch_klines(url: str, symbol: str) -> pd.Series:
    """Cierres diarios paginando desde START hasta hoy."""
    out, cur = {}, int(START.timestamp() * 1000)
    end = int(pd.Timestamp.utcnow().normalize().timestamp() * 1000)
    while cur < end:
        data = _get(url, {"symbol": symbol, "interval": "1d", "limit": 1000,
                          "startTime": cur, "endTime": end})
        if not data:
            break
        for k in data:
            out[pd.Timestamp(k[0], unit="ms").normalize().tz_localize(None)] = float(k[4])
        if len(data) < 1000:
            break
        cur = data[-1][0] + 86400000
        time.sleep(0.12)
    return pd.Series(out).sort_index()


def fetch_funding(symbol: str) -> pd.Series:
    """Tipo de funding por periodo, paginando desde START."""
    recs, cur = [], int(START.timestamp() * 1000)
    end = int(pd.Timestamp.utcnow().timestamp() * 1000)
    while cur < end:
        data = _get(f"{FAPI}/fundingRate", {"symbol": symbol, "limit": 1000,
                                            "startTime": cur, "endTime": end})
        if not data:
            break
        recs.extend(data)
        if len(data) < 1000:
            break
        cur = data[-1]["fundingTime"] + 1
        time.sleep(0.12)
    if not recs:
        return pd.Series(dtype=float)
    idx = [pd.Timestamp(r["fundingTime"], unit="ms").tz_localize(None) for r in recs]
    vals = [float(r["fundingRate"]) for r in recs]
    return pd.Series(vals, index=idx).sort_index()


def load_coin(coin: str, refresh: bool) -> pd.DataFrame:
    sym = coin.upper() + "USDT"
    f_spot = DATA / f"{coin}_spot.csv"
    f_perp = DATA / f"{coin}_perp.csv"
    f_fund = DATA / f"{coin}_funding.csv"
    if refresh or not (f_spot.exists() and f_perp.exists() and f_fund.exists()):
        print(f"  descargando {sym} ...")
        fetch_klines(SPOT, sym).rename("close").to_csv(f_spot)
        time.sleep(0.12)
        fetch_klines(f"{FAPI}/klines", sym).rename("close").to_csv(f_perp)
        time.sleep(0.12)
        fetch_funding(sym).rename("funding").to_csv(f_fund)
    spot = pd.read_csv(f_spot, index_col=0, parse_dates=True).iloc[:, 0]
    perp = pd.read_csv(f_perp, index_col=0, parse_dates=True).iloc[:, 0]
    fund = pd.read_csv(f_fund, index_col=0, parse_dates=True).iloc[:, 0]
    df = pd.DataFrame({"spot": spot, "perp": perp}).dropna()
    # funding del día = suma de los periodos de ese día (3 al día normalmente)
    fund.index = fund.index.normalize()
    fund_daily = fund.groupby(level=0).sum()
    df["funding"] = fund_daily.reindex(df.index).fillna(0.0)
    return df


def stats(r: np.ndarray, label: str) -> dict:
    v = np.nan_to_num(np.asarray(r, dtype=float))
    if len(v) < 30 or v.std() == 0:
        return {"strategy": label, "annual_pct": 0.0, "sharpe": float("nan"),
                "dd_pct": 0.0, "t": float("nan"), "n": len(v), "final_eur": 0.0}
    eq = np.cumprod(1 + v)
    dd = float(np.min(eq / np.maximum.accumulate(eq) - 1))
    ann = float(eq[-1] ** (DAYS / len(v)) - 1)
    return {
        "strategy": label,
        "annual_pct": round(ann * 100, 2),
        "total_pct": round((eq[-1] - 1) * 100, 1),
        "sharpe": round(float(v.mean() / v.std() * np.sqrt(DAYS)), 2),
        "dd_pct": round(dd * 100, 1),
        "t": round(float(v.mean() / v.std() * np.sqrt(len(v))), 2),
        "n": len(v),
        "final_eur": round(float(eq[-1]) * 10_000, 0),
    }


def run_variant(dfs: dict[str, pd.DataFrame], mode: str) -> tuple[pd.Series, pd.Series]:
    """Devuelve (retornos netos diarios, exposición) para la variante pedida."""
    idx = None
    for df in dfs.values():
        idx = df.index if idx is None else idx.union(df.index)
    idx = idx.sort_values()
    fund = pd.DataFrame({c: d["funding"].reindex(idx) for c, d in dfs.items()})
    spot_r = pd.DataFrame({c: d["spot"].pct_change().reindex(idx) for c, d in dfs.items()})
    perp_r = pd.DataFrame({c: d["perp"].pct_change().reindex(idx) for c, d in dfs.items()})
    basis = (spot_r - perp_r).fillna(0.0)
    fund = fund.fillna(0.0)
    fund_ma = fund.rolling(LOOKBACK).mean()

    out, expo, pos_prev = [], [], pd.Series(0.0, index=fund.columns)
    for i, dt in enumerate(idx):
        if i < LOOKBACK + 1 or fund.iloc[i].isna().all():
            out.append(0.0); expo.append(0.0); continue
        row = fund_ma.loc[dt]
        if mode == "siempre":
            sel = row.notna()
        elif mode == "umbral":
            sel = row > THRESHOLD
        elif mode == "top3":
            sel = pd.Series(False, index=row.index)
            top = row.dropna().nlargest(3).index
            sel[top] = row[top] > THRESHOLD
        else:
            raise ValueError(mode)
        n = int(sel.sum())
        pos = (sel.astype(float) / n) if n else pd.Series(0.0, index=row.index)
        gross = float((pos * (fund.loc[dt] + basis.loc[dt])).sum())
        turnover = float((pos - pos_prev).abs().sum())
        # entrada o salida: 2 patas por lado que se mueve
        cost = COST_LEG * 2 * turnover
        out.append(gross - cost)
        expo.append(float(pos.sum()))
        pos_prev = pos
    return pd.Series(out, index=idx), pd.Series(expo, index=idx)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    print("Carry de funding (estrategia separada del paper trading TSMOM)")
    dfs = {}
    for c in COINS:
        try:
            dfs[c] = load_coin(c, args.refresh)
        except Exception as e:
            print(f"  ⚠️  {c}: {type(e).__name__} — se omite")
    if not dfs:
        print("sin datos")
        return 1

    coverage = pd.DataFrame({c: d["funding"].abs() for c, d in dfs.items()})
    first_dates = {c: str(d.index[0].date()) for c, d in dfs.items()}
    print(f"  monedas: {len(dfs)} | inicio por moneda: {first_dates}")

    rows = []
    series = {}
    for mode in ("siempre", "umbral", "top3"):
        r, expo = run_variant(dfs, mode)
        # se evalúa desde que hay al menos 3 monedas con datos
        valid = pd.DataFrame({c: dfs[c]["spot"] for c in dfs}).reindex(r.index)
        enough = valid.notna().sum(axis=1) >= 3
        r_v = r[enough]
        rows.append({**stats(r_v.to_numpy(), mode),
                     "avg_exposure": round(float(expo[enough].mean()), 2)})
        series[mode] = r_v

    # funding medio anualizado por año (contexto)
    print(f"\n{'='*88}")
    print(f"{'variante':<10} {'anual':>8} {'total':>10} {'Sharpe':>7} {'DD%':>7} "
          f"{'t':>6} {'expos':>6} {'10.000 EUR ->':>14}")
    print("=" * 88)
    for r in rows:
        print(f"{r['strategy']:<10} {r['annual_pct']:>7.2f}% {r['total_pct']:>9.1f}% "
              f"{r['sharpe']:>7.2f} {r['dd_pct']:>6.1f}% {r['t']:>+6.2f} "
              f"{r['avg_exposure']:>6.2f} {r['final_eur']:>13,.0f} €")

    for var in ("siempre", "umbral"):
        r_v = series[var]
        print(f"\n{'='*88}\nDETALLE POR AÑO — variante {var}\n{'='*88}")
        print(f"{'año':>5} {'retorno':>10} {'Sharpe':>7} {'DD%':>7} {'días inv.':>10}")
        for y in sorted({d.year for d in r_v.index}):
            v = r_v[r_v.index.year == y]
            st = stats(v.to_numpy(), str(y))
            inv = int((v != 0).sum())
            print(f"{y:>5} {st['total_pct']:>9.1f}% {st['sharpe']:>7.2f} "
                  f"{st['dd_pct']:>6.1f}% {inv:>10}")

    # funding medio por año (contexto de mercado)
    print(f"\n{'='*88}\nFUNDING MEDIO ANUALIZADO POR AÑO (todas las monedas)\n{'='*88}")
    allf = pd.DataFrame({c: dfs[c]["funding"] for c in dfs})
    for y in sorted({d.year for d in allf.index}):
        row = allf[allf.index.year == y]
        if row.empty:
            continue
        media = float(row.stack().mean()) * 3 * 365 * 100
        print(f"  {y}: funding medio {media:>6.2f}% anualizado")

    with open(OUT / "carry_results.json", "w") as f:
        json.dump({"rows": rows,
                   "first_dates": first_dates,
                   "by_year_umbral": {str(y): stats(series["umbral"][series["umbral"].index.year == y].to_numpy(), str(y))
                                      for y in sorted({d.year for d in series["umbral"].index})}},
                  f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    # guardar las series diarias de todas las variantes y el gráfico
    pd.DataFrame(series).to_csv(OUT / "carry_daily.csv")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=140)
    colors = {"siempre": "#2ca02c", "umbral": "#1f77b4", "top3": "#d62728"}
    for var in ("siempre", "umbral", "top3"):
        eq = np.cumprod(1 + np.nan_to_num(series[var].to_numpy())) * 10_000
        ax.plot(series[var].index, eq, label=var, color=colors[var], linewidth=1.8)
    ax.set_yscale("log")
    ax.set_title("Carry de funding · 10.000 € · long spot + short perpetuo "
                 "(2019-2026)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Capital (€, log)")
    ax.set_xlabel("Fecha")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper left")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:,.0f}".replace(",", ".") + " €"))
    fig.tight_layout()
    chart = OUT / "carry_equity.png"
    fig.savefig(chart)
    plt.close(fig)
    print(f"grafico: {chart}")
    print(f"\nresultados en {OUT / 'carry_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())