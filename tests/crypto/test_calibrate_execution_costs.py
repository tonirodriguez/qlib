import pandas as pd

from work.crypto.calibrate_execution_costs import estimate_asset_costs


def sample_frame(volume=1_000_000.0):
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 101.0],
            "high": [102.0, 103.0, 104.0, 103.0],
            "low": [99.0, 100.0, 100.0, 99.0],
            "close": [101.0, 102.0, 101.0, 102.0],
            "volume": [volume] * 4,
        }
    )


def test_cost_increases_with_order_size():
    costs = estimate_asset_costs(sample_frame(), (1_000.0, 10_000.0, 100_000.0))
    assert costs[0]["one_way_cost"] < costs[1]["one_way_cost"] < costs[2]["one_way_cost"]


def test_cost_decreases_with_liquidity():
    low_liquidity = estimate_asset_costs(sample_frame(volume=10_000.0), (100_000.0,))[0]
    high_liquidity = estimate_asset_costs(sample_frame(volume=10_000_000.0), (100_000.0,))[0]
    assert low_liquidity["slippage_proxy"] > high_liquidity["slippage_proxy"]
