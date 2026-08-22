"""FASE A2 — PEAD: calcular el IC entre la sorpresa de earnings y el retorno post-anuncio.

Objetivo: medir si el PEAD (post-earnings announcement drift) tiene alpha real:
cuando una empresa bate/falla el consenso (sorpresa), ¿el precio sigue derivando
en esa dirección los días/semanas posteriores al anuncio?

CRITERIO: si IC(sorpresa, retorno post-anuncio) > 0.02, el PEAD aporta alpha y se integra.

Fuente de earnings: CSV de la Fase A (pead_earnings_data.csv)
Fuente de precios: Qlib local (historia completa)
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
qlib.init(provider_uri=QLIB_URI, region='us')

# Retorno post-anuncio en días (el "drift" a medir)
FWD_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 20


def get_prices(ticker):
    """Series de precios reales (close/factor) para un ticker desde Qlib."""
    try:
        df = D.features([ticker], ["$close", "$factor"], start_time="2020-01-01",
                        end_time="2100-12-31", freq="day")
        if df is None or df.empty:
            return None
        c = df["$close"].unstack(level=0)
        f = df["$factor"].unstack(level=0)
        close = c[ticker] / f[ticker]
        close = close.dropna()
        return close.sort_index()
    except Exception:
        return None


def main():
    data_file = "/opt/data/qlib/work/estrategias/pead_earnings_data.csv"
    if not os.path.exists(data_file):
        print("No existe pead_earnings_data.csv. Ejecuta primero la Fase A.")
        return
    df = pd.read_csv(data_file)
    print(f"Datos de earnings: {len(df)} trimestres\n")

    # Añadir retorno post-anuncio para cada evento
    results = []
    used = 0
    for _, row in df.iterrows():
        tk = row["ticker"]
        report_ts = row["reported_ts"]
        events = get_prices(tk)
        if events is None or len(events) < FWD_DAYS + 10:
            continue
        # Fecha del anuncio
        report_date = pd.to_datetime(report_ts, unit="s", utc=True).tz_convert(None)
        # Buscar el índice de la fecha del anuncio (o la más próxima posterior)
        try:
            idx_date = events.index.asof(report_date)
            if pd.isna(idx_date):
                continue
        except Exception:
            continue
        pos = events.index.get_indexer([idx_date])[0]
        if pos + FWD_DAYS >= len(events):
            continue
        price_at = events.iloc[pos]
        price_fwd = events.iloc[pos + FWD_DAYS]
        ret_fwd = price_fwd / price_at - 1
        results.append({
            "ticker": tk,
            "quarter": row["quarter"],
            "surprise_pct": row["surprise_pct"],
            f"ret_{FWD_DAYS}d": ret_fwd,
        })
        used += 1

    if not results:
        print("No se pudieron calcular retornos post-anuncio.")
        return

    rdf = pd.DataFrame(results)
    print(f"Eventos con retorno post-anuncio calculado: {len(rdf)}\n")

    # --- IC del PEAD ---
    ic = rdf["surprise_pct"].corr(rdf[f"ret_{FWD_DAYS}d"])
    # IC no paramétrico (Spearman) más robusto
    sp = rdf["surprise_pct"].corr(rdf[f"ret_{FWD_DAYS}d"], method="spearman")

    print("="*56)
    print(f"📊 IC DEL PEAD (sorpresa → retorno post-anuncio {FWD_DAYS}d)")
    print("="*56)
    print(f"  Muestras: {len(rdf)}")
    print(f"  IC Pearson:  {ic:+.4f}")
    print(f"  IC Spearman: {sp:+.4f}")
    print()
    if ic > 0.02:
        print("  ✅ PEAD con alpha: la sorpresa predice el retorno post-anuncio")
        print("     → vale la pena integrar PEAD (Fase B)")
    elif ic > 0:
        print("  ⚠️ PEAD positivo pero débil")
    else:
        print("  ❌ Sin PEAD: la sorpresa NO predice el retorno post-anuncio en este universo")

    # Long-short: alto surprise vs bajo surprise
    rdf["bin"] = pd.qcut(rdf["surprise_pct"], 3, labels=["bajo", "medio", "alto"], duplicates="drop")
    print("\nRetorno post-anuncio por tercil de sorpresa:")
    print(rdf.groupby("bin")[f"ret_{FWD_DAYS}d"].agg(["mean", "count"]).round(4).to_string())
    high = rdf[rdf["bin"] == "alto"][f"ret_{FWD_DAYS}d"].mean()
    low = rdf[rdf["bin"] == "bajo"][f"ret_{FWD_DAYS}d"].mean()
    print(f"\n  Long-short (alto - bajo): {(high-low)*100:+.2f}% en {FWD_DAYS}d")

    # Guardar
    out = f"/opt/data/qlib/work/estrategias/pead_returns_{FWD_DAYS}d.csv"
    rdf.to_csv(out, index=False)
    print(f"\n✅ Datos guardados en {out}")


if __name__ == "__main__":
    main()
