"""calibra_switch.py — Grid-search del régimen-switch para que gane a USDT en el crash SIN perder el bull.

Objetivo (definido con Toni): el switch debe superar al USDT puro protegiendo el DOWNSIDE
(crash 2021-22) mientras captura el UPSIDE (bull 2020-21). El switch naive perdió contra USDT
en los 4 regímenes — aquí se buscan hiperparámetros.

Método (anti-sobreajuste):
  SELECCIÓN (fitting): bull2021 (2020-11→2021-11) + giro2022 (2021-06→2022-12)
  VALIDACIÓN (OOS):     rally2024 (2024-01→2024-12) + base2025 (2025-01→2026-08)
El grid se ordena por una métrica de aptitud que equilibra: ganar al USDT en el crash
(evitar el drawdown) sin sacrificar el bull, con penalización por exceso de trades.

Se busca la config con mejor combinación en SELECCIÓN y se reporta cómo lo hace en OOS.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OHLCV_DIR = PROJECT_ROOT / "scripts" / "crypto" / "csv_data" / "crypto_cryptocompare" / "ohlcv"
INITIAL_USD = 11000.0
CASH_YIELD_APY = 0.045
PROXY = "btc"


def load_proxy():
    df = pd.read_csv(OHLCV_DIR / f"{PROXY}.csv", parse_dates=["date"]).set_index("date")
    return df["close"].dropna()


def regime_signal(price, ma_win, dd_entrar, minsd):
    ma = price.rolling(ma_win, min_periods=ma_win // 2).mean()
    running_max = price.cummax()
    dd = price / running_max - 1.0
    # Entrar long solo si la caída desde ATH se recuperó a < dd_entrar (más estricto que salir)
    raw_long = (price > ma) & (dd > -dd_entrar)
    raw = raw_long.fillna(True)
    state = raw.astype(int).values
    out = np.ones(len(state), dtype=int)
    i = 0
    n = len(state)
    while i < n:
        if state[i] == 0:
            end = min(i + minsd, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=price.index)


def simulate_switch(price, signal):
    daily_rate = (1.0 + CASH_YIELD_APY) ** (1.0 / 365.0) - 1.0
    cash = INITIAL_USD
    shares = 0.0
    n_trades = 0
    for day in price.index:
        long_now = signal.loc[day] if day in signal.index else True
        px = float(price.loc[day])
        cash += cash * daily_rate
        if long_now and shares == 0 and px > 0:      # CASH -> LONG
            n_trades += 1
            shares = (INITIAL_USD - INITIAL_USD * 0.0010) / px
            cash = 0.0
        elif not long_now and shares > 0:            # LONG -> CASH
            n_trades += 1
            cash += shares * px - shares * px * 0.0010
            shares = 0.0
    val = cash + (shares * price.iloc[-1] if shares > 0 else 0)
    return val, n_trades


def eval_window(price, start, end, params):
    p = price[(price.index >= pd.Timestamp(start, tz="UTC")) & (price.index <= pd.Timestamp(end, tz="UTC"))]
    sig = regime_signal(p, params["ma_win"], params["dd_entrar"], params["minsd"])
    val, n_trades = simulate_switch(p, sig)
    ret = (val / INITIAL_USD - 1) * 100

    def bh(ser):
        return (ser.iloc[-1] / ser.iloc[0] - 1) * 100
    bh_ret = bh(p)
    usdt = ((1 + CASH_YIELD_APY) ** (len(p) / 365.0) - 1) * 100
    return {"ret": ret, "bh": bh_ret, "usdt": usdt, "trades": n_trades, "days": len(p)}


WINDOWS = {
    "seleccion_bull2021": ("2020-11-01", "2021-11-30"),
    "seleccion_giro2022": ("2021-06-01", "2022-12-31"),
    "oos_rally2024": ("2024-01-01", "2024-12-31"),
    "oos_base2025": ("2025-01-01", "2026-08-30"),
}


def main():
    price = load_proxy()
    # Grid de hiperparámetros (acotado, barato)
    grid = [
        {"ma_win": m, "dd_entrar": e, "minsd": d}
        for m in (50, 100, 150, 200)
        for e in (0.05, 0.10, 0.15)
        for d in (5, 10, 20)
    ]
    print(f"Grid: {len(grid)} configs x {len(WINDOWS)} ventanas")

    results = []
    for idx, params in enumerate(grid):
        row = {"params": params}
        evals = {}
        for name, (s, e) in WINDOWS.items():
            evals[name] = eval_window(price, s, e, params)
        row["evals"] = evals
        # Aptitud en SELECCIÓN: gana al USDT en el giro (evitar carry del crash)
        # sin perder el bull. Edge = ret - usdt (si es positivo, el switch añade valor).
        g = evals["seleccion_giro2022"]; b = evals["seleccion_bull2021"]
        edge_giro = g["ret"] - g["usdt"]     # > 0 = capear crash mejor que cash
        edge_bull = (b["ret"] - b["usdt"])   # ideal >= 0 (capturar bs algo de la subida)
        # aptitud prioriza: no quedarte atrapado (giro) y no perderte el bull
        fitness = edge_giro + 0.5 * edge_bull - 0.25 * (g["trades"] + b["trades"])
        row["fitness"] = round(fitness, 2)
        row["edge_giro"] = round(edge_giro, 2)
        row["edge_bull"] = round(edge_bull, 2)
        results.append(row)

    results.sort(key=lambda r: -r["fitness"])
    best = results[0]

    print(f"\n=== MEJOR CONFIG (fitness {best['fitness']}) ===")
    print(f"  params: {best['params']}")
    for name in WINDOWS:
        e = best["evals"][name]
        print(f"  {name:<22} ret_switch={e['ret']:>8}  bh={e['bh']:>8}  usdt={e['usdt']:>7}  trades={e['trades']}")
    print(f"  edge_giro(sel)={best['edge_giro']}  edge_bull(sel)={best['edge_bull']}")

    # Top-5 para ver el espectro
    print("\n=== TOP-5 por fitness ===")
    for r in results[:5]:
        print(f"  fit={r['fitness']:>7} params={r['params']}")

    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "calibracion_switch_results.json").write_text(
        json.dumps({"best": {**best["params"], "fitness": best["fitness"],
                             "evals": {k: v for k, v in best["evals"].items()}},
                    "top5": [{"params": r["params"], "fitness": r["fitness"]} for r in results[:5]]},
                   indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()