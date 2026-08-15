import numpy as np

from work.crypto.execution_costs_v2 import (
    AssetMarketData,
    CostModelConfig,
    DEFAULT_FEE_SCHEDULE,
    blended_fee,
    build_one_way_cost_vector,
    estimate_one_way_cost,
    half_spread_from_quotes,
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
