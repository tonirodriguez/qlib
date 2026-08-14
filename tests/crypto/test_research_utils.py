import numpy as np

from work.crypto.research_utils import (
    apply_clip_bounds,
    evaluate_cost_scenarios,
    fit_clip_bounds,
    performance_metrics,
    top1_long_returns,
)


def test_future_values_do_not_change_fitted_preprocessing():
    train = np.arange(20, dtype=float).reshape(10, 2)
    future_a = np.array([[20.0, 21.0]])
    future_b = np.array([[20_000.0, -20_000.0]])

    bounds = fit_clip_bounds(train, quantile=0.9)

    np.testing.assert_allclose(
        apply_clip_bounds(train, bounds),
        apply_clip_bounds(train, fit_clip_bounds(train, quantile=0.9)),
    )
    assert not np.array_equal(
        apply_clip_bounds(future_a, bounds),
        apply_clip_bounds(future_b, bounds),
    )


def test_costs_apply_only_when_position_changes():
    predictions = np.array([[-1.0, -2.0], [1.0, 0.0], [2.0, 0.0], [0.0, 3.0], [-1.0, -2.0]])
    realized = np.full_like(predictions, 0.01)

    returns, positions = top1_long_returns(predictions, realized, transaction_cost=0.001)

    np.testing.assert_array_equal(positions, [-1, 0, 0, 1, -1])
    np.testing.assert_allclose(returns, [0.0, 0.009, 0.01, 0.008, -0.001])


def test_crypto_metrics_use_365_day_annualization():
    returns = np.array([0.01, -0.005, 0.007, 0.002])
    metrics = performance_metrics(returns)
    expected = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(365)
    assert metrics["sharpe"] == expected
    assert metrics["max_drawdown"] <= 0
    assert "sortino" in metrics
    assert "calmar" in metrics
    assert metrics["cvar_95"] <= metrics["var_95"]


def test_cost_scenarios_degrade_monotonically():
    predictions = np.array([[1.0, 0.0], [0.0, 1.0]] * 20)
    realized = np.full_like(predictions, 0.01)
    scenarios = evaluate_cost_scenarios(predictions, realized)

    assert scenarios["optimistic"]["equity_final"] > scenarios["base"]["equity_final"]
    assert scenarios["base"]["equity_final"] > scenarios["adverse"]["equity_final"]


def test_asset_specific_cost_charges_exit_and_entry_on_switch():
    predictions = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, -2.0]])
    realized = np.zeros_like(predictions)
    returns, positions = top1_long_returns(
        predictions, realized, one_way_costs=np.array([0.001, 0.003])
    )

    np.testing.assert_array_equal(positions, [0, 1, -1])
    np.testing.assert_allclose(returns, [-0.001, -0.004, -0.003])
