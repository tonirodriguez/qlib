"""audit_vol_target.py — ¿El vol-targeting aporta sobre el equal-weight?

CONTEXTO
    Es la ultima linea con fundamento del proyecto. El resto se descarto:
      - momentum 120d: percentil 57 vs carteras aleatorias (sin edge)
      - PEAD: no backtesteable (Yahoo solo da 1 ano de earnings)
      - crypto: 9 monedas, insuficiente para seccion cruzada
      - Jev: descartado

    El vol-gate mostro un efecto REAL sobre drawdown en la arquitectura E3
    (-41.0% -> -33.4%), pero el Sharpe apenas cambia (+0.017 = ruido).

    La pregunta ahora: ¿el vol-TARGETING (continuo, no por umbrales) mejora
    el perfil riesgo-retorno del equal-weight?

POR QUE ESTE TEST SI TIENE POTENCIA
    El problema del momentum era que el dataset no distingue un IC de 0.03 de
    cero (~17 obs independientes a 120d). Aqui NO se busca un alpha pequeno:
    se mide un efecto de GESTION DE RIESGO sobre retornos diarios, donde hay
    ~2.200 observaciones y los efectos son grandes. La relacion senal/ruido
    es incomparablemente mejor.

DISENO
    Base: equal-weight del universo (283 tickers), rebalanceo semanal.
    Encima: exposicion dinamica

        e_t = clip(target_vol / vol_realizada_{t-1}, 0, max_lev)

    donde vol_realizada se calcula con los retornos HASTA t-1 (sin look-ahead).

    Variantes:
      A) EW puro                 (exposicion 1.0 constante)
      B) VT con max_lev=1.0      (solo des-riesga; exposicion media < 1)
      C) VT con max_lev=2.0      (puede apalancar; exposicion media ~1)
      D) Escalado constante      (control: misma exposicion media que B, fija)

EL CONTROL ES LA CLAVE
    Escalar la exposicion por una CONSTANTE no cambia el Sharpe (es una
    transformacion lineal). Asi que si el VT mejora el Sharpe frente a A, la
    mejora viene del TIMING de la exposicion, no de estar menos invertido.

    Y si mejora el drawdown pero NO el Sharpe, entonces solo esta reduciendo
    riesgo en proporcion a la exposicion media: eso ya lo consigue D sin
    necesidad de ninguna senal de volatilidad.

USO
    conda run -n qlib python work/estrategias/audit_vol_target.py
    conda run -n qlib python work/estrategias/audit_vol_target.py --selftest
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


def pesos_equal_weight(px: pd.DataFrame) -> dict:
    """Equal-weight de todos los tickers con dato en cada rebalanceo semanal."""
    from audit_momentum_alpha import weekly_dates
    out = {}
    for dia in weekly_dates(px.index):
        fila = px.loc[dia].dropna()
        if len(fila) < 20:
            continue
        w = 1.0 / len(fila)
        out[dia] = {t: w for t in fila.index}
    return out


def aplicar_vol_target(r_ew: pd.Series, target_vol: float, ventana: int,
                       max_lev: float, cost_bps: float) -> tuple[pd.Series, pd.Series]:
    """Aplica exposicion dinamica a los retornos del EW.

    SIN LOOK-AHEAD: la volatilidad usada en t se calcula con retornos hasta
    t-1 (rolling().shift(1)). El retorno de t se escala por la exposicion
    decidida con informacion de t-1.
    """
    vol = r_ew.rolling(ventana).std().shift(1) * np.sqrt(252)
    vol = vol.replace(0, np.nan)
    e = (target_vol / vol).clip(0, max_lev)
    # exposicion 1.0 mientras no haya historico suficiente
    e = e.fillna(1.0)
    r_vt = e * r_ew
    # coste de cambiar la exposicion (entrar/salir es operar)
    de = e.diff().abs().fillna(0.0)
    r_vt = r_vt - de * (cost_bps / 10000.0)
    return r_vt, e


def metricas_ext(r: pd.Series, e: pd.Series | None = None) -> dict:
    from audit_momentum_alpha import metricas
    m = metricas(r)
    if not m:
        return {}
    if e is not None:
        m["exposicion_media"] = float(e.mean())
        m["exposicion_min"] = float(e.min())
        m["exposicion_max"] = float(e.max())
        m["pct_des_riesgado"] = float((e < 0.99).mean())
    return m


def t_stat_serie(r: pd.Series, lag: int = 10) -> float:
    """t-stat con Newey-West (lag corto: retornos diarios, autocorr. por vol)."""
    x = r.dropna().to_numpy(dtype=float)
    n = len(x)
    if n < 30:
        return float("nan")
    mu = x.mean()
    d = x - mu
    var = (d @ d) / n
    s = 0.0
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        s += 2.0 * w * ((d[k:] @ d[:-k]) / n)
    var_nw = (var + s) / n
    return float(mu / np.sqrt(var_nw)) if var_nw > 0 else float("nan")


def selftest() -> int:
    """Verifica que el vol-targeting NO usa informacion del futuro."""
    print("=" * 74)
    print(" SELFTEST — ¿hay look-ahead en la exposicion?")
    print("=" * 74)
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2020-01-01", periods=600)
    # retornos con clustering de volatilidad (como la realidad)
    vol = np.repeat([0.008, 0.020, 0.012, 0.030], 150)
    r = pd.Series(rng.normal(0, 1, 600) * vol, index=idx)

    r_vt, e = aplicar_vol_target(r, 0.15, 20, 2.0, 5.0)

    # (1) la exposicion en t no puede depender de r_t
    print("\n[1] ¿La exposicion en t depende del retorno de t?")
    # correlacion entre e_t y r_t (si hay fuga, sera fuerte y negativa)
    c = float(pd.concat([e, r], axis=1).dropna().corr().iloc[0, 1])
    print(f"    corr(e_t, r_t) = {c:+.4f}   (debe ser ~0, no negativa fuerte)")
    ok1 = abs(c) < 0.15
    print(f"    {'OK' if ok1 else 'FALLO: la exposicion ve el retorno del mismo dia'}")

    # (2) truncar el futuro no cambia el pasado
    print("\n[2] Truncar el futuro no debe cambiar el pasado")
    corte = 400
    r_a, e_a = aplicar_vol_target(r.iloc[:corte], 0.15, 20, 2.0, 5.0)
    comun = r_vt.index.intersection(r_a.index)
    dif = float((r_vt.loc[comun] - r_a.loc[comun]).abs().max())
    print(f"    fechas comparadas: {len(comun)} | dif max: {dif:.2e}")
    ok2 = dif < 1e-12
    print(f"    {'OK' if ok2 else 'FALLO: HAY LOOK-AHEAD'}")

    # (3) reacciona a la volatilidad: en el tramo de vol alta, e debe bajar
    print("\n[3] ¿Reduce exposicion cuando sube la volatilidad?")
    tramo_bajo = e.iloc[30:150].mean()
    tramo_alto = e.iloc[480:600].mean()
    print(f"    vol 0.8%  -> e media {tramo_bajo:.2f}")
    print(f"    vol 3.0%  -> e media {tramo_alto:.2f}")
    ok3 = tramo_alto < tramo_bajo
    print(f"    {'OK: des-riesga donde toca' if ok3 else 'FALLO'}")

    # (4) el escalado constante NO cambia el Sharpe
    print("\n[4] Escalado constante: el Sharpe debe ser identico")
    from audit_momentum_alpha import metricas
    s0 = metricas(r)["sharpe"]
    for c_ in (0.5, 0.8, 1.2):
        s1 = metricas(r * c_)["sharpe"]
        print(f"    c={c_}: Sharpe {s1:.4f} (base {s0:.4f})")
        if abs(s1 - s0) > 1e-6:
            print("    FALLO: el escalado altera el Sharpe")
            return 1
    print("    OK: invariante al escalado (por eso el control D es valido)")

    todo = ok1 and ok2 and ok3
    print("\n" + "=" * 74)
    print("RESULTADO:", "sin look-ahead, logica correcta" if todo else "REVISAR")
    print("=" * 74)
    return 0 if todo else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    ap.add_argument("--out", default=str(HERE / "audit_vol_target.json"))
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    from audit_momentum_alpha import load_prices, metricas, simulate

    print("=" * 78)
    print(" ¿EL VOL-TARGETING APORTA SOBRE EL EQUAL-WEIGHT?")
    print("=" * 78)
    print(f"  base: equal-weight | costes {COST_BPS:.0f}bps | {args.start} -> {args.end}")

    px = load_prices(args.start, args.end)
    print(f"  cierres: {px.shape[0]} fechas x {px.shape[1]} tickers")

    w_ew = pesos_equal_weight(px)
    r_ew = simulate(px, w_ew, COST_BPS)
    m_ew = metricas(r_ew)
    print(f"  EW puro: CAGR {100*m_ew['cagr']:+.1f}% | vol {100*m_ew['vol']:.1f}% "
          f"| Sharpe {m_ew['sharpe']:.2f} | DD {100*m_ew['maxdd']:.1f}%")

    # --- grid de variantes ---
    print("\n  Barriendo ventanas y targets...")
    filas = []
    for ventana in (20, 60):
        for target in (0.10, 0.12, 0.15):
            for lev in (1.0, 2.0):
                r_vt, e = aplicar_vol_target(r_ew, target, ventana, lev, COST_BPS)
                m = metricas_ext(r_vt, e)
                if not m:
                    continue
                filas.append({
                    "ventana": ventana, "target": target, "max_lev": lev,
                    **m,
                })

    # --- control D: escalado constante con la exposicion media de la mejor B ---
    b = [f for f in filas if f["max_lev"] == 1.0]
    if b:
        mejor_b = max(b, key=lambda f: f["sharpe"])
        em = mejor_b["exposicion_media"]
        r_const = r_ew * em
        m_const = metricas(r_const)
        m_const["exposicion_media"] = em
        m_const["variante"] = "D control (escalado constante)"
    else:
        mejor_b, m_const = None, {}

    print("\n" + "=" * 78)
    print(" RESULTADOS")
    print("=" * 78)
    print(f"  {'variante':<30} {'CAGR':>8} {'vol':>7} {'Sharpe':>8} "
          f"{'maxDD':>8} {'expo':>6}")
    print("  " + "-" * 72)
    print(f"  {'A) EW puro':<30} {100*m_ew['cagr']:>7.1f}% "
          f"{100*m_ew['vol']:>6.1f}% {m_ew['sharpe']:>8.2f} "
          f"{100*m_ew['maxdd']:>7.1f}% {1.0:>6.2f}")
    for f in filas:
        nm = (f"VT win{f['ventana']} tgt{int(f['target']*100)}% "
              f"lev<={f['max_lev']:.1f}")
        print(f"  {nm:<30} {100*f['cagr']:>7.1f}% {100*f['vol']:>6.1f}% "
              f"{f['sharpe']:>8.2f} {100*f['maxdd']:>7.1f}% "
              f"{f['exposicion_media']:>6.2f}")
    if m_const:
        print(f"  {'D) control escalado constante':<30} "
              f"{100*m_const['cagr']:>7.1f}% {100*m_const['vol']:>6.1f}% "
              f"{m_const['sharpe']:>8.2f} {100*m_const['maxdd']:>7.1f}% "
              f"{m_const['exposicion_media']:>6.2f}")

    # --- test central: ¿el VT mejora el Sharpe frente al EW? ---
    print("\n" + "=" * 78)
    print(" TEST CENTRAL — ¿El timing aporta, o solo reduce exposicion?")
    print("=" * 78)
    mejor = max(filas, key=lambda f: f["sharpe"]) if filas else None
    if mejor:
        d_sharpe = mejor["sharpe"] - m_ew["sharpe"]
        nm = (f"win{mejor['ventana']} tgt{int(mejor['target']*100)}% "
              f"lev<={mejor['max_lev']:.1f}")
        print(f"  Mejor VT ({nm}):")
        print(f"    Sharpe {mejor['sharpe']:.3f} vs EW {m_ew['sharpe']:.3f} "
              f"-> delta {d_sharpe:+.3f}")
        print(f"    maxDD  {100*mejor['maxdd']:.1f}% vs EW {100*m_ew['maxdd']:.1f}% "
              f"-> delta {100*(mejor['maxdd']-m_ew['maxdd']):+.1f}pp")
        print(f"    exposicion media {mejor['exposicion_media']:.2f} "
              f"(min {mejor['exposicion_min']:.2f}, max {mejor['exposicion_max']:.2f})")
        print(f"    tiempo des-riesgado: {100*mejor['pct_des_riesgado']:.0f}%")

        # diferencia de retornos VT - EW escalada a la exposicion media
        r_best, _ = aplicar_vol_target(r_ew, mejor["target"], mejor["ventana"],
                                       mejor["max_lev"], COST_BPS)
        dif = (r_best - r_ew * mejor["exposicion_media"]).dropna()
        t = t_stat_serie(dif)
        print(f"\n    Test: VT vs EW escalado a la misma exposicion media")
        print(f"    t-stat (Newey-West lag 10) de la diferencia: {t:+.2f}")

        print()
        if d_sharpe > 0.05 and abs(t) >= 2:
            print("  >> El vol-targeting APORTA: mejora el Sharpe y la diferencia")
            print("     es significativa frente al control de exposicion.")
        elif d_sharpe > 0.05:
            print("  >> Indicio: mejora el Sharpe pero NO es significativo.")
        else:
            print("  >> El vol-targeting NO aporta valor ajustado por riesgo.")
            print("     Reduce el drawdown, pero eso se consigue igual bajando")
            print("     la exposicion de forma constante (control D), sin senal.")
    else:
        print("  Sin resultados validos.")

    # --- veredicto sobre drawdown ---
    if m_const and mejor:
        dd_vt = mejor["maxdd"]
        dd_c = m_const["maxdd"]
        print(f"\n  Drawdown: VT {100*dd_vt:.1f}% vs control constante "
              f"{100*dd_c:.1f}%")
        if dd_vt < dd_c - 0.005:
            print("  -> El VT reduce el drawdown MAS de lo que explica su")
            print("     exposicion media: hay valor en el TIMING.")
        else:
            print("  -> El VT NO reduce el drawdown mas de lo que explica su")
            print("     exposicion media: solo esta invirtiendo menos.")

    out = {
        "fecha": pd.Timestamp.now().isoformat(),
        "periodo": [args.start, args.end], "tickers": int(px.shape[1]),
        "cost_bps": COST_BPS,
        "ew": m_ew, "variantes": filas,
        "control_constante": m_const,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                         default=float), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
