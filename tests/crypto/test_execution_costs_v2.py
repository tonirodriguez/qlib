import json

import numpy as np
import pandas as pd

from work.crypto.execution_costs_v2 import (
    AssetMarketData,
    CostModelConfig,
    DEFAULT_FEE_SCHEDULE,
    blended_fee,
    build_one_way_cost_vector,
    estimate_one_way_cost,
    fee_schedule_from_records,
    fold_cost_vector_v2,
    half_spread_from_quotes,
    load_fee_schedule,
    select_fee_tier,
    square_root_impact,
)


def test_fee_tier_selection_uses_highest_qualifying_tier():
    tier = select_fee_tier(DEFAULT_FEE_SCHEDULE, 12_000_000.0)
    assert tier.min_thirty_day_volume_usd == 10_000_000.0
    assert tier.taker <= DEFAULT_FEE_SCHEDULE[0].taker


def test_blended_fee_between_maker_and_taker():
    tier = DEFAULT_FEE_SCHEDULE[0]
    assert blended_fee(tier, 0.0) == tier.maker
    assert blended_fee(tier, 1.0) == tier.taker
    mid = blended_fee(tier, 0.5)
    assert min(tier.maker, tier.taker) <= mid <= max(tier.maker, tier.taker)


def test_half_spread_from_quotes_is_relative():
    hs = half_spread_from_quotes(bid=99.0, ask=101.0)
    assert abs(hs - (1.0 / 100.0)) < 1e-9


def test_impact_grows_with_size_and_shrinks_with_liquidity():
    small = square_root_impact(1_000.0, 1_000_000.0, 0.05)
    large = square_root_impact(100_000.0, 1_000_000.0, 0.05)
    deep = square_root_impact(100_000.0, 100_000_000.0, 0.05)
    assert small < large
    assert deep < large


def test_orderbook_inputs_are_labelled_over_proxy():
    proxy = AssetMarketData("BTC", 0.04, 5_000_000.0, 0.03)
    real = AssetMarketData("BTC", 0.04, 5_000_000.0, 0.03, bid=100.0, ask=100.2, depth_notional=2_000_000.0)
    cfg = CostModelConfig()
    e_proxy = estimate_one_way_cost(proxy, 10_000.0, cfg)
    e_real = estimate_one_way_cost(real, 10_000.0, cfg)
    assert e_proxy["half_spread_source"] == "proxy"
    assert e_proxy["market_impact_source"] == "proxy"
    assert e_real["half_spread_source"] == "orderbook"
    assert e_real["market_impact_source"] == "orderbook"


def test_participation_cap_flags_rejection():
    thin = AssetMarketData("XLM", 0.06, 50_000.0, 0.05)
    cfg = CostModelConfig(max_participation=0.1)
    estimate = estimate_one_way_cost(thin, 100_000.0, cfg)
    assert estimate["rejected"] is True


def test_cost_vector_is_aligned_and_plugs_into_backtester_shape():
    instruments = ("BTC", "ETH", "SOL")
    market = {
        "BTC": AssetMarketData("BTC", 0.03, 50_000_000.0, 0.02),
        "ETH": AssetMarketData("ETH", 0.04, 20_000_000.0, 0.03),
        "SOL": AssetMarketData("SOL", 0.06, 5_000_000.0, 0.05),
    }
    vector, breakdown = build_one_way_cost_vector(instruments, market, 10_000.0, CostModelConfig())
    assert vector.shape == (3,)
    assert [b["instrument"] for b in breakdown] == list(instruments)
    # thinner, more volatile asset should not be the cheapest
    assert vector[2] >= vector[0]


def test_load_fee_schedule_default_and_from_json(tmp_path):
    assert load_fee_schedule() is DEFAULT_FEE_SCHEDULE
    records = [
        {"min_thirty_day_volume_usd": 0.0, "maker": 0.0009, "taker": 0.0011},
        {"min_thirty_day_volume_usd": 5_000_000.0, "maker": 0.0005, "taker": 0.0007},
    ]
    path = tmp_path / "fees.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    schedule = load_fee_schedule(path)
    assert len(schedule) == 2
    assert select_fee_tier(schedule, 6_000_000.0).taker == 0.0007


def test_fee_schedule_from_records_rejects_empty():
    try:
        fee_schedule_from_records([])
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty schedule")


def _write_ohlcv(path, prices, volume=5_000_000.0):
    dates = pd.date_range("2023-08-11", periods=len(prices), freq="D", tz="UTC")
    pd.DataFrame(
        {
            "date": dates,
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [volume] * len(prices),
        }
    ).to_csv(path, index=False)


def test_fold_cost_vector_v2_is_train_only_and_uses_proxy_without_quotes(tmp_path):
    ohlcv = tmp_path / "ohlcv"
    ohlcv.mkdir()
    prices = [100.0 + i for i in range(40)]
    for asset in ("BTC", "ETH"):
        _write_ohlcv(ohlcv / f"{asset}.csv", prices)
    cutoff = pd.Timestamp("2023-08-30", tz="UTC")  # only first 20 rows are train
    vector, breakdown = fold_cost_vector_v2(
        ["BTC", "ETH"], ohlcv, cutoff, 10_000.0, CostModelConfig()
    )
    assert vector.shape == (2,)
    assert all(b["half_spread_source"] == "proxy" for b in breakdown)
    assert all(b["market_impact_source"] == "proxy" for b in breakdown)


def test_fold_cost_vector_v2_flips_to_orderbook_with_quotes_and_depth(tmp_path):
    ohlcv = tmp_path / "ohlcv"
    quotes = tmp_path / "quotes"
    depth = tmp_path / "depth"
    for d in (ohlcv, quotes, depth):
        d.mkdir()
    prices = [100.0 + i for i in range(40)]
    dates = pd.date_range("2023-08-11", periods=40, freq="D", tz="UTC")
    for asset in ("BTC", "ETH"):
        _write_ohlcv(ohlcv / f"{asset}.csv", prices)
        pd.DataFrame({"date": dates, "bid": [99.9] * 40, "ask": [100.1] * 40}).to_csv(
            quotes / f"{asset}.csv", index=False
        )
        pd.DataFrame({"date": dates, "depth_notional": [3_000_000.0] * 40}).to_csv(
            depth / f"{asset}.csv", index=False
        )
    cutoff = pd.Timestamp("2023-08-30", tz="UTC")
    _, breakdown = fold_cost_vector_v2(
        ["BTC", "ETH"], ohlcv, cutoff, 10_000.0, CostModelConfig(),
        quotes_dir=quotes, depth_dir=depth,
    )
    assert all(b["half_spread_source"] == "orderbook" for b in breakdown)
    assert all(b["market_impact_source"] == "orderbook" for b in breakdown)
