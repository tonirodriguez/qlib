#!/usr/bin/env python3
"""Escanea el universo sp500_liquid por earnings próximos (Yahoo Finance)."""
import json, time, sys, datetime
import urllib.request, urllib.parse

UNIVERSE = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"

def universe():
    out = []
    with open(UNIVERSE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t:
                out.append(t)
    return out

def yahoo_earnings(ticker):
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=calendarEvents"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
        ev = d["quoteSummary"]["result"][0]["calendarEvents"]["earnings"]
        dates = ev.get("earningsDate") or []
        if not dates:
            return None
        # fecha más próxima futura
        future = [fmt["fmt"] for fmt in dates]
        return future
    except Exception as e:
        return f"ERR:{type(e).__name__}"

tickers = universe()
print(f"Escaneando {len(tickers)} tickers del universo ...", file=sys.stderr)
today = datetime.date.today()
horizon_days = 45
upcoming = []
for i, t in enumerate(tickers):
    ed = yahoo_earnings(t)
    if isinstance(ed, list) and ed:
        for s in ed:
            try:
                d = datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
                delta = (d - today).days
                if 0 <= delta <= horizon_days:
                    upcoming.append((t, d.isoformat(), delta))
                    break
            except Exception:
                continue
    if (i+1) % 50 == 0:
        print(f"  ...{i+1}/{len(tickers)}", file=sys.stderr)
    time.sleep(1.0)

upcoming.sort(key=lambda x: x[2])
print(f"\n=== {len(upcoming)} tickers con earnings en los próximos {horizon_days} días ({today}) ===")
for t, d, delta in upcoming:
    print(f"  {t:<6} {d}  (en {delta}d)")