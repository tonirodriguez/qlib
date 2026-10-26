"""jev_formulas_test.py — Prueba VARIAS formulas de sizing sobre las mismas
probabilidades de Jev, SIN volver a llamar a la API.

MOTIVO
    El backtest A/B mostro que Jev (Sharpe 0.970) pierde contra el vol_gate
    (1.128). El diagnostico: Jev NUNCA cierra la posicion (minimo 0.37, cero
    dias a 0), mientras el vol_gate se pone a cero 260 dias. La causa mecanica
    es que `1 - P(crisis) - 0.5*P(risk_off)` no puede llegar a 0 salvo que
    P(crisis) sea exactamente 1.0.

    Este script prueba formulas alternativas que SI pueden llegar a cero,
    reutilizando el vector de probabilidades ya pagado.

REQUIERE
    - La cache con probabilidades: jev_phase0_out/jev_exposure_cache.json
      (si es del formato antiguo, ejecuta antes jev_backtest_ab.py para
       regenerarla con los vectores completos)
    - Precios de qlib para simular los retornos

Uso:
    python3 jev_formulas_test.py
    python3 jev_formulas_test.py --only-gate      # solo comparar, sin Jev
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jev_backtest_ab import (  # noqa: E402
    load_market_data, build_states, run_strategy, metrics,
    load_probabilities,
)
from vol_gate import gate_level_from_pct  # noqa: E402

CACHE = HERE / "jev_phase0_out" / "jev_exposure_cache.json"
TD = 252


# ---------------------------------------------------------------------------
# Formulas candidatas
# ---------------------------------------------------------------------------

def f_original(p: pd.DataFrame) -> pd.Series:
    """Formula acordada: 1 - P(crisis) - 0.5*P(risk_off)."""
    return (1 - p.get("crisis", 0) - 0.5 * p.get("risk_off", 0)).clip(0, 1)


def f_x2(p: pd.DataFrame) -> pd.Series:
    """Castigo doble: 1 - 2*P(crisis) - P(risk_off)."""
    return (1 - 2 * p.get("crisis", 0) - p.get("risk_off", 0)).clip(0, 1)


def f_x2_5(p: pd.DataFrame) -> pd.Series:
    """Castigo 2.5x: 1 - 2.5*P(crisis) - 1.5*P(risk_off)."""
    return (1 - 2.5 * p.get("crisis", 0) - 1.5 * p.get("risk_off", 0)).clip(0, 1)


def f_binary(p: pd.DataFrame, thr: float = 0.5) -> pd.Series:
    """Binaria: fuera si P(crisis) > umbral, si no dentro."""
    return (p.get("crisis", 0) <= thr).astype(float)


def f_binary_soft(p: pd.DataFrame, thr: float = 0.35) -> pd.Series:
    """Binaria con umbral mas bajo, media posicion en risk_off."""
    crisis = p.get("crisis", 0)
    risk_off = p.get("risk_off", 0)
    out = pd.Series(1.0, index=p.index)
    out[crisis > thr] = 0.0
    out[(crisis <= thr) & (risk_off > 0.5)] = 0.5
    return out


def f_expected(p: pd.DataFrame) -> pd.Series:
    """Sizing por utilidad esperada: peso segun probabilidad de cada estado."""
    w = {"risk_on": 1.0, "neutral": 0.8, "risk_off": 0.3, "crisis": 0.0}
    total = sum(p.get(k, 0) * w[k] for k in w)
    return total.clip(0, 1)


def f_percentile(p: pd.DataFrame) -> pd.Series:
    """Escala P(crisis) a [0,1] por su propio percentil CAUSAL.

    Evita el problema de "nunca llega a 1": el peor dia observado HASTA HOY
    se mapea a 0. Usa ventana expansiva -> causal, sin mirar al futuro.
    """
    crisis = p.get("crisis", pd.Series(0.0, index=p.index))
    out = pd.Series(index=crisis.index, dtype=float)
    vals = crisis.to_numpy()
    for i in range(len(vals)):
        hist = vals[: i + 1]
        hist = hist[~np.isnan(hist)]
        if len(hist) < 20:
            out.iloc[i] = 1.0
            continue
        pct = (hist[-1] > hist[:-1]).mean()
        # pct alto -> crisis -> exposicion baja
        out.iloc[i] = float(1.0 - pct)
    return out.clip(0, 1)


FORMULAS = {
    "orig_1-.5": f_original,
    "x2": f_x2,
    "x2.5": f_x2_5,
    "binaria_.5": f_binary,
    "binaria_soft": f_binary_soft,
    "esperada": f_expected,
    "percentil_causal": f_percentile,
}


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-12-31")
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--lookback", type=int, default=120)
    ap.add_argument("--rebalance-days", type=int, default=5)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--max-tickers", type=int, default=120)
    args = ap.parse_args()

    print("=" * 80)
    print(" COMPARACION DE FORMULAS DE SIZING (mismas probabilidades, sin API)")
    print("=" * 80)

    # 1) Probabilidades
    probs = load_probabilities(CACHE)
    if probs.empty:
        print("\n  ERROR: la cache no tiene probabilidades.")
        print("  La cache actual guarda solo escalares. Ejecuta primero:")
        print("      python3 jev_backtest_ab.py")
        print("  Eso la regenera con los vectores completos (usa el cache")
        print("  existente para no repetir llamadas si ya tiene el formato nuevo).")
        return 1
    print(f"\n  probabilidades: {len(probs)} fechas")
    print(f"  rango: {probs.index.min().date()} -> {probs.index.max().date()}")
    print(f"  columnas: {list(probs.columns)}")

    # 2) Datos de mercado
    print("\n  cargando precios...")
    bench, prices = load_market_data(args.start, args.end, args.max_tickers)
    prices = prices.dropna(axis=0, thresh=int(0.5 * prices.shape[1]))

    # 3) Vol_gate (baseline B)
    idx_ret = bench / bench.shift(1) - 1
    vol = idx_ret.rolling(20).std() * np.sqrt(TD)
    pct = vol.rolling(252, min_periods=120).apply(
        lambda x: (x.iloc[-1] > x.iloc[:-1]).mean(), raw=False
    )
    gate = pct.apply(lambda x: gate_level_from_pct(x) if pd.notna(x) else 1.0)

    # 4) Evaluar todo
    results = {}
    expo_stats = {}

    # Baseline A y B
    for name, expo in [("A_FIXED", pd.Series(1.0, index=gate.index)),
                       ("B_VOL_GATE", gate)]:
        net = run_strategy(prices, expo, args.top_n, args.lookback,
                           args.rebalance_days, args.cost_bps)
        m = metrics(net, expo)
        if m and not np.isnan(m["sharpe"]):
            results[name] = m
            expo_stats[name] = expo

    # Formulas Jev
    for fname, fn in FORMULAS.items():
        try:
            expo = fn(probs).reindex(gate.index).ffill().fillna(1.0)
        except Exception as exc:  # noqa: BLE001
            print(f"  {fname}: FALLO ({exc})")
            continue
        net = run_strategy(prices, expo, args.top_n, args.lookback,
                           args.rebalance_days, args.cost_bps)
        m = metrics(net, expo)
        if m and not np.isnan(m["sharpe"]):
            results[f"JEV_{fname}"] = m
            expo_stats[f"JEV_{fname}"] = expo

    # 5) Tabla
    print("\n" + "=" * 80)
    print(" RESULTADOS")
    print("=" * 80)
    df = pd.DataFrame(results).T[["n", "sharpe", "cagr", "max_dd", "vol", "avg_exposure"]]
    df = df.sort_values("sharpe", ascending=False)
    print(df.round(4).to_string())

    # 6) Detalle de exposiciones
    print("\n" + "=" * 80)
    print(" DISTRIBUCION DE EXPOSICIONES (clave del diagnostico)")
    print("=" * 80)
    print(f"  {'formula':<20} {'min':>6} {'max':>6} {'media':>6} "
          f"{'dias=0':>7} {'dias>=.95':>9}")
    for name, expo in expo_stats.items():
        s = expo.dropna()
        print(f"  {name:<20} {s.min():>6.3f} {s.max():>6.3f} {s.mean():>6.3f} "
              f"{(s <= 0.05).sum():>7} {(s >= 0.95).sum():>9}")

    # 7) Veredicto
    print("\n" + "=" * 80)
    print(" VEREDICTO")
    print("=" * 80)
    base = results.get("A_FIXED", {})
    gate_m = results.get("B_VOL_GATE", {})
    jev = {k: v for k, v in results.items() if k.startswith("JEV_")}

    if gate_m:
        print(f"  B_VOL_GATE: Sharpe={gate_m['sharpe']:.4f} "
              f"MaxDD={gate_m['max_dd']:.2%} expo={gate_m['avg_exposure']:.3f}")

    if not jev:
        print("  Ninguna formula Jev produjo resultados.")
        return 0

    best_name, best = max(jev.items(), key=lambda kv: kv[1]["sharpe"])
    print(f"\n  Mejor formula Jev: {best_name}")
    print(f"    Sharpe={best['sharpe']:.4f}  CAGR={best['cagr']:.2%}  "
          f"MaxDD={best['max_dd']:.2%}  expo={best['avg_exposure']:.3f}")

    if gate_m:
        d = best["sharpe"] - gate_m["sharpe"]
        print(f"\n    vs B_VOL_GATE: dSharpe={d:+.4f}  "
              f"dMaxDD={best['max_dd'] - gate_m['max_dd']:+.2%}")
        if d > 0:
            print("\n  >> Alguna formula Jev SUPERA al vol_gate. Merece investigacion.")
        else:
            print("\n  >> Ninguna formula Jev supera al vol_gate.")
            print("     Recomendacion: DESCARTAR la capa Jev y quedarse con vol_gate.")
    else:
        if base:
            d = best["sharpe"] - base["sharpe"]
            print(f"\n    vs A_FIXED: dSharpe={d:+.4f}")
            if d <= 0:
                print("\n  >> Jev no supera ni la exposicion fija. Descartar.")

    print("\n  NOTA: in-sample, una sola muestra. No concluyente sin walk-forward.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
