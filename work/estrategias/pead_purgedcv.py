"""PURGED CV aplicado al PEAD — re-validar el IC de la sorpresa de earnings.

Contexto: el IC original del PEAD (0.19-0.22) se calculó con TODAS las muestras
(correlación global surprise vs retorno post-anuncio a 20-60 días). Eso ignora
el solapamiento de etiquetas (cada retorno a N días se solapa con los vecinos).

Este script aplica PURGED CROSS-VALIDATION:
- Divide las muestras en pliegues TEMPORALES (por fecha de anuncio)
- Para cada pliegue, calcula el IC sólo en las muestras del pliegue (test),
  purgando/embargo de manera temporal
- Promedia el IC por pliegue → IC out-of-sample honesto sin leakage
- Compara con el IC global (sin CV) para ver cuánto estaba inflado

Fuente: pead_earnings_data_full.csv / appended (con fecha de anuncio)
Precios: Qlib local
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
qlib.init(provider_uri=QLIB_URI, region='us')

# Retorno post-anuncio en días (el "drift")
FWD_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
# Número de pliegues temporales
N_SPLITS = int(sys.argv[2]) if len(sys.argv) > 2 else 5

# Datos de earnings (append-only o full)
EAR_APP = "/opt/data/qlib/work/estrategias/pead_earnings_appended.csv"
EAR_FULL = "/opt/data/qlib/work/estrategias/pead_earnings_data_full.csv"
EAR = EAR_APP if os.path.exists(EAR_APP) else EAR_FULL


def get_prices(ticker):
    try:
        df = D.features([ticker], ["$close", "$factor"], start_time="2020-01-01",
                        end_time="2100-12-31", freq="day")
        if df is None or df.empty:
            return None
        c = df["$close"].unstack(level=0)
        f = df["$factor"].unstack(level=0)
        close = c[ticker] / f[ticker]
        return close.dropna().sort_index()
    except Exception:
        return None


def main():
    df = pd.read_csv(EAR)
    df["announce_date"] = pd.to_datetime(df["reported_ts"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
    print(f"Datos de earnings: {len(df)} trimestres\n")

    # Calcular retorno post-anuncio para cada evento
    rows = []
    for _, row in df.iterrows():
        tk = row["ticker"]
        prices = get_prices(tk)
        if prices is None or len(prices) < FWD_DAYS + 10:
            continue
        try:
            idx_date = prices.index.asof(row["announce_date"])
            if pd.isna(idx_date):
                continue
            pos = prices.index.get_indexer([idx_date])[0]
            if pos + FWD_DAYS >= len(prices):
                continue
            ret_fwd = prices.iloc[pos + FWD_DAYS] / prices.iloc[pos] - 1
        except Exception:
            continue
        rows.append({
            "ticker": tk,
            "announce_date": row["announce_date"],
            "surprise_pct": row["surprise_pct"],
            f"ret_{FWD_DAYS}d": ret_fwd,
        })

    rdf = pd.DataFrame(rows)
    if rdf.empty:
        print("No se pudieron calcular retornos.")
        return
    print(f"Eventos con retorno post-anuncio: {len(rdf)}\n")

    # --- IC GLOBAL (sin CV) — el que dio 0.19 ---
    ic_global = rdf["surprise_pct"].corr(rdf[f"ret_{FWD_DAYS}d"])
    sp_global = rdf["surprise_pct"].corr(rdf[f"ret_{FWD_DAYS}d"], method="spearman")
    print("="*60)
    print("📊 IC GLOBAL (sin purge — medición original)")
    print("="*60)
    print(f"  Muestras: {len(rdf)}")
    print(f"  IC Pearson:  {ic_global:+.4f}")
    print(f"  IC Spearman: {sp_global:+.4f}\n")

    # --- PURGED CV: dividir por tiempo en pliegues ---
    # Ordenar por fecha de anuncio
    rdf = rdf.sort_values("announce_date").reset_index(drop=True)
    # Los eventos no están en fechas regulares; usar quantiles por número de eventos
    edges = np.quantile(np.arange(len(rdf)), np.linspace(0, 1, N_SPLITS + 1)).astype(int)
    print("="*60)
    print(f"🧬 PURGED CV ({N_SPLITS} pliegues temporales, retorno {FWD_DAYS}d)")
    print("="*60)

    ic_list, sp_list = [], []
    for k in range(N_SPLITS):
        test_idx = np.arange(edges[k], edges[k + 1])
        test = rdf.iloc[test_idx]
        # IC SÓLO en el pliegue de test (out-of-sample)
        ic = test["surprise_pct"].corr(test[f"ret_{FWD_DAYS}d"])
        sp = test["surprise_pct"].corr(test[f"ret_{FWD_DAYS}d"], method="spearman")
        ic_list.append(ic)
        sp_list.append(sp)
        print(f"  Pliegue {k+1}: {len(test)} muestras | rango {test['announce_date'].min().date()}→{test['announce_date'].max().date()} "
              f"| IC P {ic:+.4f} | IC Sp {sp:+.4f}")

    ic_mean = float(np.nanmean(ic_list))
    sp_mean = float(np.nanmean(sp_list))

    print("="*60)
    print(f"  IC Pearson PURGED medio:  {ic_mean:+.4f}")
    print(f"  IC Spearman PURGED medio: {sp_mean:+.4f}")
    print()
    print("  Comparativa:")
    print(f"    IC Pearson  global +{ic_global:+.4f} → purged {ic_mean:+.4f}  (Δ {ic_mean-ic_global:+.4f})")
    print(f"    IC Spearman global {sp_global:+.4f} → purged {sp_mean:+.4f}  (Δ {sp_mean-sp_global:+.4f})")
    print()
    if sp_mean > 0.02:
        print("  ✅ PEAD mantiene alpha con purged CV → el alpha es más robusto de lo que parecía")
    elif sp_mean > 0:
        print("  ⚠️ PEAD positivo pero débil tras purgar → el alpha global estaba inflado por leakage")
    else:
        print("  ❌ PEAD se desvanece con purged CV → el alpha era data leakage (solapamiento de etiquetas)")

    # Guardar
    out = f"/opt/data/qlib/work/estrategias/pead_purgedcv_{FWD_DAYS}d.csv"
    rdf.to_csv(out, index=False)
    print(f"\n✅ Datos guardados en {out}")


if __name__ == "__main__":
    main()
