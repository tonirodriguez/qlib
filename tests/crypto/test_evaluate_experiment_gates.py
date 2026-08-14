from work.crypto.evaluate_experiment_gates import evaluate_universe


GATES = {
    "minimum_seed_count": 3,
    "minimum_outer_fold_count_per_seed": 3,
    "calibrated_cost_sharpe_median_min": 0.0,
    "calibrated_cost_positive_fold_fraction_min": 2 / 3,
    "maximum_drawdown_worst_fold_min": -0.5,
    "adverse_cost_sharpe_mean_min": 0.0,
    "outperform_benchmark_fold_fraction_min": 0.5,
}


def metrics(**overrides):
    values = {
        "seeds": [42, 43, 44],
        "fold_observations": 9,
        "calibrated_cost_sharpe_median": 0.4,
        "calibrated_cost_positive_fold_fraction": 0.75,
        "maximum_drawdown_worst_fold": -0.4,
        "adverse_cost_sharpe_mean": 0.2,
        "outperform_benchmark_fold_fraction": 0.6,
    }
    values.update(overrides)
    return values


def test_all_predeclared_gates_must_pass():
    assert evaluate_universe(metrics(), GATES)["passed"] is True
    failed = evaluate_universe(metrics(maximum_drawdown_worst_fold=-0.7), GATES)
    assert failed["passed"] is False
    assert failed["checks"]["maximum_drawdown"] is False


def test_smoke_budget_cannot_pass_formal_gates():
    result = evaluate_universe(metrics(seeds=[42], fold_observations=2), GATES)
    assert result["passed"] is False
    assert result["checks"]["minimum_seed_count"] is False
