"""audit_momentum_alpha.py — ¿El ranking de momentum APORTA algo?

PREGUNTA QUE RESPONDE
    El IC cross-sectional del momentum es ~0 (o negativo) a los horizontes
    en que opera la estrategia (30d). Pero el IC mide correlacion lineal de
    RANGO, y una estrategia top-30 es de SELECCION DE COLA: puede ganar por
    unas pocas posiciones ganadoras aunque el IC promedio sea cero.

    Entonces la pregunta correcta no es "¿hay IC?" sino:
        **¿el top-30 bate a 30 acciones elegidas AL AZAR del mismo universo?**

    Comparar contra un indice (^NDX, S&P) mezcla seleccion con beta y con
    diferencias de volatilidad. Comparar contra carteras aleatorias del
    MISMO universo y MISMO tamano aisla la habilidad de seleccion.

DISENO
    1. Cartera TOP: en cada rebalanceo semanal, las 30 con mayor momentum 120d.
    2. Carteras RANDOM: 300 carteras de 30 tickers al azar, mismo calendario
       de rebalanceo, mismos costes. Se obtiene la DISTRIBUCION de resultados
       que se lograria SIN habilidad de seleccion.
    3. Cartera BOTTOM: las 30 con menor momentum (control de signo). Si el
       bottom bate al top, la senal esta invertida.

    El top debe superar el percentil 95 de la distribucion aleatoria para
    afirmar que el ranking aporta con ~5% de significancia.

COSTES
    5 bps por turnover (aproxima IB). Se cobra al cambiar de cartera.

USO
    conda run -n qlib python work/estrategias/audit_momentum_alpha.py
    conda run -n qlib python work/estrategias/audit_momentum_alpha.py --n-random 500
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "simulation"))

MOM_W = 120
TOPK = 30
START = "2018-01-01"
END = "2026-10-22"
COST_BPS = 5.0


def load_prices() -> pd.DataFrame:
    import qlib
    from qlib.data import D

    from rutas_entorno import get_qlib_uri, get_universe

    uri = get_qlib_uri()
    print(f"  provider_uri: {uri}")
    qlib.init(provider_uri=uri, region="us",
              kernels=int(os.environ.get("QLIB_KERNELS", "1")))
    tickers = get_universe(verbose=True)
    df = D.features(tickers, ["$close", "$factor"], start_time=START,
                    end_time=END, freq="day")
    c = df["$close"].unstack(level=0).sort_index()
    f = df["$factor"].unstack(level=0).sort_index()
    px = (c / f).dropna(axis=0, thresh=int(0.5 * c.shape[1]))
    # tickers con historia suficiente
    px = px.loc[:, px.notna().sum() > 250]
    return px


def weekly_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Ultimo dia habil de cada semana ISO (el rebalanceo)."""
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(
        s.groupby([index.isocalendar().year, index.isocalendar().week]).max()
    )


def simulate(px: pd.DataFrame, weights_by_date: dict,
             cost_bps: float) -> pd.Series:
    """Valor de la cartera con rebalanceo en las fechas dadas. VECTORIZADO.

    weights_by_date: {fecha_rebalanceo: {ticker: peso}}

    Implementacion vectorizada (la version con .loc por posicion tardaba
    horas con 300 carteras). Logica identica:
      - Cada fecha usa los pesos del ULTIMO rebalanceo <= fecha (sin
        look-ahead: los pesos se fijan con datos de ese dia).
      - Turnover = 0.5*sum|w_nuevo - w_viejo|, cobrado el dia del rebalanceo.
    """
    tickers = list(px.columns)
    idx = {t: i for i, t in enumerate(tickers)}
    fechas = px.index
    D, T = len(fechas), len(tickers)

    # matriz de retornos (0 en el primer dia / NaN)
    rets = px.pct_change().to_numpy(dtype=float)
    rets = np.nan_to_num(rets, nan=0.0)

    reb = sorted(weights_by_date)
    if not reb:
        return pd.Series(dtype=float)

    # matriz de pesos (R x T)
    R = len(reb)
    W = np.zeros((R, T))
    for k, dia in enumerate(reb):
        for t, w in weights_by_date[dia].items():
            j = idx.get(t)
            if j is not None:
                W[k, j] = w

    # A que rebalanceo pertenece cada fecha.
    #
    # CRITICO (bug corregido 2026-10-27): side="left" - 1, NO "right".
    #   Con "right", el dia del rebalanceo d usaba los pesos NUEVOS, formados
    #   con el momentum que incluye el cierre de d. Pero el retorno de d ya
    #   ocurrio: se estaba aplicando a la rentabilidad pasada una cartera
    #   decidida con informacion de ese mismo cierre -> look-ahead de 1 dia.
    #   El test sintetico lo delato: en un mercado ALEATORIO el top-30 sacaba
    #   percentil 100 (Sharpe +1.08 vs azar -0.46), imposible sin fuga.
    #   Con "left"-1, el dia d usa los pesos ANTERIORES y los nuevos empiezan
    #   a aplicarse al dia siguiente. Se opera al cierre de d.
    reb_arr = np.array([fechas.get_loc(d) for d in reb])
    active = np.searchsorted(reb_arr, np.arange(D), side="left") - 1
    valid = active >= 0

    # retorno de cartera por dia: w . r  (vectorizado)
    port = np.zeros(D)
    port[valid] = (W[active[valid]] * rets[valid]).sum(axis=1)

    # costes de turnover en cada rebalanceo
    tv = np.zeros(R)
    for k in range(1, R):
        tv[k] = 0.5 * np.abs(W[k] - W[k - 1]).sum()
    costes = np.zeros(D)
    for k in range(1, R):
        costes[reb_arr[k]] = tv[k] * (cost_bps / 10000.0)

    out = port - costes
    # descartar el tramo previo al primer rebalanceo
    primero = reb_arr[0]
    return pd.Series(out[primero:], index=fechas[primero:])


def metricas(rets: pd.Series) -> dict:
    """CAGR, vol, Sharpe, maxDD a partir de retornos diarios."""
    if len(rets) < 50:
        return {}
    cum = (1 + rets).cumprod()
    años = len(rets) / 252.0
    cagr = cum.iloc[-1] ** (1 / años) - 1 if años > 0 else float("nan")
    vol = rets.std() * np.sqrt(252)
    sharpe = (rets.mean() * 252) / vol if vol > 0 else float("nan")
    dd = (cum / cum.cummax() - 1).min()
    return {"cagr": float(cagr), "vol": float(vol),
            "sharpe": float(sharpe), "maxdd": float(dd),
            "total": float(cum.iloc[-1] - 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-random", type=int, default=300)
    ap.add_argument("--topk", type=int, default=TOPK)
    ap.add_argument("--out", default=str(HERE / "audit_momentum_alpha.json"))
    args = ap.parse_args()

    topk = args.topk
    print("=" * 78)
    print(" ¿EL RANKING DE MOMENTUM APORTA ALGO?")
    print("=" * 78)
    print(f"  momentum {MOM_W}d | top-{topk} | costes {COST_BPS:.0f}bps "
          f"| {START} -> {END}")
    print(f"  control aleatorio: {args.n_random} carteras de {topk} al azar")

    px = load_prices()
    print(f"  cierres: {px.shape[0]} fechas x {px.shape[1]} tickers")

    mom = px / px.shift(MOM_W) - 1
    reb = weekly_dates(px.index)
    print(f"  rebalanceos semanales: {len(reb)}")

    rng = np.random.default_rng(20261027)

    # --- construir pesos por fecha para cada estrategia ---
    def pesos_por_ranking(signo: int) -> dict:
        out = {}
        for dia in reb:
            if dia not in mom.index:
                continue
            m = mom.loc[dia].dropna()
            if len(m) < topk * 2:
                continue
            sel = m.sort_values(ascending=(signo < 0)).index[:topk]
            out[dia] = {t: 1.0 / topk for t in sel}
        return out

    def pesos_random() -> dict:
        out = {}
        for dia in reb:
            if dia not in mom.index:
                continue
            m = mom.loc[dia].dropna()
            if len(m) < topk * 2:
                continue
            sel = rng.choice(m.index.to_numpy(), size=topk, replace=False)
            out[dia] = {t: 1.0 / topk for t in sel}
        return out

    def pesos_ew_universo() -> dict:
        """Equal-weight de TODO el universo (benchmark practico)."""
        out = {}
        for dia in reb:
            if dia not in mom.index:
                continue
            m = mom.loc[dia].dropna()
            if len(m) < topk * 2:
                continue
            w = 1.0 / len(m)
            out[dia] = {t: w for t in m.index}
        return out

    print("\n  Simulando TOP...")
    r_top = simulate(px, pesos_por_ranking(+1), COST_BPS)
    print("  Simulando BOTTOM (control de signo)...")
    r_bot = simulate(px, pesos_por_ranking(-1), COST_BPS)
    print("  Simulando EQUAL-WEIGHT del universo...")
    r_ew = simulate(px, pesos_ew_universo(), COST_BPS)

    print(f"  Simulando {args.n_random} carteras aleatorias...")
    rnd = []
    for k in range(args.n_random):
        r = simulate(px, pesos_random(), COST_BPS)
        if len(r) > 50:
            rnd.append(metricas(r))
        if (k + 1) % 50 == 0:
            print(f"    {k+1}/{args.n_random}")

    m_top = metricas(r_top)
    m_bot = metricas(r_bot)
    m_ew = metricas(r_ew)
    sh_rnd = np.array([d["sharpe"] for d in rnd], dtype=float)
    cg_rnd = np.array([d["cagr"] for d in rnd], dtype=float)

    print("\n" + "=" * 78)
    print(" RESULTADOS")
    print("=" * 78)
    print(f"  {'cartera':<26} {'CAGR':>9} {'vol':>8} {'Sharpe':>8} {'maxDD':>9}")
    print("  " + "-" * 62)
    for nm, m in [("TOP-30 momentum", m_top),
                  ("BOTTOM-30 (inverso)", m_bot),
                  (f"EW universo ({px.shape[1]})", m_ew)]:
        print(f"  {nm:<26} {100*m['cagr']:>8.1f}% {100*m['vol']:>7.1f}% "
              f"{m['sharpe']:>8.2f} {100*m['maxdd']:>8.1f}%")
    print(f"  {'aleatoria-30 (mediana)':<26} {100*np.median(cg_rnd):>8.1f}% "
          f"{'—':>8} {np.median(sh_rnd):>8.2f} {'—':>9}")

    # --- donde cae el top en la distribucion aleatoria ---
    p_sh = float((sh_rnd < m_top["sharpe"]).mean() * 100)
    p_cg = float((cg_rnd < m_top["cagr"]).mean() * 100)
    print(f"\n  El TOP-30 esta en el percentil {p_sh:.0f} de Sharpe "
          f"y {p_cg:.0f} de CAGR vs carteras aleatorias.")
    print(f"  Distribucion aleatoria de Sharpe: "
          f"p05={np.percentile(sh_rnd,5):.2f} p50={np.percentile(sh_rnd,50):.2f} "
          f"p95={np.percentile(sh_rnd,95):.2f}")

    print("\n" + "=" * 78)
    print(" VEREDICTO")
    print("=" * 78)
    if p_sh >= 95:
        print(f"  >> El ranking APORTA: el TOP-30 supera el p95 de las")
        print(f"     carteras aleatorias (percentil {p_sh:.0f}).")
    elif p_sh >= 80:
        print(f"  >> Indicio debil: percentil {p_sh:.0f}. El ranking podria")
        print(f"     aportar algo, pero no es concluyente.")
    elif p_sh >= 20:
        print(f"  >> El ranking NO aporta: percentil {p_sh:.0f}. El TOP-30 es")
        print(f"     indistinguible de elegir 30 acciones al azar.")
        print(f"     >>> El retorno del backtest es BETA, no seleccion.")
    else:
        print(f"  >> El ranking PERJUDICA: percentil {p_sh:.0f}. El TOP-30")
        print(f"     queda por debajo de la mayoria de carteras aleatorias.")

    # control de signo
    if m_bot["sharpe"] > m_top["sharpe"]:
        print(f"\n  ADEMAS: el BOTTOM-30 (inverso) tiene mejor Sharpe que el TOP")
        print(f"  ({m_bot['sharpe']:.2f} vs {m_top['sharpe']:.2f}). La senal")
        print(f"  estaria INVERTIDA en este periodo.")

    out = {
        "fecha": pd.Timestamp.now().isoformat(),
        "momentum_dias": MOM_W, "topk": topk, "cost_bps": COST_BPS,
        "periodo": [START, END], "tickers": int(px.shape[1]),
        "top": m_top, "bottom": m_bot, "ew_universo": m_ew,
        "random": {
            "n": len(rnd),
            "sharpe_p05": float(np.percentile(sh_rnd, 5)),
            "sharpe_p50": float(np.percentile(sh_rnd, 50)),
            "sharpe_p95": float(np.percentile(sh_rnd, 95)),
            "cagr_p50": float(np.percentile(cg_rnd, 50)),
            "percentil_top_sharpe": p_sh,
            "percentil_top_cagr": p_cg,
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                         default=float), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
