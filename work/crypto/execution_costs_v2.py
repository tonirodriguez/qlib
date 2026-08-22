"""Realistic execution-cost model: maker/taker fee tiers + order-book aware slippage.

This module upgrades the OHLCV proxy in ``calibrate_execution_costs.py`` with a
microstructure-aware model, while remaining honest about which inputs are real
and which are proxies.

Cost of one execution (one way), as a fraction of notional, is::

    one_way_cost = blended_fee + half_spread + market_impact

Components
---------
* ``blended_fee``   maker/taker fees from a configurable tier schedule, blended
  by the expected taker fill fraction. Real exchange input.
* ``half_spread``   from real top-of-book bid/ask when available; otherwise a
  labelled OHLCV range proxy.
* ``market_impact`` square-root impact ``k * sigma * sqrt(Q / L)`` where ``L`` is
  the order-book depth available near touch when available; otherwise a labelled
  average-daily-quote-volume proxy. Orders above ``max_participation * L`` are
  flagged as rejected.

Every estimate records the ``source`` of each component ("orderbook" or
"proxy") so downstream reports never present a proxy as microstructure truth.
Execution is assumed to happen on the next available bar (t+1); this model
prices the cost, the t+1 alignment is enforced by the backtester.

The output vector is aligned to the instrument order and is directly consumable
by ``research_utils.top1_long_returns(one_way_costs=...)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INSTRUMENTS = ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC")


# --------------------------------------------------------------------------- #
# Fee tiers
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FeeTier:
    """A single maker/taker fee tier keyed by trailing 30-day USD volume."""

    min_thirty_day_volume_usd: float
    maker: float
    taker: float


# Placeholder schedule modelled on a typical spot venue. Replace with the real
# schedule for the venue and account before using for any decision.
DEFAULT_FEE_SCHEDULE: tuple[FeeTier, ...] = (
    FeeTier(0.0, 0.0010, 0.0010),
    FeeTier(1_000_000.0, 0.0008, 0.0010),
    FeeTier(10_000_000.0, 0.0006, 0.0008),
    FeeTier(50_000_000.0, 0.0004, 0.0006),
    FeeTier(100_000_000.0, 0.0002, 0.0004),
)


def select_fee_tier(
    schedule: tuple[FeeTier, ...], thirty_day_volume_usd: float
) -> FeeTier:
    """Return the applicable tier for a trailing 30-day volume."""
    if thirty_day_volume_usd < 0:
        raise ValueError("thirty_day_volume_usd cannot be negative")
    if not schedule:
        raise ValueError("fee schedule is empty")
    applicable = [t for t in schedule if thirty_day_volume_usd >= t.min_thirty_day_volume_usd]
    if not applicable:
        return min(schedule, key=lambda t: t.min_thirty_day_volume_usd)
    return max(applicable, key=lambda t: t.min_thirty_day_volume_usd)


def blended_fee(tier: FeeTier, taker_fraction: float) -> float:
    """Blend maker/taker fees by the expected fraction of taker fills."""
    if not 0.0 <= taker_fraction <= 1.0:
        raise ValueError("taker_fraction must be in [0, 1]")
    return float(tier.taker * taker_fraction + tier.maker * (1.0 - taker_fraction))


# --------------------------------------------------------------------------- #
# Spread and impact
# --------------------------------------------------------------------------- #
def half_spread_from_quotes(bid: float, ask: float) -> float:
    """Relative half-spread from a real top-of-book snapshot."""
    if bid <= 0 or ask <= 0 or ask < bid:
        raise ValueError("require 0 < bid <= ask")
    mid = 0.5 * (bid + ask)
    return float((ask - bid) / 2.0 / mid)


def half_spread_from_range(
    median_daily_range: float, floor: float = 0.0001, cap: float = 0.005
) -> float:
    """Labelled OHLCV proxy: a conservative fraction of the median daily range."""
    return float(np.clip(median_daily_range * 0.025, floor, cap))


def square_root_impact(
    order_notional: float,
    liquidity_notional: float,
    volatility: float,
    coefficient: float = 1.0,
    floor: float = 0.0,
    cap: float = 0.05,
) -> float:
    """Square-root market-impact model ``k * sigma * sqrt(Q / L)``.

    ``liquidity_notional`` is order-book depth near touch when available, or an
    average-daily-quote-volume proxy otherwise.
    """
    if order_notional <= 0:
        raise ValueError("order_notional must be positive")
    liquidity = max(liquidity_notional, 1.0)
    participation = order_notional / liquidity
    impact = coefficient * max(volatility, 0.0) * float(np.sqrt(participation))
    return float(np.clip(impact, floor, cap))


# --------------------------------------------------------------------------- #
# Config + per-asset estimate
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CostModelConfig:
    fee_schedule: tuple[FeeTier, ...] = DEFAULT_FEE_SCHEDULE
    thirty_day_volume_usd: float = 0.0
    taker_fraction: float = 1.0
    impact_coefficient: float = 1.0
    max_participation: float = 0.1  # reject orders above 10% of available liquidity
    half_spread_floor: float = 0.0001
    half_spread_cap: float = 0.005
    impact_cap: float = 0.05


@dataclass
class AssetMarketData:
    """Per-asset inputs. Real microstructure fields are optional; proxies fill in.

    ``depth_notional`` is the USD available within a chosen band of the touch
    (real order book). ``bid``/``ask`` are a top-of-book snapshot. When absent,
    ``median_daily_quote_volume`` and ``median_daily_range`` drive the proxies.
    """

    instrument: str
    daily_volatility: float
    median_daily_quote_volume: float
    median_daily_range: float
    bid: float | None = None
    ask: float | None = None
    depth_notional: float | None = None


def estimate_one_way_cost(
    market: AssetMarketData, order_notional: float, config: CostModelConfig
) -> dict[str, object]:
    """Estimate one-way cost for a single asset, labelling each component's source."""
    if order_notional <= 0:
        raise ValueError("order_notional must be positive")

    tier = select_fee_tier(config.fee_schedule, config.thirty_day_volume_usd)
    fee = blended_fee(tier, config.taker_fraction)

    if market.bid is not None and market.ask is not None:
        half_spread = half_spread_from_quotes(market.bid, market.ask)
        spread_source = "orderbook"
    else:
        half_spread = half_spread_from_range(
            market.median_daily_range, config.half_spread_floor, config.half_spread_cap
        )
        spread_source = "proxy"

    if market.depth_notional is not None:
        liquidity = float(market.depth_notional)
        impact_source = "orderbook"
    else:
        liquidity = float(market.median_daily_quote_volume)
        impact_source = "proxy"

    impact = square_root_impact(
        order_notional,
        liquidity,
        market.daily_volatility,
        coefficient=config.impact_coefficient,
        cap=config.impact_cap,
    )
    participation = order_notional / max(liquidity, 1.0)
    rejected = participation > config.max_participation

    one_way = fee + half_spread + impact
    return {
        "instrument": market.instrument,
        "order_notional": float(order_notional),
        "fee": float(fee),
        "fee_tier_min_volume": float(tier.min_thirty_day_volume_usd),
        "half_spread": float(half_spread),
        "half_spread_source": spread_source,
        "market_impact": float(impact),
        "market_impact_source": impact_source,
        "participation": float(participation),
        "max_participation": float(config.max_participation),
        "rejected": bool(rejected),
        "one_way_cost": float(one_way),
        "round_trip_cost": float(2.0 * one_way),
        "execution_timing": "t+1",
    }


def build_one_way_cost_vector(
    instruments: tuple[str, ...],
    market_by_instrument: dict[str, AssetMarketData],
    order_notional: float,
    config: CostModelConfig,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Return (cost vector aligned to ``instruments``, per-asset breakdown).

    The vector plugs straight into ``top1_long_returns(one_way_costs=...)``.
    """
    vector = np.zeros(len(instruments), dtype=float)
    breakdown: list[dict[str, object]] = []
    for i, name in enumerate(instruments):
        if name not in market_by_instrument:
            raise KeyError(f"missing market data for instrument {name!r}")
        estimate = estimate_one_way_cost(market_by_instrument[name], order_notional, config)
        vector[i] = estimate["one_way_cost"]
        breakdown.append(estimate)
    return vector, breakdown


# --------------------------------------------------------------------------- #
# Loading market data from the training CSVs (train-only, holdout preserved)
# --------------------------------------------------------------------------- #
def market_data_from_ohlcv(
    frame: pd.DataFrame,
    instrument: str,
    quotes: pd.DataFrame | None = None,
    depth: pd.DataFrame | None = None,
) -> AssetMarketData:
    """Build ``AssetMarketData`` from a decision-window OHLCV frame.

    ``quotes`` (columns bid, ask) and ``depth`` (column depth_notional) are
    optional real microstructure inputs; when omitted the proxies are used.
    """
    required = {"high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    close = pd.to_numeric(frame["close"], errors="raise")
    high = pd.to_numeric(frame["high"], errors="raise")
    low = pd.to_numeric(frame["low"], errors="raise")
    volume = pd.to_numeric(frame["volume"], errors="raise")
    quote_volume = (close * volume).replace(0, np.nan)
    daily_range = ((high - low) / close).clip(lower=0)
    returns = close.pct_change().dropna()

    bid = ask = depth_notional = None
    if quotes is not None and len(quotes):
        bid = float(pd.to_numeric(quotes["bid"], errors="raise").median())
        ask = float(pd.to_numeric(quotes["ask"], errors="raise").median())
    if depth is not None and len(depth):
        depth_notional = float(pd.to_numeric(depth["depth_notional"], errors="raise").median())

    return AssetMarketData(
        instrument=instrument,
        daily_volatility=float(returns.std()),
        median_daily_quote_volume=float(quote_volume.median()),
        median_daily_range=float(daily_range.median()),
        bid=bid,
        ask=ask,
        depth_notional=depth_notional,
    )


def fee_schedule_from_records(records: list[dict[str, float]]) -> tuple[FeeTier, ...]:
    """Build a fee schedule from a list of {min_thirty_day_volume_usd, maker, taker}."""
    schedule = tuple(
        FeeTier(
            float(r["min_thirty_day_volume_usd"]),
            float(r["maker"]),
            float(r["taker"]),
        )
        for r in records
    )
    if not schedule:
        raise ValueError("fee schedule cannot be empty")
    return schedule


def load_fee_schedule(path: str | Path | None = None) -> tuple[FeeTier, ...]:
    """Load a maker/taker schedule from JSON, or return the default placeholder.

    Resolution order: explicit ``path`` argument, then ``CRYPTO_FEE_SCHEDULE_JSON``,
    then ``DEFAULT_FEE_SCHEDULE``. JSON format is a list of objects with keys
    ``min_thirty_day_volume_usd``, ``maker`` and ``taker``. This lets step 4 flip
    from the placeholder to a real venue schedule with no code change.
    """
    source = path if path is not None else os.getenv("CRYPTO_FEE_SCHEDULE_JSON")
    if not source:
        return DEFAULT_FEE_SCHEDULE
    records = json.loads(Path(source).expanduser().read_text(encoding="utf-8"))
    return fee_schedule_from_records(records)


def _train_only_frame(path: Path, cutoff: pd.Timestamp) -> pd.DataFrame | None:
    """Read a dated CSV keeping only rows at or before ``cutoff`` (causal)."""
    if path is None or not Path(path).exists():
        return None
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    train = frame[frame["date"] <= cutoff]
    return train if len(train) else None


def fold_cost_vector_v2(
    instruments: list[str] | tuple[str, ...],
    ohlcv_dir: str | Path,
    train_end_date,
    order_notional: float,
    config: CostModelConfig,
    quotes_dir: str | Path | None = None,
    depth_dir: str | Path | None = None,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Train-only per-asset one-way cost vector using the v2 model, for one fold.

    Reads OHLCV strictly up to ``train_end_date`` (no leakage). If ``quotes_dir`` or
    ``depth_dir`` hold ``<ASSET>.csv`` files, their train-only medians feed the real
    bid/ask and depth and the component ``source`` becomes ``"orderbook"``;
    otherwise the labelled proxies are used. The vector is aligned to ``instruments``
    and plugs into ``research_utils.top1_long_returns(one_way_costs=...)``.
    """
    ohlcv_dir = Path(ohlcv_dir)
    cutoff = pd.Timestamp(train_end_date)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    market_by_instrument: dict[str, AssetMarketData] = {}
    for instrument in instruments:
        upper = str(instrument).upper()
        frame = pd.read_csv(ohlcv_dir / f"{upper}.csv")
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        train_frame = frame[frame["date"] <= cutoff]
        quotes = _train_only_frame(Path(quotes_dir) / f"{upper}.csv", cutoff) if quotes_dir else None
        depth = _train_only_frame(Path(depth_dir) / f"{upper}.csv", cutoff) if depth_dir else None
        market_by_instrument[instrument] = market_data_from_ohlcv(
            train_frame, instrument, quotes=quotes, depth=depth
        )
    return build_one_way_cost_vector(tuple(instruments), market_by_instrument, order_notional, config)


def env_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


def main() -> None:
    """Calibrate the realistic cost model from train-only OHLCV (+ optional quotes/depth)."""
    source_dir = env_path("CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto/ohlcv")
    output_dir = env_path("CRYPTO_COST_CALIBRATION_V2_DIR", "work/crypto/output/cost_calibration_v2")
    output_dir.mkdir(parents=True, exist_ok=True)
    instruments = tuple(
        item.strip().upper()
        for item in os.getenv("CRYPTO_INSTRUMENTS", ",".join(DEFAULT_INSTRUMENTS)).split(",")
        if item.strip()
    )
    notionals = tuple(
        float(item) for item in os.getenv("CRYPTO_ORDER_NOTIONALS", "1000,10000,100000").split(",")
    )
    holdout_fraction = float(os.getenv("CRYPTO_FINAL_HOLDOUT_FRACTION", "0.15"))
    config = CostModelConfig(
        thirty_day_volume_usd=float(os.getenv("CRYPTO_THIRTY_DAY_VOLUME_USD", "0")),
        taker_fraction=float(os.getenv("CRYPTO_TAKER_FRACTION", "1.0")),
        impact_coefficient=float(os.getenv("CRYPTO_IMPACT_COEFFICIENT", "1.0")),
        max_participation=float(os.getenv("CRYPTO_MAX_PARTICIPATION", "0.1")),
    )

    market_by_instrument: dict[str, AssetMarketData] = {}
    decision_end_dates: list[pd.Timestamp] = []
    for instrument in instruments:
        frame = pd.read_csv(source_dir / f"{instrument}.csv")
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.sort_values("date").drop_duplicates("date", keep="last")
        decision_end = int(len(frame) * (1.0 - holdout_fraction))
        decision_frame = frame.iloc[:decision_end]
        decision_end_dates.append(decision_frame["date"].max())
        market_by_instrument[instrument] = market_data_from_ohlcv(decision_frame, instrument)

    per_notional: dict[str, object] = {}
    rows: list[dict[str, object]] = []
    for notional in notionals:
        vector, breakdown = build_one_way_cost_vector(
            instruments, market_by_instrument, notional, config
        )
        rows.extend(breakdown)
        per_notional[str(int(notional))] = {
            "one_way_cost_by_asset": {
                b["instrument"]: b["one_way_cost"] for b in breakdown
            },
            "rejected_assets": [b["instrument"] for b in breakdown if b["rejected"]],
            "mean_one_way_cost": float(np.mean(vector)),
        }

    summary = {
        "methodology": {
            "fee": "configurable maker/taker tier schedule, blended by taker_fraction",
            "half_spread": "real top-of-book when provided, else labelled OHLCV range proxy",
            "market_impact": "sqrt model k*sigma*sqrt(Q/L); L = order-book depth or ADV proxy",
            "participation_cap": config.max_participation,
            "execution_timing": "t+1",
            "holdout_fraction": holdout_fraction,
            "holdout_used": False,
        },
        "config": {
            "thirty_day_volume_usd": config.thirty_day_volume_usd,
            "taker_fraction": config.taker_fraction,
            "impact_coefficient": config.impact_coefficient,
            "max_participation": config.max_participation,
        },
        "decision_sample_end": min(decision_end_dates).isoformat(),
        "instruments": list(instruments),
        "order_notionals": list(notionals),
        "per_notional": per_notional,
    }
    pd.DataFrame(rows).to_csv(output_dir / "asset_costs_v2.csv", index=False)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
