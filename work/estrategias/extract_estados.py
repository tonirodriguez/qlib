"""extract_estados.py — Construir la serie temporal de ESTADOS de mercado.

Según el plan de Quinn (plan_E3_quinn_futuro.md, Semana 2):
Serie de estados que alimentará regimen_test.py (semana 3-4) para demostrar
(o descartar) la dependencia de régimen del momentum de forma rigurosa.

Indicadores por fecha:
1. vol_pct    : percentil de la vol realizada 20d del índice (histórico rolante).
2. drawdown120: mercado en drawdown (retorno 120d del índice < 0) → 0/1
3. mom_crash  : indicador de momentum-crash (decil perdedor > decil ganador)
   (estilo Daniel-Moskowitz: los "perdedores" rinden más que los "ganadores")

Salida: work/estrategias/estados_mercado.csv (index=fecha)

Uso: python work/estrategias/extract_estados.py
"""
import os, sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
UNIVERSE = "sp500_liquid"
START = "2018-01-01"
END = "2026-08-01"
VOL_WIN = 20
MOM_CRASH_WIN = 120   # ventana para ranking moment.

# Índice de mercado: usaremos ^GSPC si está en Qlib, si no el promedio del universo
BENCH = "^GSPC"


def main():
    qlib.init(provider_uri=QLIB_URI, region='us')
    from qlib.data import D as _D
    tickers = _D.list_instruments(_D.instruments(UNIVERSE), as_list=True)

    # 1. Índice de mercado
    bench = None
    try:
        b = D.features([BENCH], ["$close", "$factor"], start_time=START, end_time=END, freq="day")
        if b is not None and not b.empty:
            c = b["$close"].unstack(level=0)
            f = b["$factor"].unstack(level=0)
            bench = (c[BENCH] / f[BENCH]).dropna().sort_index()
    except Exception:
        bench = None

    if bench is None or len(bench) < VOL_WIN + 10:
        # fallback: promedio del universo
        close = D.features(tickers, ["$close", "$factor"], start_time=START, end_time=END, freq="day")
        c = close["$close"].unstack(level=0).sort_index()
        f = close["$factor"].unstack(level=0).sort_index()
        prices = c / f
        bench = prices.mean(axis=1).dropna()
        print("Usando promedio del universo como proxy del mercado (no hay ^GSPC)")

    # 2. Retorno del índice para vol y drawdown
    idx_ret = bench / bench.shift(1) - 1
    vol = idx_ret.rolling(VOL_WIN).std() * np.sqrt(252)   # vol anualizada
    vol_pct = vol.rolling(252, min_periods=120).apply(
        lambda x: (x.iloc[-1] > x).mean(), raw=False
    ).rename("vol_pct") if len(vol) >= 252 else vol / vol.max()

    # drawdown 120d del índice (<0 => en drawdown)
    ret120 = bench / bench.shift(MOM_CRASH_WIN) - 1
    drawdown120 = (ret120 < 0).astype(int).rename("drawdown120")

    # 3. Indicador de momentum-crash (decil perdedor > decil ganador)
    #   Necesitamos cross-section de retornos 120d del universo
    close = D.features(tickers, ["$close", "$factor"], start_time=START, end_time=END, freq="day")
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    prices = c / f
    cross_ret = prices / prices.shift(MOM_CRASH_WIN) - 1
    # por fecha: retorno medio del decil ganador (top 10%) y perdedor (bottom 10%)
    def crash_indicator(row):
        r = row.dropna()
        if len(r) < 20:
            return np.nan
        q = r.rank(pct=True)
        losers = r[q <= 0.1].mean()
        winners = r[q >= 0.9].mean()
        return 1 if losers > winners else 0
    mom_crash = cross_ret.apply(crash_indicator, axis=1).rename("mom_crash")

    # 4. Tabla de estados
    estados = pd.concat([vol_pct, drawdown120, mom_crash], axis=1).replace([np.inf, -np.inf], np.nan)
    # GD: estados[".date"] con índice de tipo date
    if estados.index.tz is not None:
        estados.index = estados.index.tz_localize(None)
    estados = estados.dropna(subset=["vol_pct", "drawdown120"])
    print(f"Estados construidos: {len(estados)} fechas | rango {estados.index.min().date()} → {estados.index.max().date()}")

    # Guardar
    out = "/opt/data/qlib/work/estrategias/estados_mercado.csv"
    estados.to_csv(out)
    print(f"✅ Guardado en {out}")
    print(estados.tail(20).round(3).to_string())


if __name__ == "__main__":
    main()
