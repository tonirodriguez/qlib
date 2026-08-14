import numpy as np
import pandas as pd

from work.crypto.analyze_crypto_universe import analyze, cluster_assets


def test_clustering_groups_highly_correlated_assets():
    correlation = pd.DataFrame(
        [[1.0, 0.9, 0.1], [0.9, 1.0, 0.2], [0.1, 0.2, 1.0]],
        index=["A", "B", "C"], columns=["A", "B", "C"],
    )
    clusters = cluster_assets(correlation, distance_threshold=0.25)
    assert clusters["A"] == clusters["B"]
    assert clusters["A"] != clusters["C"]


def test_analysis_reserves_holdout_from_all_decision_statistics():
    rng = np.random.default_rng(42)
    index = pd.date_range("2020-01-01", periods=200, tz="UTC")
    assets = ["BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC"]
    returns = rng.normal(0, 0.01, size=(200, len(assets)))
    closes = pd.DataFrame(100 * np.cumprod(1 + returns, axis=0), index=index, columns=assets)
    volumes = pd.DataFrame(1_000_000.0, index=index, columns=assets)

    summary, _, _ = analyze(closes, volumes, holdout_fraction=0.15)

    assert summary["decision_sample"]["rows"] == 170
    assert summary["reserved_holdout"]["rows"] == 30
    assert summary["methodology"]["holdout_used"] is False
