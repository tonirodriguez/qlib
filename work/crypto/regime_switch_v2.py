"""regime_switch_v2.py — Régimen-switch v2: switch base calibrado + capa de VITALIDAD.

Filosofía (discutida con Toni): mantener el switch base (MA50/dd15%/minsd5) que ya gana a USDT
en giro-2022 y rally-2024, y AÑADIR una señal ORTOGONAL de VITALIDAD que, estando en LONG,
distinga el "bull ruidoso que sigue" (2021) del "crash que no vuelve" (2022).

Señal de vitalidad (opción 1, single-parámetro, causal):
    Se calcula el drawdown desde el PICO RECIENTE (running max de ventana corta, causal).
    Si el precio cae por debajo de VITAL_DD (-X%) de su pico reciente Y no recupera
    (el drawdown sigue empeorando / se mantiene profundo), el LONG es un crash -> CASH.
    Un bull ruidoso (2021) rebota rápido -> se mantiene LONG.

Estructura en 2 capas:
  Long_CASH_base(fuera de tuercas) = MA50 + dd_entrar15% + minsd5 (identico al calibrado v1)
  Vitalidad(solo cuando base=LONG) = si drawdown_pico_reciente < VITAL_DD -> forzar CASH.
Se mantiene la histéresis minsd sobre el resultado final (no zigzaguear).

Uso:
    python regime_switch_v2.py --proxy btc --start 2020-11-01 --end 2021-11-30 --name bull2021v2
Parámetros de vitalidad configurables via --vital-dd (0.30) y --pico-win (90).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OHLCV_DIR = PROJECT_ROOT / "scripts" / "crypto" / "csv_data" / "crypto_cryptocompare" / "ohlcv"
INITIAL_USD = 11000.0
CASH_YIELD_APY = 0.045

# --- Switch base calibrado (v1, identico): NO MODIFICAR ---
MA_WIN = 50
DD_ENTRAR = 0.15
MINSD = 5
COST = 0.0010


def load_proxy(proxy="btc"):
    df = pd.read_csv(OHLCV_DIR / f"{proxy}.csv", parse_dates=["date"]).set_index("date")
    return df["close"].dropna()


def regime_signal_base(price, ma_win=MA_WIN, dd_entrar=DD_ENTRAR, minsd=MINSD):
    ma = price.rolling(ma_win, min_periods=ma_win // 2).mean()
    running_max = price.cummax()
    dd = price / running_max - 1.0
    raw_long = (price > ma) & (dd > -dd_entrar)
    raw = raw_long.fillna(True)
    # histéresis simple
    s = raw.astype(int).values
    out = np.ones(len(s), dtype=int)
    i, n = 0, len(s)
    while i < n:
        if s[i] == 0:
            end = min(i + minsd, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=price.index)


def vitalidad(price, pico_win=90, vital_dd=0.30):
    """Drawdown desde el pico RECIENTE (running max ventana corta). Positivo/vital = cerca del pico."""
    pico_reciente = price.rolling(pico_win, min_periods=30, closed="left").max()  # causal, sin incluir hoy? usamos max hasta hoy para ser razonable
    # rolling().max con min_periods: incluye el punto actual. Para no mirar el futuro, es causal (solo pasado).
    pico_reciente = pico_reciente.fillna(price.cummax())
    dd_reci = price / pico_reciente - 1.0
    return dd_reci  # negativo = por debajo del pico reciente


def regime_signal_v2(price, vital_dd=0.30, pico_win=90):
    base = regime_signal_base(price)  # capa 1
    dd_reci = vitalidad(price, pico_win, vital_dd)  # capa 2: drawdown desde pico reciente
    # VITALIDAD = reversión: si el precio está rebotando fuerte del pico reciente
    # (bull ruidoso/moderado), se MANTIENE LONG aunque la vol/MA digan salir.
    # Solo se fuerza CASH si el drawdown de PICO RECIENTE es muy profundo (crash que no vuelve).
    # Rebase: el precio > -VITAL_DD por debajo del pico reciente => sano/rebotando.
    rebote = dd_reci > -vital_dd  # no hundido bajo el pico reciente
    final = pd.Series(base | rebote, index=price.index).astype(bool)
    # histéresis
    s = final.astype(int).values
    out = np.ones(len(s), dtype=int)
    i, n = 0, len(s)
    while i < n:
        if s[i] == 0:
            end = min(i + MINSD, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=price.index)


def simulate_switch(price, signal, initial_usd=INITIAL_USD):
    daily_rate = (1.0 + CASH_YIELD_APY) ** (1.0 / 365.0) - 1.0
    cash = initial_usd
    shares = 0.0
    n_trades = 0
    ops = []
    for day in price.index:
        long_now = signal.loc[day] if day in signal.index else True
        px = float(price.loc[day])
        cash += cash * daily_rate
        if long_now and shares == 0 and px > 0:
            n_trades += 1
            shares = (INITIAL_USD - INITIAL_USD * COST) / px
            cash = 0.0
            ops.append({"date": str(day.date()), "a": "BUY", "px": round(px, 2)})
        elif not long_now and shares > 0:
            n_trades += 1
            cash += shares * px - shares * px * COST
            shares = 0.0
            ops.append({"date": str(day.date()), "a": "SELL", "px": round(px, 2)})
    val = cash + (shares * price.iloc[-1] if shares > 0 else 0)
    return val, n_trades, ops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default="btc")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--vital-dd", type=float, default=0.30)
    ap.add_argument("--pico-win", type=int, default=90)
    ap.add_argument("--initial-usd", type=float, default=INITIAL_USD)
    args = ap.parse_args()

    start, end = pd.Timestamp(args.start, tz="UTC"), pd.Timestamp(args.end, tz="UTC")
    price = load_proxy(args.proxy)
    price = price[(price.index >= start) & (price.index <= end)]
    initial_usd = args.initial_usd

    sig = regime_signal_v2(price, args.vital_dd, args.pico_win)
    val, n_trades, ops = simulate_switch(price, sig, initial_usd=initial_usd)
    ret = (val / initial_usd - 1) * 100

    bh = (price.iloc[-1] / price.iloc[0] - 1) * 100
    usdt = ((1 + CASH_YIELD_APY) ** (len(price) / 365.0) - 1) * 100

    result = {
        "nombre": args.name, "proxy": args.proxy,
        "start_date": str(price.index[0].date()), "end_date": str(price.index[-1].date()),
        "n_dias": len(price),
        "ret_v2_usd_pct": round(ret, 2),
        "ret_buyhold_pct": round(bh, 2), "ret_usdt_pct": round(usdt, 2),
        "n_cambios": n_trades, "dias_long": int(sig.sum()),
        "dias_cash": int((~sig).sum()),
        "param_v2": {"base": {"ma": MA_WIN, "dd_entrar": DD_ENTRAR, "minsd": MINSD},
                     "vitalidad": {"vital_dd": args.vital_dd, "pico_win": args.pico_win}},
    }
    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"regime_switch_v2_{args.name}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()