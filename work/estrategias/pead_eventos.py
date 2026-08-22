"""Estrategia de eventos PEAD — validación directa.

Simula la operativa real: cuando una empresa anuncia resultados con sorpresa
positiva, se entra (1-5 días tras el anuncio) y se mantiene el drift (20-60 días).
Se mide el retorno medio, el % de veces que gana, y el IC del evento.

Esto valida la estrategia de eventos PEAD sin montar el DataHandler completo
(Fase B pragmática).
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
qlib.init(provider_uri=QLIB_URI, region='us')

FWD = int(sys.argv[1]) if len(sys.argv) > 1 else 20
ENTRY_DELAY = int(sys.argv[2]) if len(sys.argv) > 2 else 2   # días tras anuncio
SURPRISE_THRESHOLD = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0  # % mínimo de sorpresa


def get_prices_series(ticker, start="2020-01-01"):
    df = D.features([ticker], ["$close", "$factor"], start_time=start, end_time="2100-12-31", freq="day")
    if df is None or df.empty:
        return None
    c = df["$close"].unstack(level=0)
    f = df["$factor"].unstack(level=0)
    close = c[ticker] / f[ticker]
    return close.dropna().sort_index()


def main():
    ear = pd.read_csv("/opt/data/qlib/work/estrategias/pead_earnings_data.csv")
    ear["date"] = pd.to_datetime(ear["reported_ts"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
    print(f"Eventos de earnings: {len(ear)}")

    # Filtrar solo sorpresas por encima del umbral (nuestras entradas)
    entries = ear[ear["surprise_pct"] >= SURPRISE_THRESHOLD].copy()
    print(f"Entradas (sorpresa ≥ +{SURPRISE_THRESHOLD}%): {len(entries)}\n")

    results = []
    for _, row in entries.iterrows():
        tk = row["ticker"]
        prices = get_prices_series(tk)
        if prices is None or len(prices) < FWD + ENTRY_DELAY + 10:
            continue
        ann_date = row["date"]
        # Índice del anuncio en la serie de precios
        idx = prices.index.asof(ann_date)
        if pd.isna(idx):
            continue
        pos = prices.index.get_indexer([idx])[0]
        # Entrada ENTRY_DELAY días después del anuncio
        if pos + ENTRY_DELAY + FWD >= len(prices):
            continue
        entry_price = prices.iloc[pos + ENTRY_DELAY]
        exit_price = prices.iloc[pos + ENTRY_DELAY + FWD]
        ret = exit_price / entry_price - 1
        results.append({"ticker": tk, "quarter": row["quarter"],
                        "surprise": row["surprise_pct"], f"ret_{FWD}d": ret})

    if not results:
        print("No se pudieron validar entradas (datos insuficientes).")
        return
    rdf = pd.DataFrame(results)
    print("="*60)
    print(f"📊 ESTRATEGIA DE EVENTOS PEAD — entrada {ENTRY_DELAY}d tras anuncio, hold {FWD}d")
    print(f"   Umbral sorpresa: ≥ +{SURPRISE_THRESHOLD}%\n")
    print("="*60)
    print(f"  Operaciones:      {len(rdf)}")
    print(f"  Retorno medio:    {rdf[f'ret_{FWD}d'].mean()*100:+.2f}%")
    print(f"  Retorno mediano:  {rdf[f'ret_{FWD}d'].median()*100:+.2f}%")
    print(f"  % positivas:      {(rdf[f'ret_{FWD}d']>0).mean()*100:.1f}%")
    print(f"  Sharpe (evento):  {rdf[f'ret_{FWD}d'].mean()/rdf[f'ret_{FWD}d'].std():.3f}")
    print(f"  Mejor operación:  {rdf[f'ret_{FWD}d'].max()*100:+.2f}%")
    print(f"  Peor operación:   {rdf[f'ret_{FWD}d'].min()*100:+.2f}%")

    # IC dentro de la estrategia: la sorpresa importa entre las que ya entraron?
    ic = rdf["surprise"].corr(rdf[f"ret_{FWD}d"], method="spearman")
    print(f"\n  IC Spearman (sorpresa→ret, dentro de entradas): {ic:+.4f}")

    out = f"/opt/data/qlib/work/estrategias/pead_eventos_{FWD}d_th{SURPRISE_THRESHOLD}.csv"
    rdf.to_csv(out, index=False)
    print(f"\n✅ Datos guardados en {out}")


if __name__ == "__main__":
    main()
