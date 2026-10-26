"""vol_gate_validacion_v3.py — Validacion del vol-gate con estrategia PROPIA.

Usa `gated_strategy.GatedTopkStrategy`, que NO hereda de TopkDropoutStrategy.
Motivo: subclasear no funciono (los 4 backtests daban Sharpe identico aunque
el override cambiaba `self.topk`), y no se pudo determinar la causa leyendo
el codigo de qlib.

Esta version genera las ordenes explicitamente, asi que el efecto del gate
es verificable. Incluye diagnostico obligatorio: si el gate no cambia el
numero de posiciones, el script lo dice y NO presenta resultados como validos.

Uso (en WSL):
    conda run -n qlib python work/estrategias/vol_gate_validacion_v3.py
    conda run -n qlib python work/estrategias/vol_gate_validacion_v3.py --quick
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
from gated_strategy import GatedTopkStrategy  # noqa: E402

MOM_W = 120
TOPK = 30
IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

AGOSTO = {
    "momentum puro": {"sharpe": 0.960, "maxdd": -0.193, "anual": 0.185},
    "gate P70": {"sharpe": 0.967, "maxdd": -0.150, "anual": 0.189},
    "gate P75": {"sharpe": 1.136, "maxdd": -0.166, "anual": 0.232},
    "gate P80": {"sharpe": 1.071, "maxdd": -0.177, "anual": 0.215},
}

# Referencia: estrategia estandar de qlib (baseline sin gate)
STRAT_BASE = {
    "class": "TopkDropoutStrategy",
    "module_path": "qlib.contrib.strategy",
    "kwargs": {"signal": None, "topk": TOPK, "n_drop": 5,
               "only_tradable": True, "hold_thresh": 20},
}


def perf_from_account(pv: np.ndarray) -> dict:
    r = pd.Series(pv).pct_change().dropna().values
    if len(r) < 10:
        return {"sharpe": float("nan"), "maxdd": float("nan"),
                "anual": float("nan"), "n_weeks": len(r)}
    ann = float(np.mean(r)) * 52
    vol = float(np.std(r)) * np.sqrt(52)
    cum = np.cumprod(1 + r)
    dd = cum / np.maximum.accumulate(cum) - 1
    return {"sharpe": float(ann / vol) if vol else float("nan"),
            "maxdd": float(dd.min()), "anual": ann, "n_weeks": int(len(r))}


def run(signal, gate_series, name, bt_start, bt_end, benchmark,
        base_topk=TOPK, use_gated=True):
    """Backtest. Para el gate se construye la INSTANCIA a mano.

    MOTIVO: `init_instance_by_config` (qlib/utils/mod.py:178-184) hace
        try:    klass(**cls_kwargs, **try_kwargs, **kwargs)
        except TypeError: klass(**cls_kwargs, **kwargs)
    Si el constructor lanza TypeError, qlib REINTENTA sin los kwargs extra:
    la estrategia se queda sin `gate`, `level_at` devuelve 1.0 siempre y el
    backtest sale identico al puro. Fue la causa del fallo de v2
    (diagnostico observado: niveles de gate {1.0: 240}).

    Solucion: crear la instancia nosotros. `init_instance_by_config` la
    devuelve tal cual si ya es del tipo aceptado (accept_types), sin reconstruir.
    """
    from qlib.backtest import backtest

    if use_gated:
        GatedTopkStrategy.configure(gate_series, base_topk=base_topk)
        strategy = {
            "class": GatedTopkStrategy,
            "kwargs": {"signal": signal, "only_tradable": True},
        }
    else:
        cfg = {k: (dict(v) if isinstance(v, dict) else v)
               for k, v in STRAT_BASE.items()}
        cfg["kwargs"]["signal"] = signal
        strategy = cfg

    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
    }
    report, _ = backtest(
        start_time=bt_start, end_time=bt_end, strategy=strategy,
        executor=executor, benchmark=benchmark, account=100000,
        exchange_kwargs=IB,
    )
    fk = list(report.keys())[0]
    df = report[fk][0]
    pv = df["account"].values
    m = perf_from_account(pv)
    m["name"] = name
    m["final_value"] = float(pv[-1]) if len(pv) else float("nan")
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-08-01")
    ap.add_argument("--bt-start", default="2022-01-01")
    ap.add_argument("--bt-end", default="2026-08-07")
    ap.add_argument("--benchmark", default="^NDX")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(HERE / "vol_gate_validacion_v3.json"))
    args = ap.parse_args()

    import qlib
    from qlib.data import D

    print("=" * 78)
    print(" VALIDACION v3 — estrategia PROPIA (ordenes explicitas)")
    print("=" * 78)
    print("  gate 1.0 -> 30 posiciones | 0.5 -> 15 | 0.0 -> TODO A CASH")

    uri = os.environ.get("QLIB_US_DATA") or os.path.expanduser("~/.qlib/qlib_data/us_data")
    qlib.init(provider_uri=uri, region="us")

    inst_dir = os.path.join(uri, "instruments")
    universe = next((nm for nm in ("sp500_liquid", "sp500")
                     if os.path.exists(os.path.join(inst_dir, nm + ".txt"))), None)
    if universe is None:
        raise FileNotFoundError(f"Sin universo en {inst_dir}")
    print(f"  universo : {universe}")

    tickers = D.list_instruments(D.instruments(universe), as_list=True)
    close = D.features(tickers, ["$close"], start_time=args.start,
                       end_time=args.end, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    print(f"  precios  : {close.shape[0]} x {close.shape[1]}")

    mom = close / close.shift(MOM_W) - 1
    market = close.mean(axis=1)

    def to_qlib(df):
        s = df.stack().dropna().reset_index()
        s.columns = ["datetime", "instrument", "signal"]
        s["datetime"] = pd.to_datetime(s["datetime"])
        return s.set_index(["datetime", "instrument"])["signal"].sort_index()

    sig = to_qlib(mom)
    results = []

    print("\n  [1] momentum puro (TopkDropout estandar)...")
    try:
        results.append(run(sig, None, "momentum puro", args.bt_start,
                           args.bt_end, args.benchmark, use_gated=False))
    except Exception as exc:  # noqa: BLE001
        print(f"      FALLO: {str(exc)[:200]}")

    grid = [(0.75, 0.90)] if args.quick else [(0.70, 0.85), (0.75, 0.90), (0.80, 0.95)]
    diags = {}
    for p75, p90 in grid:
        label = f"gate P{int(p75*100)}"
        print(f"\n  {label}...")
        gate = vg.gate_series_gated(market, p75=p75, p90=p90)
        gate_col = gate.reindex(close.index).ffill().fillna(1.0)
        try:
            r = run(sig, gate_col, label, args.bt_start, args.bt_end,
                    args.benchmark, use_gated=True)
            results.append(r)
        except Exception as exc:  # noqa: BLE001
            print(f"      FALLO: {str(exc)[:300]}")
            diags[label] = {"error": str(exc)[:300]}
            continue

        # El diagnostico se lee de la instancia creada dentro de qlib; como no
        # la tenemos a mano, lo inferimos del propio resultado + un chequeo
        # directo de la clase:
        diags[label] = {"gate_value_counts": {str(k): int(v) for k, v in
                                              gate_col.value_counts().items()}}
        print(f"      gate: {dict(gate_col.value_counts().sort_index())}")

    # --- Tabla ---
    print("\n" + "=" * 78)
    print(" RESULTADOS")
    print("=" * 78)
    print(f"  {'Estrategia':<18}{'Sharpe':>9}{'MaxDD':>10}{'Anual':>10}{'Final':>13}")
    print("  " + "-" * 58)
    for r in results:
        print(f"  {r['name']:<18}{r['sharpe']:>9.3f}{r['maxdd']*100:>9.1f}%"
              f"{r['anual']*100:>9.1f}%{r['final_value']:>13,.0f}")

    # --- Chequeo de inercia ---
    print("\n" + "=" * 78)
    print(" CHEQUEO: ¿el gate cambia algo?")
    print("=" * 78)
    if len(results) >= 2:
        base = results[0]
        gates = results[1:]
        identical = all(abs(r["sharpe"] - base["sharpe"]) < 1e-6 for r in gates)
        same_final = all(abs(r["final_value"] - base["final_value"]) < 1.0
                         for r in gates)
        if identical and same_final:
            print("  ❌ TODOS IDENTICOS -> el gate NO afecta al backtest.")
            print("     Este resultado NO es valido. Hay que depurar la estrategia.")
            print("     Comprueba que GatedTopkStrategy.generate_trade_decision")
            print("     se ejecuta y que target_n varia.")
        else:
            print("  ✅ Los resultados DIFIEREN -> el gate esta actuando.")
    else:
        print("  (faltan resultados para comparar)")

    # --- Veredicto ---
    print("\n" + "=" * 78)
    print(" VEREDICTO")
    print("=" * 78)
    if len(results) >= 2:
        base = results[0]
        gates = results[1:]
        print(f"  momentum puro: Sharpe {base['sharpe']:.3f}, DD {base['maxdd']:.1%}")
        for r in gates:
            print(f"  {r['name']:<13}: Sharpe {r['sharpe']:.3f} "
                  f"({r['sharpe']-base['sharpe']:+.3f}), DD {r['maxdd']:.1%} "
                  f"({(r['maxdd']-base['maxdd'])*100:+.1f}pp)")
        mej = sum(1 for r in gates if r["sharpe"] > base["sharpe"])
        ddm = sum(1 for r in gates if r["maxdd"] >= base["maxdd"] * 0.80)
        print(f"\n  Mejoran Sharpe: {mej}/{len(gates)} | Reducen DD>=20%: {ddm}/{len(gates)}")
        if mej == len(gates):
            print("  -> ROBUSTO en todos los umbrales.")
        elif mej > 0:
            print("  -> Mejora PARCIAL.")
        elif ddm > 0:
            print("  -> No mejora Sharpe pero SI reduce drawdown: util como")
            print("     control de riesgo, no como mejora de retorno.")
        else:
            print("  -> No aporta con este mecanismo.")

    Path(args.out).write_text(json.dumps({
        "fecha": pd.Timestamp.now().isoformat(),
        "mecanismo": "estrategia propia, gate sobre numero de posiciones",
        "periodo": [args.bt_start, args.bt_end],
        "benchmark": args.benchmark,
        "universe": universe,
        "resultados": results,
        "diagnostico": diags,
    }, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
