"""Baselines and statistical robustness for crypto research.

Two pieces the formal experiment needs before any result can be trusted:

1. Baselines to compare the model against, all evaluated t+1 on the same
   realized-return matrix and the same cost model:
   * cash              — flat, zero return (the true "do nothing").
   * equal_weight      — daily-rebalanced equal weight (the existing benchmark).
   * buy_and_hold      — equal weight at t0, no rebalancing (weights drift).
   * momentum          — top-1 long by trailing cumulative return, t+1.

2. Statistical robustness so point estimates are not read as truth:
   * block_bootstrap_sharpe — CI and p(Sharpe>0) preserving autocorrelation.
   * probabilistic_sharpe_ratio (PSR) — confidence that SR exceeds a benchmark,
     correcting for sample length, skew and kurtosis.
   * deflated_sharpe_ratio (DSR) — PSR against the expected maximum Sharpe from
     N trials, i.e. correcting for multiple testing across universes/seeds.

Only numpy is required (normal CDF/inverse implemented locally). Sharpe here
reuses the project's 365-day annualization via ``research_utils``.
"""

from __future__ import annotations

import math

import numpy as np

try:  # allow both "python -m" and direct execution
    from work.crypto.research_utils import performance_metrics, top1_long_returns
except ImportError:  # pragma: no cover - fallback for direct script runs
    from research_utils import performance_metrics, top1_long_returns


# --------------------------------------------------------------------------- #
# Baseline return series (all shaped (T,) net of nothing unless costs passed)
# --------------------------------------------------------------------------- #
def cash_returns(n_periods: int) -> np.ndarray:
    if n_periods <= 0:
        raise ValueError("n_periods must be positive")
    return np.zeros(n_periods, dtype=float)


def equal_weight_returns(realized_returns: np.ndarray) -> np.ndarray:
    """Daily-rebalanced equal weight across all assets."""
    matrix = np.asarray(realized_returns, dtype=float)
    if matrix.ndim != 2 or not matrix.size:
        raise ValueError("realized_returns must be a non-empty 2D array")
    return matrix.mean(axis=1)


def buy_and_hold_returns(realized_returns: np.ndarray) -> np.ndarray:
    """Equal weight at t0 with no rebalancing; weights drift with performance."""
    matrix = np.asarray(realized_returns, dtype=float)
    if matrix.ndim != 2 or not matrix.size:
        raise ValueError("realized_returns must be a non-empty 2D array")
    n_assets = matrix.shape[1]
    weights = np.full(n_assets, 1.0 / n_assets, dtype=float)
    portfolio = np.zeros(len(matrix), dtype=float)
    for t in range(len(matrix)):
        portfolio[t] = float(np.dot(weights, matrix[t]))
        grown = weights * (1.0 + matrix[t])
        total = grown.sum()
        weights = grown / total if total > 0 else weights
    return portfolio


def momentum_returns(
    realized_returns: np.ndarray,
    lookback: int = 30,
    one_way_costs: np.ndarray | None = None,
) -> np.ndarray:
    """Top-1 long by trailing cumulative return, executed t+1, net of costs.

    The signal at day ``t`` uses returns strictly before ``t`` and is applied to
    the realized return of ``t`` (no look-ahead). Reuses ``top1_long_returns`` so
    the trade-cost accounting matches the model strategy exactly.
    """
    matrix = np.asarray(realized_returns, dtype=float)
    if matrix.ndim != 2 or not matrix.size:
        raise ValueError("realized_returns must be a non-empty 2D array")
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    t_total, n_assets = matrix.shape
    predictions = np.full((t_total, n_assets), -np.inf, dtype=float)
    for t in range(t_total):
        start = t - lookback
        if start < 0:
            continue  # not enough history -> stay in cash (all -inf -> position -1)
        window = matrix[start:t]
        predictions[t] = np.cumprod(1.0 + window, axis=0)[-1] - 1.0
    # rows without history are all -inf; top1_long_returns treats max<=0 as cash,
    # but -inf breaks argmax comparisons, so map them to a small negative sentinel.
    predictions[~np.isfinite(predictions)] = -1e9
    returns, _ = top1_long_returns(predictions, matrix, one_way_costs=one_way_costs)
    return returns


def baseline_returns(
    realized_returns: np.ndarray,
    momentum_lookback: int = 30,
    one_way_costs: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Convenience: all baseline series keyed by name."""
    matrix = np.asarray(realized_returns, dtype=float)
    return {
        "cash": cash_returns(len(matrix)),
        "equal_weight": equal_weight_returns(matrix),
        "buy_and_hold": buy_and_hold_returns(matrix),
        "momentum": momentum_returns(matrix, momentum_lookback, one_way_costs),
    }


# --------------------------------------------------------------------------- #
# Normal CDF / inverse CDF (no scipy dependency)
# --------------------------------------------------------------------------- #
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's algorithm)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


# --------------------------------------------------------------------------- #
# Statistical robustness
# --------------------------------------------------------------------------- #
def _per_period_sharpe(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=float)
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    return float(np.mean(values) / (std + 1e-12))


def block_bootstrap_sharpe(
    returns: np.ndarray,
    block_size: int = 20,
    n_boot: int = 2000,
    periods_per_year: int = 365,
    seed: int = 0,
    confidence: float = 0.95,
) -> dict[str, float]:
    """Circular block bootstrap of the annualized Sharpe, preserving autocorrelation."""
    values = np.asarray(returns, dtype=float)
    n = len(values)
    if n < 2:
        raise ValueError("returns must have length >= 2")
    if not 1 <= block_size <= n:
        raise ValueError("block_size must be in [1, len(returns)]")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_size))
    ann = math.sqrt(periods_per_year)
    samples = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = (starts[:, None] + np.arange(block_size)[None, :]).ravel() % n
        resampled = values[idx[:n]]
        samples[i] = _per_period_sharpe(resampled) * ann
    alpha = (1.0 - confidence) / 2.0
    return {
        "sharpe_point": _per_period_sharpe(values) * ann,
        "sharpe_bootstrap_mean": float(np.mean(samples)),
        "ci_low": float(np.quantile(samples, alpha)),
        "ci_high": float(np.quantile(samples, 1.0 - alpha)),
        "prob_sharpe_gt_0": float(np.mean(samples > 0.0)),
        "n_boot": int(n_boot),
        "block_size": int(block_size),
    }


def probabilistic_sharpe_ratio(
    returns: np.ndarray, benchmark_sharpe_per_period: float = 0.0
) -> dict[str, float]:
    """PSR: P(true SR > benchmark), correcting for length, skew and kurtosis.

    Sharpe values here are per-period (not annualized), following Bailey & López
    de Prado (2012).
    """
    values = np.asarray(returns, dtype=float)
    n = len(values)
    if n < 3:
        raise ValueError("need at least 3 observations")
    sr = _per_period_sharpe(values)
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) + 1e-12
    z = (values - mean) / std
    skew = float(np.mean(z ** 3))
    kurt = float(np.mean(z ** 4))  # non-excess kurtosis
    denom = math.sqrt(max(1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr ** 2, 1e-12))
    psr = _norm_cdf((sr - benchmark_sharpe_per_period) * math.sqrt(n - 1) / denom)
    return {
        "sharpe_per_period": sr,
        "skew": skew,
        "kurtosis": kurt,
        "psr": float(psr),
        "benchmark_sharpe_per_period": float(benchmark_sharpe_per_period),
    }


def expected_max_sharpe(variance_of_trial_sharpes: float, n_trials: int) -> float:
    """Expected maximum of ``n_trials`` iid Sharpes ~ N(0, var). Used by DSR."""
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if variance_of_trial_sharpes < 0:
        raise ValueError("variance cannot be negative")
    if n_trials == 1:
        return 0.0
    gamma = 0.5772156649015329  # Euler-Mascheroni
    sigma = math.sqrt(variance_of_trial_sharpes)
    e = math.e
    return sigma * (
        (1.0 - gamma) * _norm_ppf(1.0 - 1.0 / n_trials)
        + gamma * _norm_ppf(1.0 - 1.0 / (n_trials * e))
    )


def deflated_sharpe_ratio(
    returns: np.ndarray, variance_of_trial_sharpes: float, n_trials: int
) -> dict[str, float]:
    """DSR: PSR against the expected max Sharpe from ``n_trials`` (multiple testing)."""
    benchmark = expected_max_sharpe(variance_of_trial_sharpes, n_trials)
    result = probabilistic_sharpe_ratio(returns, benchmark_sharpe_per_period=benchmark)
    result["dsr"] = result.pop("psr")
    result["expected_max_sharpe"] = float(benchmark)
    result["n_trials"] = int(n_trials)
    return result


# --------------------------------------------------------------------------- #
# Comparison report
# --------------------------------------------------------------------------- #
def compare_to_baselines(
    strategy_returns: np.ndarray,
    realized_returns: np.ndarray,
    momentum_lookback: int = 30,
    one_way_costs: np.ndarray | None = None,
    periods_per_year: int = 365,
    block_size: int = 20,
    n_boot: int = 2000,
    seed: int = 0,
) -> dict[str, object]:
    """Full comparison: metrics + bootstrap for the strategy and every baseline."""
    strategy = np.asarray(strategy_returns, dtype=float)
    series = {"strategy": strategy, **baseline_returns(realized_returns, momentum_lookback, one_way_costs)}
    report: dict[str, object] = {}
    for name, ret in series.items():
        entry = {
            "metrics": performance_metrics(ret, periods_per_year=periods_per_year),
            "bootstrap": block_bootstrap_sharpe(
                ret, block_size=block_size, n_boot=n_boot,
                periods_per_year=periods_per_year, seed=seed,
            ),
            "psr_vs_zero": probabilistic_sharpe_ratio(ret),
        }
        report[name] = entry
    strat_sharpe = report["strategy"]["metrics"]["sharpe"]
    report["strategy_beats_baseline"] = {
        name: bool(strat_sharpe > report[name]["metrics"]["sharpe"])
        for name in series
        if name != "strategy"
    }
    return report
