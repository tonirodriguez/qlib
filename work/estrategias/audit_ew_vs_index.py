"""audit_ew_vs_index.py — ¿El equal-weight bate al indice cap-weighted?

PREGUNTA
    El equal-weight del universo (292 tickers) es la unica base que sobrevivio
    a las auditorias. Pero nunca se comparo contra su competidor real:
    comprar el S&P 500 cap-weighted (^GSPC).

    Su competidor NO es "nada". Es el indice. Si no lo bate, el EW no es una
    mejora: es una apuesta factorial (sesgo de tamano/equiponderacion) que en
    esta decada pudo salir peor que simplemente comprar el indice.

CUIDADO TECNICO: DIVIDENDOS
    En qlib, `$close / $factor` es el precio AJUSTADO. Si `$factor` incluye
    dividendos (habitual en datos de Yahoo), el retorno ajustado es TOTAL
    RETURN. Pero ^GSPC suele venir con factor=1, es decir precio sin dividendos.

    Comparar EW-total-return contra ^GSPC-precio favorece al EW por el
    dividend yield (~1.5-2%/ano). Seria un sesgo a mi favor.

    Por eso se miden DOS comparaciones:
      (a) ajustado  : EW total return vs ^GSPC ajustado  (como vengan los datos)
      (b) precio    : EW precio vs ^GSPC precio  <- apples-to-apples

    La (b) es la que zanja la pregunta.

BENCHMARK INTERMEDIO
    Ademas del EW y el indice, se anade una cartera ponderada por LIQUIDEZ
    (volumen en dolares) del mismo universo. Es un punto intermedio entre
    equiponderar y capitalizar: si el EW bate al indice pero no a la
    ponderada por liquidez, la ganancia viene de sobreponderar nombres
    pequenos (sesgo de tamano), no de equiponderar en si.

USO
    conda run -n qlib python work/estrategias/audit_ew_vs_index.py
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
sys.path.insert(0, str(HERE))

START = "2018-01-01"
END = "2026-10-22"
COST_BPS = 5.0
BENCH = "^GSPC"


def cargar_datos(start: str, end: str):
    """Cierres ajustados y crudos del universo + benchmark + volumen."""
    import qlib
    from qlib.data import D

    from rutas_entorno import get_qlib_uri, get_universe

    uri = get_qlib_uri()
    print(f"  provider_uri: {uri}")
    qlib.init(provider_uri=uri, region="us",
              kernels=int(os.environ.get("QLIB_KERNELS", "1")))

    tickers = get_universe(verbose=True)

    campos = ["$close", "$factor", "$volume"]
    df = D.features(tickers, campos, start_time=start, end_time=end,
                    freq="day")
    close = df["$close"].unstack(level=0).sort_index()
    factor = df["$factor"].unstack(level=0).sort_index()
    vol = df["$volume"].unstack(level=0).sort_index()

    adj = (close / factor)
    adj = adj.dropna(axis=0, thresh=int(0.5 * adj.shape[1]))
    adj = adj.loc[:, adj.notna().sum() > 250]
    raw = close.reindex(columns=adj.columns)
    vol = vol.reindex(columns=adj.columns)

    # --- benchmark ---
    bench = None
    try:
        bdf = D.features([BENCH], campos, start_time=start, end_time=end,
                         freq="day")
        bclose = bdf["$close"].unstack(level=0).sort_index()
        bfactor = bdf["$factor"].unstack(level=0).sort_index()
        b_raw = bclose[BENCH].dropna()
        b_adj = (bclose / bfactor)[BENCH].dropna()
        bench = {"raw": b_raw, "adj": b_adj}
        print(f"  benchmark {BENCH}: {len(b_raw)} fechas, "
              f"{b_raw.index.min().date()} -> {b_raw.index.max().date()}")
        # ¿el factor del indice ajusta algo?
        f = bfactor[BENCH].dropna()
        print(f"  factor de {BENCH}: min {f.min():.4f} max {f.max():.4f} "
              f"(si es ~1.0, es PRECIO sin dividendos)")
    except Exception as exc:  # noqa: BLE001
        print(f"  AVISO: no se pudo cargar {BENCH}: {str(exc)[:120]}")

    return adj, raw, vol, bench


def identificar_series(px_a: pd.DataFrame, px_b: pd.DataFrame,
                       etiqueta_a: str = "$close",
                       etiqueta_b: str = "$close/$factor") -> dict:
    """Determina CUAL de las dos series es PRECIO y cual TOTAL RETURN.

    POR QUE NO SE PUEDE ASUMIR
        El primer intento asumio que `$close/$factor` era el ajustado (total
        return), siguiendo la convencion habitual de qlib. Es FALSO en estos
        datos: `$close` es el total return y `$close/$factor` es el precio.

        Consecuencia del error: se comparo EW-con-dividendos (13.9%) contra
        ^GSPC-sin-dividendos (12.6%) y el script concluyo "el EW bate al
        indice" cuando en la comparacion honesta (precio vs precio) el EW
        PIERDE (11.3% vs 12.6%).

    COMO SE DETERMINA
        Empiricamente: las series con dividendos acumulan MAS retorno. Se
        calcula el retorno del buy&hold equiponderado de cada una y la de
        mayor CAGR es la de TOTAL RETURN.

        Sanity check: la diferencia debe ser ~1-3%/ano (dividend yield tipico
        de un universo large/mid cap). Si la diferencia es minuscula, las dos
        series son equivalentes y da igual cual se use.
    """
    ca = float((px_a.pct_change(fill_method=None).mean(axis=1).add(1)
                .prod()) ** (252 / max(len(px_a), 1)) - 1)
    cb = float((px_b.pct_change(fill_method=None).mean(axis=1).add(1)
                .prod()) ** (252 / max(len(px_b), 1)) - 1)
    dif = ca - cb
    if ca >= cb:
        return {"precio": px_b, "total": px_a, "dif_pp": 100 * abs(dif),
                "etiqueta_precio": etiqueta_b, "etiqueta_total": etiqueta_a}
    return {"precio": px_a, "total": px_b, "dif_pp": 100 * abs(dif),
            "etiqueta_precio": etiqueta_a, "etiqueta_total": etiqueta_b}


def pesos_ew(px: pd.DataFrame) -> dict:
    from audit_momentum_alpha import weekly_dates
    out = {}
    for dia in weekly_dates(px.index):
        fila = px.loc[dia].dropna()
        if len(fila) < 20:
            continue
        w = 1.0 / len(fila)
        out[dia] = {t: w for t in fila.index}
    return out


def _cap_pesos(w: pd.Series, cap: float, max_iter: int = 50) -> pd.Series:
    """Limita el peso maximo REDISTRIBUYENDO el exceso (water-filling).

    Un clip simple NO sirve: al renormalizar despues, los pesos recortados
    vuelven a subir por encima del limite. Verificado: con 2 nombres de
    volumen 50x y 30x, clip(0.05)+renormalizar dejaba el maximo en 24.86%.

    Aqui se recorta y se reparte el exceso entre los NO recortados,
    iterando hasta que nadie supere el limite.
    """
    w = w.astype(float).copy()
    if w.sum() <= 0:
        return w
    w = w / w.sum()
    for _ in range(max_iter):
        sobre = w > cap + 1e-12
        if not sobre.any():
            break
        w[sobre] = cap
        libre = ~sobre
        resto = 1.0 - float(w[sobre].sum())
        if not libre.any() or resto <= 0:
            break
        s = float(w[libre].sum())
        if s <= 0:
            break
        w[libre] = w[libre] / s * resto
    return w


def pesos_liquidez(px: pd.DataFrame, vol: pd.DataFrame,
                   dias_rebal: int = 63) -> dict:
    """Ponderado por volumen en dolares medio 60d. Rebalanceo trimestral.

    Es un punto intermedio entre equiponderar y capitalizar: se aproxima al
    peso por tamano usando liquidez, que es lo que hay disponible.
    """
    dv = px.mul(vol)          # volumen en dolares (precio x volumen)
    adv = dv.rolling(60).mean()
    out = {}
    fechas = px.index[::dias_rebal]
    for dia in fechas:
        if dia not in adv.index:
            continue
        fila = adv.loc[dia].dropna()
        fila = fila[fila > 0]
        if len(fila) < 20:
            continue
        w = _cap_pesos(fila / fila.sum(), cap=0.05)
        out[dia] = w.to_dict()
    return out


def hhi(pesos: dict) -> dict:
    """Concentracion: HHI y numero efectivo de nombres (1/HHI)."""
    if not pesos:
        return {}
    ultimo = max(pesos)
    w = np.array(list(pesos[ultimo].values()), dtype=float)
    w = w / w.sum()
    h = float((w ** 2).sum())
    return {"n_nombres": int(len(w)), "hhi": h, "n_efectivo": float(1 / h),
            "peso_max": float(w.max())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    ap.add_argument("--out", default=str(HERE / "audit_ew_vs_index.json"))
    args = ap.parse_args()

    from audit_momentum_alpha import metricas, simulate
    from audit_vol_target import bootstrap_sharpe

    print("=" * 78)
    print(" ¿EL EQUAL-WEIGHT BATE AL INDICE CAP-WEIGHTED?")
    print("=" * 78)
    print(f"  {args.start} -> {args.end} | costes {COST_BPS:.0f}bps")

    adj, raw, vol, bench = cargar_datos(args.start, args.end)
    print(f"  universo: {adj.shape[1]} tickers x {adj.shape[0]} fechas")

    w_ew = pesos_ew(adj)
    w_lq = pesos_liquidez(adj, vol)

    # --- identificar EMPIRICAMENTE que serie es precio y cual total return ---
    ident = identificar_series(raw, adj)
    print("\n  identificacion de series (empirica, no por suposicion):")
    print(f"    total return : {ident['etiqueta_total']}")
    print(f"    precio       : {ident['etiqueta_precio']}")
    print(f"    diferencia   : {ident['dif_pp']:.2f}pp/ano "
          f"(deberia ser ~dividend yield, 1-3%)")
    if ident["dif_pp"] < 0.3:
        print("    AVISO: diferencia minuscula, las series son equivalentes")

    px_precio = ident["precio"]
    px_total = ident["total"]
    r_ew_precio = simulate(px_precio, w_ew, COST_BPS)
    r_ew_total = simulate(px_total, w_ew, COST_BPS)
    r_lq_precio = simulate(px_precio, w_lq, COST_BPS)

    print(f"\n  concentracion (ultimo rebalanceo):")
    for nm, w in [("EW", w_ew), ("liquidez", w_lq)]:
        h = hhi(w)
        print(f"    {nm:<10} {h['n_nombres']} nombres | n efectivo "
              f"{h['n_efectivo']:.1f} | peso max {100*h['peso_max']:.2f}%")

    if bench is None:
        print("\n  SIN BENCHMARK: no se puede responder la pregunta.")
        return 1

    # ^GSPC es un indice de PRECIO por definicion. Si su factor es constante,
    # las dos series dan lo mismo y no hay ambiguedad.
    r_b_raw = bench["raw"].pct_change(fill_method=None).dropna()
    r_b_adj = bench["adj"].pct_change(fill_method=None).dropna()
    print(f"\n  benchmark: ^GSPC es indice de PRECIO (no reparte dividendos)")

    # --- comparacion PRINCIPAL: PRECIO vs PRECIO, apples-to-apples ---
    print("\n" + "=" * 78)
    print(" COMPARACION PRINCIPAL — PRECIO vs PRECIO (justa)")
    print("=" * 78)
    print(f"  {'cartera':<28} {'CAGR':>9} {'vol':>8} {'Sharpe':>8} "
          f"{'maxDD':>9} {'Calmar':>7}")
    print("  " + "-" * 70)

    filas = {}
    for nm, r in [("EW (292, semanal)", r_ew_precio),
                  ("Liquidez (292, trim.)", r_lq_precio),
                  (f"{BENCH} (cap-weighted)", r_b_raw)]:
        m = metricas(r)
        if not m:
            continue
        calmar = m["cagr"] / abs(m["maxdd"]) if m["maxdd"] else float("nan")
        filas[nm] = {**m, "calmar": calmar}
        print(f"  {nm:<28} {100*m['cagr']:>8.1f}% {100*m['vol']:>7.1f}% "
              f"{m['sharpe']:>8.2f} {100*m['maxdd']:>8.1f}% {calmar:>7.2f}")

    # --- test: EW vs indice ---
    print("\n" + "=" * 78)
    print(" TEST — EW vs INDICE (precio vs precio)")
    print("=" * 78)
    bs = bootstrap_sharpe(r_ew_precio, r_b_raw, n_boot=2000, block=20)
    print(f"  delta Sharpe (EW - indice): {bs['delta']:+.3f}")
    print(f"  IC95: {bs['ic95_lo']:+.3f} .. {bs['ic95_hi']:+.3f}   "
          f"p={bs['p_valor']:.3f}")

    m_ew = filas.get("EW (292, semanal)", {})
    m_b = filas.get(f"{BENCH} (cap-weighted)", {})
    if m_ew and m_b:
        d_cagr = m_ew["cagr"] - m_b["cagr"]
        d_dd = (m_ew["maxdd"] - m_b["maxdd"]) * 100
        print(f"\n  CAGR:  EW {100*m_ew['cagr']:.1f}% vs indice "
              f"{100*m_b['cagr']:.1f}%  -> {100*d_cagr:+.1f}pp/ano")
        print(f"  maxDD: EW {100*m_ew['maxdd']:.1f}% vs indice "
              f"{100*m_b['maxdd']:.1f}%  -> {d_dd:+.1f}pp")
        print(f"  Calmar: EW {m_ew['calmar']:.2f} vs indice "
              f"{m_b['calmar']:.2f}")

    # --- benchmark intermedio: ¿la ganancia es sesgo de tamano? ---
    print("\n" + "=" * 78)
    print(" ¿De donde viene la diferencia? EW vs ponderada por liquidez")
    print("=" * 78)
    m_lq = filas.get("Liquidez (292, trim.)", {})
    if m_lq and m_ew:
        print(f"  EW      CAGR {100*m_ew['cagr']:.1f}% Sharpe {m_ew['sharpe']:.2f}")
        print(f"  Liquidez CAGR {100*m_lq['cagr']:.1f}% Sharpe {m_lq['sharpe']:.2f}")
        d = m_ew["sharpe"] - m_lq["sharpe"]
        if d > 0.05:
            print("  -> El EW bate a la ponderada por liquidez: equiponderar")
            print("     aporta algo mas que sobreponderar nombres pequenos.")
        elif d < -0.05:
            print("  -> El EW PIERDE contra la ponderada por liquidez: su")
            print("     ventaja (si la hay) viene del sesgo de tamano, no de")
            print("     la equiponderacion.")
        else:
            print("  -> Sin diferencia apreciable: el metodo de ponderacion")
            print("     no es lo que explica el resultado.")

    # --- referencia: total return del EW (el indice no lo tiene) ---
    print("\n" + "=" * 78)
    print(" REFERENCIA — TOTAL RETURN del EW (el indice NO reparte dividendos)")
    print("=" * 78)
    m_ew_t = metricas(r_ew_total)
    if m_ew_t and m_ew:
        print(f"  EW total return : CAGR {100*m_ew_t['cagr']:.1f}% "
              f"Sharpe {m_ew_t['sharpe']:.2f}")
        print(f"  EW precio       : CAGR {100*m_ew['cagr']:.1f}% "
              f"Sharpe {m_ew['sharpe']:.2f}")
        print(f"  diferencia      : {100*(m_ew_t['cagr']-m_ew['cagr']):+.1f}pp "
              f"(dividendos)")
        print(f"\n  OJO: NO se compara contra el indice en esta base. Seria")
        print(f"  comparar EW-con-dividendos contra indice-sin-dividendos, que")
        print(f"  es el sesgo que invalidaba la primera version de este test.")

    # --- veredicto ---
    print("\n" + "=" * 78)
    print(" VEREDICTO (sobre la comparacion justa: precio vs precio)")
    print("=" * 78)
    if m_ew and m_b:
        gana_sharpe = bs["delta"] > 0 and bs["p_valor"] < 0.05
        gana_cagr = m_ew["cagr"] > m_b["cagr"]
        if gana_sharpe and gana_cagr:
            print("  >> El EW BATE al indice en retorno y en Sharpe, con")
            print("     significancia. Vehiculo defendible.")
        elif gana_cagr and bs["delta"] > 0:
            print("  >> El EW bate en retorno y Sharpe, pero SIN significancia.")
            print("     Sugerente, no concluyente.")
        elif gana_cagr:
            print("  >> El EW bate en retorno bruto pero NO en Sharpe:")
            print("     gana asumiendo mas riesgo.")
        else:
            print("  >> El EW NO bate al indice en la comparacion justa.")
            print("     Es una apuesta factorial (equiponderacion/sesgo de")
            print("     tamano) que en este periodo salio PEOR que comprar")
            print("     el indice.")
            print()
            print("     Si el objetivo es exposicion: comprar el indice.")
            print("     Si el objetivo es menos concentracion: el EW sirve")
            print("     como vehiculo, pero SIN ventaja de retorno.")
            print()
            print("     Nota: el EW reduce el peso maximo del 0.35% por nombre")
            print(f"     (n efectivo {hhi(w_ew).get('n_efectivo', 0):.0f}) frente a la")
            print("     concentracion del indice. Ese es su unico argumento.")

    out = {
        "fecha": pd.Timestamp.now().isoformat(),
        "periodo": [args.start, args.end],
        "tickers": int(adj.shape[1]), "benchmark": BENCH,
        "identificacion_series": {
            "serie_total": ident["etiqueta_total"],
            "serie_precio": ident["etiqueta_precio"],
            "diferencia_pp": ident["dif_pp"],
        },
        "comparacion_precio": filas,
        "test_ew_vs_indice": bs,
        "ew_total_return": m_ew_t,
        "concentracion": {"ew": hhi(w_ew), "liquidez": hhi(w_lq)},
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                         default=float), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
