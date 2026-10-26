#!/usr/bin/env python3
"""carry_rebalance_test.py — prueba de rebalanceo y bandas de histeresis.

ESTRATEGIA NUEVA Y SEPARADA. No toca carry_funding.py ni el paper trading TSMOM.
Escribe en output/carry/rebalance/.

Pregunta: el carry pasivo se come parte del retorno en costes porque recalcula
pesos a diario. ¿Mejora con rebalanceo semanal/mensual? ¿Y si además usamos
bandas de histeresis para no entrar y salir con el funding oscilando alrededor
del umbral?

Variantes: frecuencia (diaria / semanal / mensual) x filtro (sin filtro /
histeresis estrecha / histeresis ancha).

  sin filtro        siempre invertido, equiponderado en las 9 monedas
  hyst estrecha     entra si funding_ma3 > 0.005%/8h; mantiene mientras >= 0.000%
  hyst ancha        entra si funding_ma3 > 0.010%/8h; mantiene mientras >= 0.002%

Uso: python carry_rebalance_test.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import carry_funding as cf

OUT = Path(__file__).resolve().parent / "output" / "carry" / "rebalance"
OUT.mkdir(parents=True, exist_ok=True)

FREQS = {"diaria": "D", "semanal": "W", "mensual": "M"}
FILTERS = {
    "sin_filtro": (None, None),
    "hyst_estrecha": (cf.THRESHOLD, 0.0),
    "hyst_ancha": (cf.THRESHOLD * 2, cf.THRESHOLD * 0.4),
}


def rebalance_mask(idx: pd.DatetimeIndex, freq: str) -> pd.Series:
    """True en los dias en que se recalcula la cartera."""
    if freq == "D":
        return pd.Series(True, index=idx)
    iso = idx.isocalendar()
    if freq == "W":
        key = iso["year"].astype(str) + "-" + iso["week"].astype(str)
    elif freq == "M":
        key = idx.year.astype(str) + "-" + idx.month.astype(str)
    else:
        raise ValueError(freq)
    key = pd.Series(key, index=idx)
    return key != key.shift(1)


def run(dfs: dict[str, pd.DataFrame], freq: str, filt: str) -> dict:
    freq = FREQS.get(freq, freq)
    idx = None
    for df in dfs.values():
        idx = df.index if idx is None else idx.union(df.index)
    idx = idx.sort_values()

    fund = pd.DataFrame({c: d["funding"].reindex(idx) for c, d in dfs.items()})
    spot_r = pd.DataFrame({c: d["spot"].pct_change().reindex(idx) for c, d in dfs.items()})
    perp_r = pd.DataFrame({c: d["perp"].pct_change().reindex(idx) for c, d in dfs.items()})
    basis = (spot_r - perp_r).fillna(0.0)
    fund = fund.fillna(0.0)
    fund_ma = fund.rolling(cf.LOOKBACK).mean()

    has_data = fund.notna() & pd.DataFrame(
        {c: d["spot"].reindex(idx).notna() for c, d in dfs.items()}
    )
    # tras el fillna, has_data debe mirar el dato original
    raw = pd.DataFrame({c: d["funding"].reindex(idx) for c, d in dfs.items()})
    has_data = raw.notna()

    reb = rebalance_mask(idx, freq)
    entry_band, exit_band = FILTERS[filt]

    rets, expos, turnovers, pos = [], [], [], pd.Series(0.0, index=fund.columns)
    n_coins_hist = []
    for i, dt in enumerate(idx):
        row = fund_ma.loc[dt]
        if i < cf.LOOKBACK + 1 or row.isna().all():
            rets.append(0.0); expos.append(0.0); turnovers.append(0.0); n_coins_hist.append(0)
            continue

        turnover = 0.0
        if bool(reb.iloc[i]):
            avail = has_data.loc[dt]
            if filt == "sin_filtro":
                sel = avail & row.notna()
            else:
                # histeresis: mantener lo que ya estaba si sigue por encima de la banda de salida
                hold = (pos > 0) & avail & row.notna() & (row >= exit_band)
                enter = (~(pos > 0)) & avail & row.notna() & (row > entry_band)
                sel = hold | enter
            n = int(sel.sum())
            target = (sel.astype(float) / n) if n else pd.Series(0.0, index=row.index)
            turnover = float((target - pos).abs().sum())
            pos = target
        # los dias sin rebalanceo se mantiene el libro; el P&L se devenga igual
        gross = float((pos * (fund.loc[dt] + basis.loc[dt])).sum())
        cost = cf.COST_LEG * 2 * turnover
        rets.append(gross - cost)
        expos.append(float(pos.sum()))
        turnovers.append(turnover)
        n_coins_hist.append(int((pos > 0).sum()))

    r = pd.Series(rets, index=idx)
    valid = pd.DataFrame({c: dfs[c]["spot"] for c in dfs}).reindex(idx)
    enough = valid.notna().sum(axis=1) >= 3
    r_v = r[enough]

    st = cf.stats(r_v.to_numpy(), f"{freq}+{filt}")
    st["avg_exposure"] = round(float(pd.Series(expos, index=idx)[enough].mean()), 2)
    st["avg_turnover"] = round(float(pd.Series(turnovers, index=idx)[enough].mean()), 4)
    st["avg_coins"] = round(float(pd.Series(n_coins_hist, index=idx)[enough].mean()), 2)
    st["freq"] = freq
    st["filt"] = filt
    return {"stats": st, "returns": r_v, "turnover": pd.Series(turnovers, index=idx)[enough]}


def main() -> int:
    print("Carry de funding — prueba de rebalanceo y bandas de histeresis")
    dfs = {c: cf.load_coin(c, refresh=False) for c in cf.COINS}
    print(f"  monedas: {len(dfs)}")

    results, series = {}, {}
    for freq in FREQS:
        for filt in FILTERS:
            key = f"{freq}+{filt}"
            try:
                res = run(dfs, freq, filt)
            except Exception as e:
                print(f"  ⚠️  {key}: {type(e).__name__}: {e}")
                continue
            results[key] = res["stats"]
            series[key] = res["returns"]

    order = [f"{f}+{k}" for f in FREQS for k in FILTERS]
    print(f"\n{'='*104}")
    print(f"{'variante':<30} {'anual':>8} {'Sharpe':>7} {'DD%':>7} {'t':>6} "
          f"{'expos':>6} {'turn/dia':>9} {'monedas':>8} {'10.000 EUR ->':>14}")
    print("=" * 104)
    for key in order:
        if key not in results:
            continue
        s = results[key]
        print(f"{key:<30} {s['annual_pct']:>7.2f}% {s['sharpe']:>7.2f} {s['dd_pct']:>6.1f}% "
              f"{s['t']:>+6.2f} {s['avg_exposure']:>6.2f} {s['avg_turnover']:>9.4f} "
              f"{s['avg_coins']:>8.2f} {s['final_eur']:>13,.0f} €")

    # detalle por año de la mejor variante por Sharpe
    cand = [k for k in results if results[k].get("sharpe") is not None
            and not np.isnan(results[k]["sharpe"])]
    if not cand:
        print("\nninguna variante produjo resultados")
        return 1
    best = max(cand, key=lambda k: results[k]["sharpe"])
    print(f"\n{'='*88}\nDETALLE POR AÑO — mejor por Sharpe: {best}\n{'='*88}")
    print(f"{'año':>5} {'retorno':>10} {'Sharpe':>7} {'DD%':>7} {'dias inv.':>10}")
    r_best = series[best]
    for y in sorted({d.year for d in r_best.index}):
        v = r_best[r_best.index.year == y]
        st = cf.stats(v.to_numpy(), str(y))
        print(f"{y:>5} {st['total_pct']:>9.1f}% {st['sharpe']:>7.2f} "
              f"{st['dd_pct']:>6.1f}% {int((v != 0).sum()):>10}")

    with open(OUT / "rebalance_results.json", "w") as f:
        json.dump({"rows": [results[k] for k in order if k in results], "best": best},
                  f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    pd.DataFrame(series).to_csv(OUT / "rebalance_daily.csv")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11.5, 6), dpi=140)
    cmap = {"sin_filtro": "#2ca02c", "hyst_estrecha": "#1f77b4", "hyst_ancha": "#d62728"}
    style = {"diaria": "-", "semanal": "--", "mensual": ":"}
    for key in order:
        if key not in series:
            continue
        freq, filt = key.split("+")
        eq = np.cumprod(1 + np.nan_to_num(series[key].to_numpy())) * 10_000
        ax.plot(series[key].index, eq, label=key, color=cmap[filt],
                linestyle=style[freq], linewidth=1.5, alpha=0.9)
    ax.set_yscale("log")
    ax.set_title("Carry de funding · rebalanceo y bandas de histeresis · 10.000 € (2019-2026)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Capital (€, log)"); ax.set_xlabel("Fecha")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:,.0f}".replace(",", ".") + " €"))
    fig.tight_layout()
    chart = OUT / "rebalance_equity.png"
    fig.savefig(chart); plt.close(fig)
    print(f"\ngrafico: {chart}")
    print(f"resultados en {OUT / 'rebalance_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
