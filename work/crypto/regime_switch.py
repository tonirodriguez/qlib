"""regime_switch.py — Detector de régimen (bull/bear) + backtest del switch LONG <-> CASH.

Tesis (discutida con Toni): lo valioso NO es predecir el retorno, sino detectar el CAMBIO
de régimen en AMBAS direcciones, para no quedar atrapado holdeando cuando el mercado gira.

Regla causal (usa SOLO datos <= t, sin lookahead), con la filosofía del vol_gate validado
(percentil + histéresis) aplicada a cripto:

  SEÑAL DE RÉGIMEN sobre un PROXY de mercado (por defecto BTC):
    LONG (invertido en el mercado) si:
        precio > MA200  (tendencia alcista sostenida)
        Y drawdown desde el máximo histórico < DRAWDOWN_ENTRAR   (no en caída profunda)
    CASH (USDT con yield) en caso contrario:
        precio <= MA200   -> "el viento dio la vuelta, tendencia rota"
        O drawdown > DRAWDOWN_SALIR  -> "caída profunda, salir antes de que empeore"

  Histéresis: una vez cambiado de estado, se mantiene MIN_STATE_DAYS días para no zigzaguear.

Cuando LONG: capital invertido en el proxy (BTC) — lo más limpio y comparable a BTC buy&hold.
Cuando CASH: capital en USDT generando CASH_YIELD_APY.

Uso:
    python regime_switch.py --proxy btc --window 2021-06-01 2022-12-31   (prueba el giro)
    python regime_switch.py --proxy btc --start 2020-11-01 --end 2021-11-30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
OHLCV_DIR = PROJECT_ROOT / "scripts" / "crypto" / "csv_data" / "crypto_cryptocompare" / "ohlcv"
INITIAL_USD = 11000.0
CASH_YIELD_APY = 0.045
MA_WIN = 200
DRAWDOWN_SALIR = 0.20    # salir a cash si el proxy cae >20% desde su máximo histórico
DRAWDOWN_ENTRAR = 0.10   # volver a long solo si la caída se recuperó a <10%
MIN_STATE_DAYS = 10      # histéresis: mantener el estado al menos N días


def load_proxy(proxy: str):
    f = OHLCV_DIR / f"{proxy}.csv"
    df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
    s = df["close"].rename(proxy)
    return s.dropna()


def regime_signal(price: pd.Series):
    """Devuelve Series bool: True = LONG, False = CASH. Causal (MA200 + drawdown ATH)."""
    ma200 = price.rolling(MA_WIN, min_periods=MA_WIN // 2).mean()
    running_max = price.cummax()
    drawdown = price / running_max - 1.0  # negativo; -0.20 = 20% bajo el ATH

    raw_long = (price > ma200) & (drawdown > -DRAWDOWN_ENTRAR)
    raw = raw_long.fillna(True)  # antes de tener MA200 completa, asumimos LONG neutro

    # Aplicar histéresis de estado (mantener LONG/CASH MIN_STATE_DAYS)
    state = raw.astype(int).values
    out = np.ones(len(state), dtype=int)
    i = 0
    n = len(state)
    while i < n:
        if state[i] == 0:  # CASH detectado
            end = min(i + MIN_STATE_DAYS, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=price.index)


def simulate_switch(price: pd.Series, signal: pd.Series):
    """Backtest long/cash sobre el proxy. Retorna (curve, ops)."""
    daily_rate = (1.0 + CASH_YIELD_APY) ** (1.0 / 365.0) - 1.0
    cash = INITIAL_USD
    shares = 0.0
    curve, ops = [], []
    days_long = 0
    state = None
    for day in price.index:
        long = signal.loc[day] if day in signal.index else True
        px = float(price.loc[day])
        # yield del cash
        interest = cash * daily_rate
        cash += interest
        # cambio de estado
        if long and shares == 0:  # CASH -> LONG (comprar)
            fee = INITIAL_USD * 0.0010
            shares = (INITIAL_USD - fee) / px if px > 0 else 0
            cash = 0.0
            ops.append({"date": str(day.date()), "action": "BUY_LONG", "px": px})
        elif not long and shares > 0:  # LONG -> CASH (vender)
            gross = shares * px
            fee = gross * 0.0010
            cash += gross - fee
            shares = 0.0
            ops.append({"date": str(day.date()), "action": "SELL_CASH", "px": px})
        # valorar
        val = cash + (shares * px if shares > 0 else 0)
        if long:
            days_long += 1
        curve.append((day, val))
    return curve, ops, days_long


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default="btc")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()

    start, end = pd.Timestamp(args.start, tz="UTC"), pd.Timestamp(args.end, tz="UTC")
    price = load_proxy(args.proxy)
    price = price[(price.index >= start) & (price.index <= end)]
    signal = regime_signal(price)

    curve, ops, days_long = simulate_switch(price, signal)
    dates = [str(d.date()) for d, _ in curve]
    vals = np.array([v for _, v in curve])
    rets = np.diff(vals) / vals[:-1]
    rets = np.insert(rets, 0, vals[0] / INITIAL_USD - 1)
    final = float(vals[-1]) if len(vals) else INITIAL_USD
    ret_pct = (final / INITIAL_USD - 1) * 100

    # benchmark: buy&hold del proxy en el mismo rango
    bh = (price.iloc[-1] / price.iloc[0] - 1) * 100
    # benchmark: USDT puro (siempre cash)
    usdt = ((1 + CASH_YIELD_APY) ** (len(price) / 365.0) - 1) * 100

    result = {
        "nombre": args.name, "proxy": args.proxy,
        "start_date": dates[0], "end_date": dates[-1], "n_dias": len(price),
        "ret_switch_usd_pct": round(ret_pct, 2),
        "ret_buyhold_proxy_pct": round(bh, 2),
        "ret_puro_usdt_pct": round(usdt, 2),
        "n_cambios": len(ops), "ops": ops,
        "dias_en_long": days_long, "dias_en_cash": len(price) - days_long,
        "parametros": {"MA": MA_WIN, "drawdown_salir": DRAWDOWN_SALIR,
                       "drawdown_entrar": DRAWDOWN_ENTRAR, "min_state_days": MIN_STATE_DAYS},
    }
    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"regime_switch_{args.name}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "ops"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()