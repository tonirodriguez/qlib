#!/usr/bin/env python3
import json, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"}

def fetch(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1mo"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    res = data["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    return closes  # most recent last

out = {}
for sym in ["NVO", "AAPL", "GOOGL", "MSFT", "META", "EURUSD=X"]:
    try:
        closes = fetch(sym)
        last = closes[-1]
        wk = closes[-6] if len(closes) >= 6 else closes[0]  # ~5 trading days ago
        out[sym] = {"last": last, "week_ago": wk,
                    "week_chg_pct": round((last/wk - 1) * 100, 2)}
        print(sym, out[sym])
    except Exception as e:
        print(sym, "ERROR", e)
with open("/opt/data/qlib/work/qlib_work/weekly.json", "w") as f:
    json.dump(out, f, indent=2)
print("DONE")