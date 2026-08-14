#!/usr/bin/env python3
"""Actualizador LIGERO de datos de sp500_liquid (SOLO para esta máquina Hermes).

Este script es un canal PARALELO a la infraestructura de actualización de Qlib
(update_us_qlib_daily.sh / update_us_all.py), que NO se toca. Se crea porque el
pipeline oficial de Qlib normaliza el universo completo `all.txt` (12,737 tickers)
y no cabe en la RAM de esta máquina (7.6 GB) → proceso "Killed" por OOM.

Este actualizador solo baja los ~292 tickers de sp500_liquid (el universo que usa
la simulación), con peticiones espaciadas para evitar el rate-limit de Yahoo, y
guarda un CSV local. La simulación (simulate.py) leerá este CSV si existe.

Salida: toni/simulation/prices_live.csv  (index=date, columns=ticker, precios REALES)
"""
import os, sys, time, json, datetime
import urllib.request

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(SIM_DIR, "prices_live.csv")
#UNIVERSE_FILE = os.path.expanduser("~/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt")
UNIVERSE_FILE = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"
# Delay entre peticiones para no disparar rate-limit de Yahoo (429)
DELAY = float(os.environ.get("YAHOO_DELAY", "0.35"))
# Rango en días de historia a pedir (necesitamos >MOM_W=120 + margen)
HIST_DAYS = 160


def get_universe():
    tickers = []
    with open(UNIVERSE_FILE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t:
                tickers.append(t)
    return tickers


def fetch_yahoo(ticker, days=HIST_DAYS):
    """Retorna (fechas_list, closes_list) o (None, None) si falla."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={days}d"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode())
        r = data["chart"]["result"][0]
        ts = r["timestamp"]
        closes = r["indicators"]["quote"][0]["close"]
        return ts, closes
    except Exception:
        return None, None


def main():
    tickers = get_universe()
    print(f"Actualizador ligero sp500_liquid: {len(tickers)} tickers (canal paralelo a Qlib)")
    print(f"Delay entre peticiones: {DELAY}s | Historial: {HIST_DAYS} días")

    import pandas as pd
    data = {}   # ticker -> Series[close] indexado por fecha (UTC)
    failures = 0
    for i, t in enumerate(tickers):
        ts, closes = fetch_yahoo(t)
        if ts and closes:
            s = pd.Series(closes, index=pd.to_datetime(ts, unit="s", utc=True))
            s = s.dropna()
            if len(s) > 100:
                data[t] = s
            else:
                failures += 1
        else:
            failures += 1
        if (i + 1) % 50 == 0:
            print(f"  ...{i+1}/{len(tickers)} (ok={len(data)}, fail={failures})")
        time.sleep(DELAY)

    print(f"\nTickers con datos: {len(data)} (fallos: {failures})")
    if not data:
        print("ERROR: no se obtuvieron datos. Posible rate-limit de Yahoo (429). Reintenta más tarde.")
        sys.exit(1)

    df = pd.DataFrame(data).sort_index()
    df.to_csv(OUT_CSV)
    print(f"✅ Datos guardados en {OUT_CSV}")
    print(f"   Rango: {df.index[0].date()} → {df.index[-1].date()}")
    print(f"   Última fecha: {df.index[-1].date()} | filas: {len(df)}")


if __name__ == "__main__":
    main()
