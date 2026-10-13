#!/usr/bin/env python3
import json, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"}

def fetch(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    res = data["chart"]["result"][0]
    meta = res["meta"]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")
    return {
        "symbol": sym,
        "price": meta["regularMarketPrice"],
        "prev_close": prev,
        "currency": meta.get("currency"),
        "regularMarketTime": meta.get("regularMarketTime"),
    }

out = {}
for sym in ["NVO", "AAPL", "GOOGL", "MSFT", "META", "EURUSD=X"]:
    try:
        out[sym] = fetch(sym)
        print(f"{sym}: {json.dumps(out[sym])}", flush=True)
    except Exception as e:
        out[sym] = {"symbol": sym, "error": str(e)}
        print(f"{sym}: ERROR {e}", flush=True)
    time.sleep(1.5)

with open("/opt/data/qlib/work/qlib_work/prices.json", "w") as f:
    json.dump(out, f, indent=2)
print("DONE")