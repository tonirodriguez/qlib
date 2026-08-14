"""Leakage-safe preprocessing and evaluation helpers for crypto research."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClipBounds:
    lower: np.ndarray
    upper: np.ndarray


def fit_clip_bounds(train: np.ndarray, quantile: float = 0.999) -> ClipBounds:
    """Fit per-feature bounds using training observations only."""
    values = np.asarray(train, dtype=float)
    if values.ndim != 2 or not len(values):
        raise ValueError("train must be a non-empty 2D array")
    if not 0.5 < quantile <= 1.0:
        raise ValueError("quantile must be in (0.5, 1.0]")
    tail = (1.0 - quantile) / 2.0
    return ClipBounds(
        lower=np.quantile(values, tail, axis=0),
        upper=np.quantile(values, 1.0 - tail, axis=0),
    )


def apply_clip_bounds(values: np.ndarray, bounds: ClipBounds) -> np.ndarray:
    """Apply already-fitted bounds without learning from these observations."""
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("values must be a 2D array")
    if matrix.shape[1] != len(bounds.lower):
        raise ValueError("feature count does not match fitted clip bounds")
    return np.clip(matrix, bounds.lower, bounds.upper)


def top1_long_returns(
    predictions: np.ndarray,
    realized_returns: np.ndarray,
    transaction_cost: float = 0.001,
    half_spread: float = 0.0,
    slippage: float = 0.0,
    daily_carry_cost: float = 0.0,
    one_way_costs: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return net t+1 P&L and positions for a top-1 long/cash strategy.

    A cost is charged only when the selected position changes. Entering and
    leaving the market each cost one transaction; switching assets costs two.
    """
    predictions = np.asarray(predictions, dtype=float)
    realized_returns = np.asarray(realized_returns, dtype=float)
    if predictions.shape != realized_returns.shape or predictions.ndim != 2:
        raise ValueError("predictions and realized_returns must be equal 2D arrays")
    if min(transaction_cost, half_spread, slippage, daily_carry_cost) < 0:
        raise ValueError("execution costs cannot be negative")

    best_assets = np.argmax(predictions, axis=1)
    positions = np.where(np.max(predictions, axis=1) > 0, best_assets, -1)
    gross = np.zeros(len(positions), dtype=float)
    active = positions >= 0
    rows = np.arange(len(positions))[active]
    gross[active] = realized_returns[rows, positions[active]]

    previous = np.concatenate((np.array([-1]), positions[:-1]))
    trades = (positions != previous).astype(float)
    switches = ((positions >= 0) & (previous >= 0) & (positions != previous)).astype(float)
    if one_way_costs is None:
        execution_cost = transaction_cost + half_spread + slippage
        costs = execution_cost * (trades + switches)
    else:
        asset_costs = np.asarray(one_way_costs, dtype=float)
        if asset_costs.shape != (predictions.shape[1],) or (asset_costs < 0).any():
            raise ValueError("one_way_costs must be a non-negative vector matching assets")
        costs = np.zeros(len(positions), dtype=float)
        changed = positions != previous
        exits = changed & (previous >= 0)
        entries = changed & (positions >= 0)
        costs[exits] += asset_costs[previous[exits]]
        costs[entries] += asset_costs[positions[entries]]
    costs += daily_carry_cost * active.astype(float)
    return gross - costs, positions


def performance_metrics(returns: np.ndarray, periods_per_year: int = 365) -> dict[str, float]:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or not len(values):
        raise ValueError("returns must be a non-empty 1D array")
    equity_curve = np.cumprod(1.0 + values)
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = equity_curve / peaks - 1.0
    downside = values[values < 0]
    downside_deviation = np.std(downside) if len(downside) else 0.0
    annualized_return = (
        float(equity_curve[-1] ** (periods_per_year / len(values)) - 1.0)
        if equity_curve[-1] > 0
        else -1.0
    )
    value_at_risk = float(np.quantile(values, 0.05))
    tail = values[values <= value_at_risk]
    return {
        "equity_final": float(equity_curve[-1]),
        "sharpe": float(np.mean(values) / (np.std(values) + 1e-10) * np.sqrt(periods_per_year)),
        "sortino": float(
            np.mean(values) / (downside_deviation + 1e-10) * np.sqrt(periods_per_year)
        ),
        "max_drawdown": float(np.min(drawdowns)),
        "annualized_return": annualized_return,
        "calmar": float(annualized_return / (abs(np.min(drawdowns)) + 1e-10)),
        "var_95": value_at_risk,
        "cvar_95": float(np.mean(tail)),
    }


DEFAULT_COST_SCENARIOS = {
    "optimistic": {
        "transaction_cost": 0.0005,
        "half_spread": 0.0001,
        "slippage": 0.0001,
        "daily_carry_cost": 0.0,
    },
    "base": {
        "transaction_cost": 0.0010,
        "half_spread": 0.0002,
        "slippage": 0.0003,
        "daily_carry_cost": 0.0,
    },
    "adverse": {
        "transaction_cost": 0.0015,
        "half_spread": 0.0005,
        "slippage": 0.0010,
        "daily_carry_cost": 0.0,
    },
}


def evaluate_cost_scenarios(
    predictions: np.ndarray,
    realized_returns: np.ndarray,
    scenarios: dict[str, dict[str, float]] | None = None,
    periods_per_year: int = 365,
) -> dict[str, dict[str, float]]:
    scenario_definitions = scenarios or DEFAULT_COST_SCENARIOS
    results: dict[str, dict[str, float]] = {}
    for name, costs in scenario_definitions.items():
        returns, positions = top1_long_returns(predictions, realized_returns, **costs)
        metrics = performance_metrics(returns, periods_per_year=periods_per_year)
        metrics["turnover"] = (
            float(np.mean(positions[1:] != positions[:-1])) if len(positions) > 1 else 0.0
        )
        results[name] = metrics
    return results
