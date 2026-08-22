"""Recuperar datos de earnings (sorpresa) para TODO el universo sp500_liquid.

Objetivo: aumentar de 39 tickers a tantos como sea posible los que tienen datos
de earnings, para que la señal PEAD sea representativa en el backtest combinado.

Usa yahooquery con reintentos robustos ante los fallos DNS/red intermitentes.
"""
import os, sys, time
import pandas as pd
from yahooquery import Ticker

UNIVERSE_FILE = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt"
OUT = "/opt/data/qlib/work/estrategias/pead_earnings_data_full.csv"

MAX_RETRIES = 5
RETRY_DELAY = 3.0

def get_universe():
    tk = []
    with open(UNIVERSE_FILE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t: tk.append(t)
    return tk

def fetch_earnings(ticker):
    """Retorna lista de diccionarios de earnings (trimestres) o None."""
    tk = Ticker(ticker)
    er = tk.earnings
    if not isinstance(er, dict) or ticker not in er or not er[ticker]:
        return None
    q = er[ticker].get("earningsChart", {}).get("quarterly", [])
    rows = []
    for trim in q:
        actual = trim.get("actual")
        est = trim.get("estimate")
        report_ts = trim.get("reportedDate")
        surp = trim.get("surprisePct")
        if actual is None or est is None or surp is None:
            continue
        rows.append({
            "ticker": ticker,
            "quarter": trim["date"],
            "actual": actual,
            "estimate": est,
            "surprise_pct": float(surp),
            "reported_ts": report_ts,
        })
    return rows if rows else None

def main():
    universe = get_universe()
    print(f"Universo: {len(universe)} tickers")

    all_rows = []
    ok_count = 0
    for t in universe:
        for attempt in range(MAX_RETRIES):
            try:
                rows = fetch_earnings(t)
                if rows:
                    all_rows.extend(rows)
                    ok_count += 1
                    break
                else:
                    break  # ticker sin earnings (no reintentar)
            except Exception:
                time.sleep(RETRY_DELAY)
        # feedback cada 50
        if (ok_count + 1) % 50 == 0 or (t == universe[-1]):
            print(f"  ...{t}: {ok_count} tickers con earnings hasta ahora")
        time.sleep(0.8)

    df = pd.DataFrame(all_rows)
    print(f"\n✅ Tickers con earnings: {ok_count}")
    print(f"✅ Trimestres totales: {len(df)}")
    if not df.empty:
        df.to_csv(OUT, index=False)
        print(f"Guardado en {OUT}")
        print("Distribución de tickers únicos con datos:")
        print(df["ticker"].nunique(), "tickers únicos")

if __name__ == "__main__":
    main()
