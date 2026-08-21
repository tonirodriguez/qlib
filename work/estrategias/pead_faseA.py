"""FASE A — PEAD: test del alpha de earnings momentum en el universo sp500_liquid.

Objetivo: medir si hay relación (IC) entre la SORPRESA de resultados (SUE/surprise)
y el RETORNO POST-ANUNCIO. Si el IC es positivo, el PEAD añade alpha ortogonal al
momentum de precios y vale la pena integrarlo.

Fuente: yahooquery (datos de earnings trimestrales: actual, estimate, surprise,
reportedDate) — ya funciona en este entorno.

Uso: python work/estrategias/pead_faseA.py [num_tickers]
"""
import os, sys, time, json
import numpy as np
import pandas as pd
from yahooquery import Ticker

from qlib.data import D
import qlib
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
qlib.init(provider_uri=QLIB_URI, region='us')

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30

def get_universe():
    inst = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data/instruments/sp500_liquid.txt"
    tk = []
    with open(inst) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t: tk.append(t)
    return tk

def get_returns(ticker, lookback=60, forward=30):
    """Retornos diarios del ticker desde Qlib (fallback)."""
    try:
        df = D.features([ticker], ["$close", "$factor"], start_time="2010-01-01",
                        end_time="2100-12-31", freq="day")
        if df is None or df.empty:
            return None
        c = df["$close"] / df["$factor"]
        c = c["$close"] if "$close" in c.columns else c
        s = c.dropna() if isinstance(c, pd.Series) else c
        # retorno
        ret = s.pct_change()
        return s, ret
    except Exception:
        return None

def main():
    universe = get_universe()
    print(f"Universo: {len(universe)} tickers | Probando {N}\n")

    # Resultados por ticker
    rows_anuncio = []  # para medir retorno post-anuncio vs surprise
    MAX_RETRIES = 4    # reintentos ante fallos DNS/red
    RETRY_DELAY = 2.5

    for t in universe[:N]:
        ok = False
        for attempt in range(MAX_RETRIES):
            try:
                tk = Ticker(t)
                er = tk.earnings
                if isinstance(er, dict) and t in er and er[t]:
                    q = er[t].get("earningsChart", {}).get("quarterly", [])
                else:
                    q = []
                # Resetear cache de yahooquery si repite fallos DNS
                try:
                    import curl_cffi
                except ImportError:
                    pass
                if not q:
                    raise ValueError("empty earnings")
                for trim in q:
                    actual = trim.get("actual")
                    est = trim.get("estimate")
                    report_ts = trim.get("reportedDate")
                    surp_pct = trim.get("surprisePct")
                    if actual is None or est is None or surp_pct is None:
                        continue
                    rows_anuncio.append({
                        "ticker": t,
                        "quarter": trim["date"],
                        "actual": actual,
                        "estimate": est,
                        "surprise_pct": float(surp_pct),
                        "reported_ts": report_ts,
                    })
                ok = True
                time.sleep(1.0)
                break
            except Exception as e:
                # Evitar imprimir demasiado; solo avisar en el último intento
                time.sleep(RETRY_DELAY)
        if not ok:
            print(f"  {t}: skip tras {MAX_RETRIES} intentos")
        else:
            print(f"  {t}: ok")

    if not rows_anuncio:
        print("No se obtuvieron datos de earnings. Revisa la conexión/rate-limit.")
        return

    df = pd.DataFrame(rows_anuncio)
    print(f"Datos de earnings obtenidos: {len(df)} trimestres-ticker\n")

    # --- Analizar: sorpresa (surprise) ~ señal; siguiente movimiento lo medimos con precios
    # Para el IC, correlacionamos surprise_pct de un trimestre con retorno post-anuncio
    # Necesitamos los precios para medir el "drift" real, pero la fecha de reporte
    # se usa para alinear. Aquí mostramos la distribución de sorpresas primero.

    print("=== DISTRIBUCIÓN DE SORPRESAS (% actual vs estimado) ===")
    print(df["surprise_pct"].describe().round(2))
    print("\nHistograma de sorpresas (¿centradas en 0 o sesgadas?):")
    bins = [-100, -10, -5, -1, 1, 5, 10, 100]
    print(pd.cut(df["surprise_pct"], bins).value_counts().sort_index().to_string())

    # IC de la sorpresa: si la sorpresa correlaciona con retorno futuro, hay PEAD
    # (aquí mostramos la señal; el retorno post-anuncio se añade en Fase A2 con precios)
    print("\n=== SEÑAL DEL PEAD ===")
    print("La sorpresa de earnings es la señal. En Fase A2 alinearemos con retorno post-anuncio")
    print("para calcular el IC real. Distribución por ticker (media de sorpresas):")
    print(df.groupby("ticker")["surprise_pct"].mean().round(2).to_string())

    # Guardar datos para Fase A2
    out = "/opt/data/qlib/work/estrategias/pead_earnings_data.csv"
    df.to_csv(out, index=False)
    print(f"\n✅ Datos guardados en {out}")

if __name__ == "__main__":
    main()
