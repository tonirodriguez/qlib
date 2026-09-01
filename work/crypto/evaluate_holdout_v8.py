"""
evaluate_holdout_v8.py — Evaluacion del holdout final de la estrategia v8.

Usa los umbrales PRE-REGISTRADOS en config/holdout_thresholds_v8.json para
decidir SI la v8 vale para capital real. Disenado para ejecutarse UNA sola vez,
tras re-entrenar el modelo dejando el 15% final sin tocar (Paso 2, GPU).

Politica (inmutable, segun umbrales):
  - open_once: si el resultado ya esta registrado, no se reabre.
  - Se escriben los retornos netos y metricas en un archivo inmutable.

Uso (cuando exista el modelo re-entrenado):
  <python> work/crypto/evaluate_holdout_v8.py --predictions <npy> --returns <npy>

Nota: NO abre el holdout con el modelo actual (que se entreno con todos los
datos). Ese paso es PRE-CONDICION del re-entrenado en genesis (Paso 2).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # work/

from crypto.research_utils import performance_metrics, top1_long_returns  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_FILE = PROJECT_ROOT / "work" / "crypto" / "config" / "holdout_thresholds_v8.json"
RESULT_FILE = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "holdout_result.json"

# Costes reales de Binance aplicados al neto (cuenta base, taker 100%)
BINANCE_BASE_COSTS = {
    "transaction_cost": 0.0010,
    "half_spread": 0.0002,
    "slippage": 0.0003,
    "daily_carry_cost": 0.0,
}


def load_thresholds() -> dict:
    if not THRESHOLDS_FILE.exists():
        raise SystemExit(f"Faltan umbrales pre-registrados: {THRESHOLDS_FILE}")
    return json.loads(THRESHOLDS_FILE.read_text(encoding="utf-8"))


def load_result() -> dict | None:
    if RESULT_FILE.exists():
        try:
            return json.loads(RESULT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def write_immutable_result(result: dict) -> None:
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if RESULT_FILE.exists():
        # Ya hay un resultado (open_once): no sobreescribir
        raise SystemExit(f"Holdout ya evaluado ({RESULT_FILE}). open_once: no se reabre.")
    RESULT_FILE.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"💾 Resultado inmutable guardado: {RESULT_FILE}")


def main() -> None:
    th = load_thresholds()
    if th.get("status") != "PREREGISTERED_NOT_YET_OPEN":
        print(f"⚠️  Status de umbrales: {th.get('status')}")

    existing = load_result()
    if existing is not None:
        print("🔒 Holdout YA evaluado. open_once: no se reabre.")
        print(json.dumps(existing, indent=2))
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, help=".npy con predicciones del modelo en holdout")
    parser.add_argument("--returns", required=True, help=".npy con retornos realizados en holdout")
    parser.add_argument("--costs", default=None, help="JSON con costes o 'binance'")
    args = parser.parse_args()

    preds = np.load(args.predictions)
    rets = np.load(args.returns)

    costs = BINANCE_BASE_COSTS
    if args.costs and args.costs != "binance":
        costs = json.loads(Path(args.costs).read_text(encoding="utf-8"))

    net_returns, _ = top1_long_returns(preds, rets, **costs)
    metrics = performance_metrics(net_returns)
    metrics["turnover"] = float(np.mean(net_returns != 0)) if len(net_returns) else 0.0
    n_pos = int((net_returns > 0).sum())
    win_rate = float(n_pos / len(net_returns)) if len(net_returns) else 0.0
    positive_fraction = win_rate

    # Evaluacion contra umbrales pre-registrados
    gates = th["predeclared_pass_gates"]
    pass_result = all([
        metrics["sharpe"] >= gates["sharpe_annualized_min"],
        metrics["sortino"] >= gates["sortino_annualized_min"],
        abs(metrics["max_drawdown"]) <= gates["max_drawdown_max_abs"],
        metrics["calmar"] >= gates["calmar_min"],
        win_rate >= gates["win_rate_min"],
        positive_fraction >= gates["positive_returns_fraction_min"],
    ])

    result = {
        "date_evaluated": date.today().isoformat(),
        "model": th["model"],
        "holdout_fraction": th["holdout"]["fraction"],
        "costs_used": costs,
        "metrics": {
            "sharpe": metrics["sharpe"],
            "sortino": metrics["sortino"],
            "max_drawdown": metrics["max_drawdown"],
            "calmar": metrics["calmar"],
            "var_95": metrics["var_95"],
            "cvar_95": metrics["cvar_95"],
            "annualized_return": metrics["annualized_return"],
            "turnover": metrics["turnover"],
        },
        "win_rate": win_rate,
        "positive_return_fraction": positive_fraction,
        "passes_predeclared_gates": pass_result,
        "decision": "APROBADA" if pass_result else "DESARTADA",
        "thresholds_used": gates,
    }
    write_immutable_result(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\n{'✅ APROBADA para capital real' if pass_result else '❌ DESARTADA'}")


if __name__ == "__main__":
    main()