"""vol_gate_reverificacion.py — RE-VERIFICAR el vol_gate TRAS el fix del look-ahead.

CONTEXTO
    El 2026-08-22 se valido el vol-gate y se documento:
        mom + gate P75 -> Sharpe 1.136, anual 23.2%, DD -16.6%
        (vs momentum puro: Sharpe 0.960, anual 18.5%, DD -19.3%)

    El 2026-10-17/18 se corrigio un BUG REAL en `vol_percentile()`:
      - El fallback `vol / vol.max()` NO era un percentil y ademas tenia
        look-ahead (`max()` sobre toda la muestra, incluido el futuro).
      - La validacion corria con historia larga (percentil) y la produccion
        con historia corta (fallback) -> "validado != desplegado".

    `vol_gate_correccion.md` dejo pendiente (paso 2 de "Proximos pasos"):
        "Re-correr vol_gate_test.py sobre historia larga Qlib para confirmar
         que los numeros de validacion (Sharpe 1.136 en P75) se mantienen."

    ESTE SCRIPT HACE ESO.

DIFERENCIAS con vol_gate_test.py (del 27-ago, pre-fix)
    1. UNIVERSE: "sp500_liquid" NO EXISTE en la instalacion actual.
       Se usa "sp500" (1.180 tickers, con composicion historica).
    2. END: se deja margen sobre el fin del calendario (el IndexError de qlib
       al pedir _calendar[index+1] si end_time es la ultima fecha).
    3. Se AÑADE un diagnostico explicito del percentil: distribucion de
       vol_pct y cuantos dias caen en cada nivel de gate. Si el gate no
       dispara, el backtest no puede mejorar nada.
    4. Se guardan los resultados en JSON para comparar con los de agosto.

Uso (en WSL):
    conda run -n qlib python work/estrategias/vol_gate_reverificacion.py
    conda run -n qlib python work/estrategias/vol_gate_reverificacion.py --quick
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
sys.path.insert(0, str(HERE))

import vol_gate as vg  # noqa: E402

# --- Valores documentados en agosto (a re-verificar) ---
AGOSTO = {
    "momentum puro":      {"sharpe": 0.960, "maxdd": -0.193, "anual": 0.185},
    "mom+gate P70":       {"sharpe": 0.967, "maxdd": -0.150, "anual": 0.189},
    "mom+gate P75":       {"sharpe": 1.136, "maxdd": -0.166, "anual": 0.232},
    "mom+gate P80":       {"sharpe": 1.071, "maxdd": -0.177, "anual": 0.215},
}

MOM_W = 120
TOPK = 30

# Costes IB (los mismos del test original, para ser comparable)
IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")


def find_universe_file() -> str:
    """Devuelve el universo disponible (sp500_liquid no existe en esta maquina)."""
    uri = os.environ.get("QLIB_US_DATA") or os.path.expanduser("~/.qlib/qlib_data/us_data")
    for name in ("sp500_liquid.txt", "sp500.txt"):
        p = os.path.join(uri, "instruments", name)
        if os.path.exists(p):
            print(f"  universo: {name}")
            return name.replace(".txt", "")
    raise FileNotFoundError(f"No encuentro universo en {uri}/instruments/")


def run_backtest(sig_series, name, bt_start, bt_end, benchmark):
    """Backtest con el motor de Qlib. Devuelve metricas comparables."""
    from qlib.backtest import backtest

    strategy = {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {"signal": sig_series, "topk": TOPK, "n_drop": 5,
                   "only_tradable": True, "hold_thresh": 20},
    }
    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
    }
    report, _ = backtest(
        start_time=bt_start, end_time=bt_end,
        strategy=strategy, executor=executor,
        benchmark=benchmark, account=100000, exchange_kwargs=IB,
    )
    freq_key = list(report.keys())[0]
    df = report[freq_key][0]
    pv = df["account"].values
    port_ret = pd.Series(pv).pct_change().dropna().values
    mean_ann = float(np.mean(port_ret)) * 52
    vol = float(np.std(port_ret)) * np.sqrt(52)
    sharpe = mean_ann / vol if vol else np.nan
    cum = np.cumprod(1 + port_ret)
    dd = cum / np.maximum.accumulate(cum) - 1
    return {
        "name": name,
        "sharpe": float(sharpe),
        "maxdd": float(dd.min()),
        "anual": float(mean_ann),
        "n_weeks": int(len(port_ret)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-08-01", help="fin del calculo de momentum")
    ap.add_argument("--bt-start", default="2022-01-01")
    ap.add_argument("--bt-end", default="2026-08-07")
    ap.add_argument("--benchmark", default="^NDX", help="el original usaba ^NDX")
    ap.add_argument("--quick", action="store_true", help="solo P75 (el documentado)")
    ap.add_argument("--out", default=str(HERE / "vol_gate_reverificacion.json"))
    args = ap.parse_args()

    import qlib
    from qlib.data import D

    print("=" * 78)
    print(" RE-VERIFICACION DEL VOL-GATE TRAS EL FIX DEL LOOK-AHEAD")
    print("=" * 78)
    print(f"  vol_gate.py     : corregido 2026-10-17 (percentil causal)")
    print(f"  validacion orig.: 2026-08-22 (Sharpe 1.136 en P75)")
    print(f"  periodo backtest: {args.bt_start} -> {args.bt_end}")
    print(f"  benchmark       : {args.benchmark}")

    uri = os.environ.get("QLIB_US_DATA") or os.path.expanduser("~/.qlib/qlib_data/us_data")
    qlib.init(provider_uri=uri, region="us")
    print(f"  qlib_data       : {uri}")

    universe = find_universe_file()
    tickers = D.list_instruments(D.instruments(universe), as_list=True)
    print(f"  tickers         : {len(tickers)}")

    close = D.features(tickers, ["$close"], start_time=args.start,
                       end_time=args.end, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    print(f"  precios         : {close.shape[0]} fechas x {close.shape[1]} tickers")

    mom = close / close.shift(MOM_W) - 1
    market = close.mean(axis=1)

    # ------------------------------------------------------------------
    # DIAGNOSTICO DEL PERCENTIL (lo que faltaba en el test original)
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(" DIAGNOSTICO DEL PERCENTIL DE VOLATILIDAD (post-fix)")
    print("=" * 78)
    vol, pct = vg.vol_percentile(market, vol_win=20, hist_win=252)
    pct_valid = pct.dropna()
    print(f"  fechas con percentil valido : {len(pct_valid)} de {len(pct)}")
    if len(pct_valid):
        print(f"  rango de vol_pct            : {pct_valid.min():.3f} .. {pct_valid.max():.3f}")
        print(f"  media / mediana             : {pct_valid.mean():.3f} / {pct_valid.median():.3f}")
        print(f"  dias con pct >= 0.75        : {(pct_valid >= 0.75).sum()} "
              f"({100*(pct_valid >= 0.75).mean():.1f}%)")
        print(f"  dias con pct >= 0.90        : {(pct_valid >= 0.90).sum()} "
              f"({100*(pct_valid >= 0.90).mean():.1f}%)")
        print("\n  (esperado por construccion: ~25% y ~10%)")

    # Verificacion de causalidad: re-calcular con una implementacion
    # independiente que solo mira al pasado y comparar.
    def pct_causal_manual(s, win=252, minp=120):
        v = s.to_numpy()
        out = np.full(len(v), np.nan)
        for i in range(len(v)):
            w = v[max(0, i - win + 1): i + 1]
            w = w[~np.isnan(w)]
            if len(w) >= minp:
                out[i] = (w[-1] > w[:-1]).mean()
        return pd.Series(out, index=s.index)

    causal = pct_causal_manual(vol)
    both = pd.concat([pct.rename("gate"), causal.rename("causal")], axis=1).dropna()
    maxdiff = (both["gate"] - both["causal"]).abs().max() if len(both) else float("nan")
    print(f"\n  CAUSALIDAD: max |percentil_gate - percentil_causal| = {maxdiff:.2e}")
    if maxdiff < 1e-9:
        print("  OK: el percentil es estrictamente causal (solo mira al pasado)")
    else:
        print("  AVISO: hay discrepancia; revisar la implementacion")

    # ------------------------------------------------------------------
    # BACKTESTS
    # ------------------------------------------------------------------
    def to_qlib(sig_df):
        s = sig_df.stack().dropna()
        s = s.reset_index()
        s.columns = ["datetime", "instrument", "signal"]
        s["datetime"] = pd.to_datetime(s["datetime"])
        return s.set_index(["datetime", "instrument"])["signal"].sort_index()

    results = []
    print("\n" + "=" * 78)
    print(" EJECUTANDO BACKTESTS")
    print("=" * 78)

    print("  momentum puro...")
    results.append(run_backtest(to_qlib(mom), "momentum puro",
                                args.bt_start, args.bt_end, args.benchmark))

    grid = [(0.75, 0.90)] if args.quick else [(0.70, 0.85), (0.75, 0.90), (0.80, 0.95)]
    for p75, p90 in grid:
        print(f"  mom+gate P{int(p75*100)}...")
        gate = vg.gate_series_gated(market, p75=p75, p90=p90)
        gate_col = gate.reindex(close.index).ffill().fillna(1.0)
        sig_gated = mom.multiply(gate_col, axis=0)
        results.append(run_backtest(to_qlib(sig_gated), f"mom+gate P{int(p75*100)}",
                                    args.bt_start, args.bt_end, args.benchmark))

    # ------------------------------------------------------------------
    # COMPARACION
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(" RESULTADO: HOY vs AGOSTO (pre-fix)")
    print("=" * 78)
    print(f"  {'Estrategia':<18}{'Sharpe ago':>11}{'Sharpe hoy':>11}{'delta':>9} "
          f"{'DD ago':>9}{'DD hoy':>9}")
    print("  " + "-" * 70)
    for r in results:
        old = AGOSTO.get(r["name"], {})
        so = old.get("sharpe")
        do = old.get("maxdd")
        delta = (r["sharpe"] - so) if so is not None else None
        print(f"  {r['name']:<18}"
              f"{so if so is not None else float('nan'):>11.3f}"
              f"{r['sharpe']:>11.3f}"
              f"{delta if delta is not None else float('nan'):>+9.3f} "
              f"{do*100 if do is not None else float('nan'):>8.1f}%"
              f"{r['maxdd']*100:>8.1f}%")

    # ------------------------------------------------------------------
    # VEREDICTO
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(" VEREDICTO")
    print("=" * 78)
    base = results[0]
    gates = results[1:]
    doc_p75 = next((r for r in results if r["name"] == "mom+gate P75"), None)

    if doc_p75:
        delta = doc_p75["sharpe"] - AGOSTO["mom+gate P75"]["sharpe"]
        print(f"  P75 documentado : Sharpe {AGOSTO['mom+gate P75']['sharpe']:.3f}")
        print(f"  P75 re-verificado: Sharpe {doc_p75['sharpe']:.3f}")
        print(f"  diferencia      : {delta:+.3f}")
        print()
        if abs(delta) < 0.10:
            print("  >> SE MANTIENE. El fix no altero la validacion.")
            print("     Los numeros de agosto siguen siendo validos.")
        elif delta < 0:
            print(f"  >> BAJA ({delta:+.3f}). El Sharpe de agosto estaba INFLADO")
            print("     (total o parcialmente) por el look-ahead del fallback.")
            print("     >>> NO usar 1.136 como referencia. Usar el valor de hoy.")
        else:
            print(f"  >> SUBE ({delta:+.3f}). El fix mejoro el gate.")

    mej = sum(1 for r in gates if r["sharpe"] > base["sharpe"])
    dd_mej = sum(1 for r in gates if r["maxdd"] <= base["maxdd"] * 0.80)
    print(f"\n  Gates que mejoran Sharpe del puro : {mej}/{len(gates)}")
    print(f"  Gates que reducen >=20% el DD      : {dd_mej}/{len(gates)}")
    if mej == len(gates):
        print("  -> El gate sigue siendo ROBUSTO en todos los umbrales.")
    elif mej > len(gates) / 2:
        print("  -> Mejora PARCIAL: robusto solo en algunos umbrales.")
    else:
        print("  -> NO robusto tras el fix. Revisar antes de usar en produccion.")

    # Guardar
    out = {
        "fecha": pd.Timestamp.now().isoformat(),
        "periodo": [args.bt_start, args.bt_end],
        "benchmark": args.benchmark,
        "universe": universe,
        "pct_causal_maxdiff": float(maxdiff) if maxdiff == maxdiff else None,
        "resultados": results,
        "agosto": AGOSTO,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
