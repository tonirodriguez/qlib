"""ms_regime_variants.py — Variantes del gate Markov-switching sobre la p_high ya calculada.

No reajusta el modelo: reutiliza `ms_regime_daily.csv` (probabilidad FILTRADA causal del
estado de alta vol) para probar, sobre las MISMAS ventanas, si el mal resultado de
`ms_regime.py` se debe al diseño del gate (whipsaw) o al modelo en sí:

  A) umbral más alto (th_enter 0.7 / 0.9) y p_high SUAVIZADA (EMA) → menos whipsaw
  B) sizing continuo: exposición = 1 - p_high (en vez de on/off)
  C) combinación con regime_switch_v2: CASH si CUALQUIERA dice CASH (v2 handle tendencia,
     MS handle volatilidad)

Uso: python work/crypto/ms_regime_variants.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from regime_switch_v2 import regime_signal_v2  # noqa: E402
from ms_regime import (  # noqa: E402
    INITIAL_USD, OUT_DIR, WINDOWS, FULL_WINDOW, curve_metrics, load_proxy, usdt_curve,
    buyhold_curve,
)

DAILY = OUT_DIR / "ms_regime_daily.csv"


def simulate_exposure(price, exposure, initial_usd=INITIAL_USD, cash_apy=0.045, cost=0.0010):
    """Long/cash con exposición continua (0..1). Rebalancea sólo cuando cambia la exposición."""
    daily = (1.0 + cash_apy) ** (1.0 / 365.0) - 1.0
    cash = initial_usd
    btc = 0.0
    trades = 0
    curve = []
    for day in price.index:
        px = float(price.loc[day])
        # valorar antes de operar
        val = cash + btc * px
        # yield sólo sobre la parte en cash
        cash += cash * daily
        e = float(exposure.get(day, 1.0))
        e = 0.0 if e != e else min(max(e, 0.0), 1.0)
        val = cash + btc * px
        target_btc = (val * e) / px if px > 0 else 0.0
        delta = target_btc - btc
        if abs(delta) * px > val * 0.02:      # banda muerta 2%: evita churn
            trades += 1
            fee = abs(delta) * px * cost
            cash -= delta * px + fee
            btc += delta
        curve.append(cash + btc * px)
    return np.array(curve), trades


def main():
    price_all = load_proxy()
    df = pd.read_csv(DAILY, parse_dates=["date"]).set_index("date")
    p_high = df["p_high"].dropna()
    print(f"p_high reutilizada: {len(p_high)} días; media={p_high.mean():.3f}, "
          f"frac>0.5={float((p_high>0.5).mean()):.1%}, frac>0.9={float((p_high>0.9).mean()):.1%}")

    p_ema7 = p_high.ewm(span=7).mean()
    p_ema30 = p_high.ewm(span=30).mean()

    results = {}
    print(f"\n{'ventana':<14}{'variante':<34}{'ret%':>9}{'maxDD%':>9}{'Sharpe':>8}{'trades':>8}")
    print("-" * 82)

    for wname, (s, e) in {**WINDOWS, "full_2020_2026": FULL_WINDOW}.items():
        s_ts, e_ts = pd.Timestamp(s, tz="UTC"), pd.Timestamp(e, tz="UTC")
        px = price_all[(price_all.index >= s_ts) & (price_all.index <= e_ts)]
        if len(px) < 30:
            continue
        v2 = regime_signal_v2(px, vital_dd=0.30, pico_win=90, exit_dd=0.30,
                              ma_win=75, under_ma_days=10)
        v2_s = pd.Series(v2.values, index=px.index)

        variants = {}

        # A) umbrales altos + suavizado (exposure 0/1)
        for label, ph, th in [
            ("A1 th .7 sin suavizar", p_high, 0.7),
            ("A2 th .9 sin suavizar", p_high, 0.9),
            ("A3 EMA7 th .7", p_ema7, 0.7),
            ("A4 EMA30 th .7", p_ema30, 0.7),
        ]:
            g = ph.reindex(px.index)
            exp = (g < th).astype(float).fillna(1.0)   # LONG si prob baja
            variants[label] = simulate_exposure(px, exp)
        # B) sizing continuo
        for label, ph in [("B1 expos=1-p_high", p_high), ("B2 expos=1-EMA7", p_ema7)]:
            g = ph.reindex(px.index).fillna(0.0)
            variants[label] = simulate_exposure(px, (1.0 - g).clip(0, 1))
        # C) combinación con v2 (CASH si cualquiera dice CASH)
        for label, ph, th in [("C1 v2 AND MS(th.5)", p_high, 0.5),
                              ("C2 v2 AND MS(EMA30,.7)", p_ema30, 0.7)]:
            g = ph.reindex(px.index).fillna(0.0)
            ms_ok = g < th
            comb = (v2_s & ms_ok)
            variants[label] = simulate_exposure(px, comb.astype(float))

        rows = {}
        for label, (vals, tr) in variants.items():
            met = curve_metrics(vals)
            rows[label] = {**met, "trades": tr}
            print(f"{wname:<14}{label:<34}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
                  f"{met['sharpe']:>8.2f}{tr:>8}")
        # referencia v2
        vals, tr = simulate_exposure(px, v2_s.astype(float))
        met = curve_metrics(vals)
        rows["REF regime_switch_v2"] = {**met, "trades": tr}
        print(f"{wname:<14}{'REF regime_switch_v2':<34}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
              f"{met['sharpe']:>8.2f}{tr:>8}")
        met = curve_metrics(buyhold_curve(px))
        print(f"{wname:<14}{'REF buy&hold BTC':<34}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
              f"{met['sharpe']:>8.2f}{'-':>8}")
        met = curve_metrics(usdt_curve(px))
        print(f"{wname:<14}{'REF USDT puro':<34}{met['ret_pct']:>9.1f}{'-':>9}{'-':>8}{'-':>8}")
        print("-" * 82)
        results[wname] = rows

    (OUT_DIR / "ms_regime_variants.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n✅ {OUT_DIR/'ms_regime_variants.json'}")


if __name__ == "__main__":
    main()
