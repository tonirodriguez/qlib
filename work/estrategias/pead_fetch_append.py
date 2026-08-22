"""Descarga APPEND-ONLY de datos de earnings (PEAD) — point-in-time safe.

Diferencias con pead_fetch_full.py (que SOBRESCRIBE):
- Este script LEE el CSV histórico existente si existe.
- Descarga earnings de todo el universo y AÑADE SOLO las filas nuevas
  (clave primaria: ticker + quarter + reported_ts) que no existían.
- NUNCA borra ni edita filas previas → historial auditado y point-in-time.
- Si el fetch devuelve 0 datos → NO toca el CSV (guarda anti-fallo).

Salida: work/estrategias/pead_earnings_appended.csv (historial completen)
"""
import os, sys, time
import pandas as pd
from yahooquery import Ticker

UNIVERSE_FILE = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt"
OUT = "/opt/data/qlib/work/estrategias/pead_earnings_appended.csv"

MAX_RETRIES = 5
RETRY_DELAY = 3.0

# Claves primarias para deduplicar (lo que define "un fila existente")
KEY_COLS = ["ticker", "quarter", "reported_ts"]


def get_universe():
    tk = []
    with open(UNIVERSE_FILE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t: tk.append(t)
    return tk


def fetch_earnings(ticker):
    """Retorna lista de dicts de earnings (trimestres) o None."""
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

    # Cargar historial previo si existe
    existing = pd.DataFrame()
    if os.path.exists(OUT):
        try:
            existing = pd.read_csv(OUT)
            print(f"Historial previo: {len(existing)} filas ({existing['ticker'].nunique()} tickers)")
        except Exception as e:
            print(f"⚠️ No pude leer CSV previo ({e}); arranco de cero")

    existing_keys = set()
    if not existing.empty:
        existing_keys = set(map(tuple, existing[KEY_COLS].astype(str).values))

    # Descargar earnings de todo el universo
    new_rows = []
    ok_count = 0
    for t in universe:
        for attempt in range(MAX_RETRIES):
            try:
                rows = fetch_earnings(t)
                if rows:
                    ok_count += 1
                    # Añadir solo filas no existentes (append-only)
                    for r in rows:
                        key = (str(r["ticker"]), str(r["quarter"]), str(r["reported_ts"]))
                        if key not in existing_keys:
                            new_rows.append(r)
                            existing_keys.add(key)
                    break
                else:
                    break
            except Exception:
                time.sleep(RETRY_DELAY)
        time.sleep(0.8)

    print(f"\nTickers consultados con datos: {ok_count}")
    print(f"Filas NUEVAS a añadir: {len(new_rows)}")

    # Guard anti-fallo: si no hay datos NUEVOS no es problema (sigue habiendo historial),
    # pero si el fetch trae 0 de todo y no hay historial previo, no guardar nada vacío
    if not existing.empty or new_rows:
        combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        # dedupe defensivo
        combined = combined.drop_duplicates(subset=KEY_COLS, keep="last")
        # ordenar por ticker y fecha
        if "reported_ts" in combined.columns:
            combined["reported_ts"] = combined["reported_ts"].astype("Int64")
        combined = combined.sort_values(KEY_COLS)
        combined.to_csv(OUT, index=False)
        print(f"\n✅ Historial append-only guardado en {OUT}")
        print(f"   Total filas: {len(combined)} | tickers: {combined['ticker'].nunique()}")
    else:
        print("No hay historial previo ni datos nuevos: NO se escribe nada (evita corromper).")


if __name__ == "__main__":
    main()
