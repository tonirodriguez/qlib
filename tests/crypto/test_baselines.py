import numpy as np

from work.crypto.baselines import (
    baseline_returns,
    block_bootstrap_sharpe,
    buy_and_hold_returns,
    cash_returns,
    compare_to_baselines,
    deflated_sharpe_ratio,
    equal_weight_returns,
    expected_max_sharpe,
    momentum_returns,
    probabilistic_sharpe_ratio,
)


def test_cash_is_flat():
    assert np.all(cash_returns(5) == 0.0)


def test_equal_weight_matches_row_mean():
    realized = np.array([[0.01, 0.03], [-0.02, 0.02]])
    np.testing.assert_allclose(equal_weight_returns(realized), [0.02, 0.0])


def test_buy_and_hold_weights_drift_vs_rebalanced():
    realized = np.array([[0.5, -0.1], [0.5, -0.1], [0.5, -0.1]])
    bah = buy_and_hold_returns(realized)
    ew = equal_weight_returns(realized)
    # after the winner grows, buy&hold tilts toward it -> diverges from equal weight
    assert bah[0] == ew[0]
    assert bah[-1] > ew[-1]


def test_momentum_has_no_lookahead_and_matches_length():
    rng = np.random.default_rng(0)
    realized = rng.normal(0, 0.02, size=(80, 4))
    out = momentum_returns(realized, lookback=10)
    assert out.shape == (80,)
    # first `lookback` rows have no history -> cash -> zero return
    assert np.allclose(out[:10], 0.0)


def test_baseline_returns_keys():
    realized = np.random.default_rng(1).normal(0, 0.02, size=(60, 3))
    series = baseline_returns(realized, momentum_lookback=15)
    assert set(series) == {"cash", "equal_weight", "buy_and_hold", "momentum"}
    assert all(v.shape == (60,) for v in series.values())


def test_block_bootstrap_ci_ordered_and_prob_bounded():
    returns = np.random.default_rng(2).normal(0.001, 0.02, size=300)
    res = block_bootstrap_sharpe(returns, block_size=20, n_boot=500, seed=3)
    assert res["ci_low"] <= res["sharpe_bootstrap_mean"] <= res["ci_high"]
    assert 0.0 <= res["prob_sharpe_gt_0"] <= 1.0


def test_psr_higher_for_stronger_track_record():
    weak = np.random.default_rng(4).normal(0.0002, 0.02, size=300)
    strong = np.random.default_rng(4).normal(0.003, 0.02, size=300)
    assert probabilistic_sharpe_ratio(strong)["psr"] > probabilistic_sharpe_ratio(weak)["psr"]


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(0.25, 1) == 0.0
    assert expected_max_sharpe(0.25, 50) > expected_max_sharpe(0.25, 5) > 0.0


def test_dsr_below_psr_when_many_trials():
    returns = np.random.default_rng(5).normal(0.002, 0.02, size=400)
    psr = probabilistic_sharpe_ratio(returns)["psr"]
    dsr = deflated_sharpe_ratio(returns, variance_of_trial_sharpes=0.25, n_trials=50)["dsr"]
    assert dsr < psr


def test_compare_to_baselines_structure():
    rng = np.random.default_rng(6)
    realized = rng.normal(0, 0.02, size=(120, 4))
    strategy = realized[:, 0] * 0.5  # arbitrary strategy series
    report = compare_to_baselines(strategy, realized, momentum_lookback=20, n_boot=300)
    assert set(report["strategy_beats_baseline"]) == {"cash", "equal_weight", "buy_and_hold", "momentum"}
    for name in ("strategy", "cash", "equal_weight", "buy_and_hold", "momentum"):
        assert "metrics" in report[name] and "bootstrap" in report[name]
