"""
paper_metrics.py — Metricas y monitor del paper trading SFM v8 (Paso 6).

Calcula las metricas de rendimiento desde el historial del paper
(history_paper_trading.csv) y las integra en el reporte/CI diario:
Sharpe, Sortino, Calmar, VaR, CVaR, max_drawdown, win rate y P&L curve.

Usa research_utils.performance_metrics (misma base que el backtest).

Uso:
    python work/crypto/paper_metrics.py --csv <path>          # reporte desde historial
    python work/crypto/paper_metrics.py --state <path>        # snapshot desde estado+prices
    python work/crypto/paper_metrics.py --current 10450 10000 # P&L snapshot (valor, capital inicial)

Los tres escriben un JSON resumen en output/sfm_v8/metrics_paper_latest.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # work/

from crypto.research_utils import performance_metrics  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8"
DEFAULT_CSV = OUTPUT_DIR / "history_paper_trading.csv"
METRICS_OUT = OUTPUT_DIR / "metrics_paper_latest.json"
PERIODS_PER_YEAR = 365


def returns_from_history(csv_path: Path, capital: float) -> np.ndarray:
    """Deriva los retornos diarios de la curva de capital del historial.

    Si el CSV tiene una columna 'total_value', usa su pct_change.
    Si no, la deriva de 'total_gain_pct' o del "cash + positions_value".
    """
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").drop_duplicates("date", keep="last")

    if "total_value" in df.columns:
        curve = df["total_value"].astype(float).values
    elif "total_gain_pct" in df.columns:
        curve = capital * (1.0 + df["total_gain_pct"].astype(float) / 100.0).values
    else:
        cash = df["cash"].astype(float).values if "cash" in df.columns else df["total_value"].values
        pos = df["positions_value"].astype(float).values if "positions_value" in df.columns else 0.0
        curve = cash + pos

    returns = np.diff(curve) / curve[:-1]
    returns = returns[~np.isnan(returns)]
    return returns


def compute_metrics(returns: np.ndarray, capital: float) -> dict:
    """Metricas completas desde un array de retornos diarios."""
    if returns is None or len(returns) == 0:
        return {
            "n_days": 0,
            "note": "No hay suficiente historial (paper recien iniciado). Poblar diariamente.",
        }
    m = performance_metrics(returns, periods_per_year=PERIODS_PER_YEAR)
    wins = int((returns > 0).sum())
    losses = int((returns < 0).sum())
    equity = float(np.prod(1.0 + returns))
    return {
        "n_days": int(len(returns)),
        "equity_curve_final": round(equity, 4),
        "total_return_pct": round((equity - 1.0) * 100, 3),
        "sharpe": round(m["sharpe"], 3),
        "sortino": round(m["sortino"], 3),
        "calmar": round(m["calmar"], 3),
        "max_drawdown_pct": round(m["max_drawdown"] * 100, 3),
        "annualized_return_pct": round(m["annualized_return"] * 100, 3),
        "var_95_daily_pct": round(m["var_95"] * 100, 3),
        "cvar_95_daily_pct": round(m["cvar_95"] * 100, 3),
        "win_rate_pct": round(wins / max(len(returns), 1) * 100, 2),
        "loss_rate_pct": round(losses / max(len(returns), 1) * 100, 2),
    }


def snapshot_metrics(current_value: float, start_capital: float) -> dict:
    """P&L snapshot (usado cuando el historial aun no tiene series)."""
    pnl_pct = (current_value - start_capital) / start_capital * 100
    return {
        "n_days": 0,
        "total_return_pct": round(pnl_pct, 3),
        "sharpe": None,
        "sortino": None,
        "calmar": None,
        "max_drawdown_pct": 0.0,
        "note": "snapshot (no hay serie historica aun)",
    }


def save_metrics(metrics: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"💾 Metricas guardadas: {METRICS_OUT}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", nargs="?", default=str(DEFAULT_CSV))
    ap.add_argument("--state", nargs="?")
    ap.add_argument("--capital", type=float, default=10000.0)
    ap.add_argument("--snapshot", nargs="?")
    args = ap.parse_args()

    if args.snapshot:
        metrics = snapshot_metrics(float(args.snapshot), args.capital)
    elif args.state:
        # state json + precios: usar total del estado
        with open(args.state) as f:
            st = json.load(f)
        metrics = snapshot_metrics(st.get("total_value", st.get("capital_usd", args.capital)), args.capital)
    else:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"⚠️  No hay historial en {csv_path}. Usando snapshot del estado.")
            metrics = snapshot_metrics(float(args.capital), args.capital)
        else:
            returns = returns_from_history(csv_path, args.capital)
            metrics = compute_metrics(returns, args.capital)

    print(json.dumps(metrics, indent=2, sort_keys=True))
    save_metrics(metrics)


if __name__ == "__main__":
    main()