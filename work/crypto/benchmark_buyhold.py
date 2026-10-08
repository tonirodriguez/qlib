"""benchmark_buyhold.py — Cuánto habría ganado un buy & hold en los MISMOS regímenes que la v8.

Compara la v8 (backtest por régimen) contra:
  - BTC buy & hold (el benchmark de referencia del mercado cripto)
  - Portfolio igual-ponderado de las 9 criptos del universo (1/9 de capital inicial en cada una, sin rebalanceo)

Formato: CSV de OHLCV por moneda (close = precio). Capital inicial fijo en USD sobre el que se
"compran" las fracciones al precio del primer día del régimen y se valoran al último día.

Uso:
    python benchmark_buyhold.py --name bull2021 --start 2020-11-01 --end 2021-11-30
    python benchmark_buyhold.py --name rally2024 --start 2024-01-01 --end 2024-12-31
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
INITIAL_USD = 11000.0  # mismo capital inicial que el backtest v8 (10000 EUR * 1.10)


def load_closes():
    closes = {}
    idx = None
    for c in CRYPTOS:
        f = OHLCV_DIR / f"{c}.csv"
        if not f.exists():
            print(f"  (falta {c}.csv)", file=sys.stderr)
            continue
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        col = c.upper()
        df = df.rename(columns={"close": col})[[col]]
        closes[col] = df[col]
    df = pd.DataFrame(closes).sort_index()
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    start, end = pd.Timestamp(args.start, tz="UTC"), pd.Timestamp(args.end, tz="UTC")
    df = load_closes()
    df = df[(df.index >= start) & (df.index <= end)].ffill()
    first_row, last_row = df.iloc[0], df.iloc[-1]
    days = len(df)

    # Evolución del índice del régimen (referencia)
    btcs = first_row.get("BTC", np.nan)

    resultados = {}
    # 1. BTC buy & hold
    if "BTC" in df.columns:
        ret_btc = (last_row["BTC"] / first_row["BTC"] - 1) * 100
        resultados["BTC_buyhold_usd_pct"] = round(ret_btc, 2)
        resultados["BTC_price_first"] = round(float(first_row["BTC"]), 2)
        resultados["BTC_price_last"] = round(float(last_row["BTC"]), 2)
    # 2. Portfolio igual-ponderado 9 criptos (fracción fija inicial, sin rebalanceo)
    frac = 1.0 / len(df.columns)
    valor_final = 0.0
    for col in df.columns:
        if first_row[col] and last_row[col] and first_row[col] > 0 and last_row[col] > 0:
            valor_final += (INITIAL_USD * frac) * (last_row[col] / first_row[col])
    ret_ew = (valor_final / INITIAL_USD - 1) * 100
    resultados["equal_weight_9_pct"] = round(ret_ew, 2)
    resultados["n_cryptos"] = len(df.columns)
    resultados["initial_usd"] = INITIAL_USD
    resultados["days"] = days

    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"benchmark_buyhold_{args.name}.json"
    out.write_text(json.dumps(resultados, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resultados, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()