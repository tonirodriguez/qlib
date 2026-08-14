"""Calibrate reproducible OHLCV-based execution-cost proxies by asset and size."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INSTRUMENTS = ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC")


def env_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


def estimate_asset_costs(
    frame: pd.DataFrame,
    order_notionals: tuple[float, ...],
    fee_rate: float = 0.001,
) -> list[dict[str, float]]:
    """Estimate cost proxies without pretending daily OHLCV is an order book.

    Half-spread is a conservative fraction of the median daily range. Market
    impact increases with the square root of order notional / quote volume and
    is scaled by realized daily volatility.
    """
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if any(value <= 0 for value in order_notionals):
        raise ValueError("Order notionals must be positive")

    close = pd.to_numeric(frame["close"], errors="raise")
    high = pd.to_numeric(frame["high"], errors="raise")
    low = pd.to_numeric(frame["low"], errors="raise")
    volume = pd.to_numeric(frame["volume"], errors="raise")
    quote_volume = (close * volume).replace(0, np.nan)
    daily_range = ((high - low) / close).clip(lower=0)
    returns = close.pct_change().dropna()
    median_quote_volume = float(quote_volume.median())
    median_range = float(daily_range.median())
    daily_volatility = float(returns.std())
    half_spread_proxy = float(np.clip(median_range * 0.025, 0.0001, 0.005))

    estimates: list[dict[str, float]] = []
    for notional in order_notionals:
        participation = notional / max(median_quote_volume, 1.0)
        slippage_proxy = float(np.clip(daily_volatility * np.sqrt(participation), 0.00005, 0.02))
        one_way_cost = fee_rate + half_spread_proxy + slippage_proxy
        estimates.append(
            {
                "order_notional": float(notional),
                "fee_rate": float(fee_rate),
                "half_spread_proxy": half_spread_proxy,
                "slippage_proxy": slippage_proxy,
                "one_way_cost": float(one_way_cost),
                "round_trip_cost": float(2.0 * one_way_cost),
                "median_daily_quote_volume": median_quote_volume,
                "median_daily_range": median_range,
                "daily_volatility": daily_volatility,
            }
        )
    return estimates


def calibrate(
    source_dir: Path,
    instruments: tuple[str, ...],
    holdout_fraction: float,
    order_notionals: tuple[float, ...],
) -> tuple[dict[str, object], pd.DataFrame]:
    if not 0 < holdout_fraction < 0.5:
        raise ValueError("holdout_fraction must be in (0, 0.5)")
    rows: list[dict[str, object]] = []
    decision_end_dates: list[pd.Timestamp] = []
    for instrument in instruments:
        frame = pd.read_csv(source_dir / f"{instrument}.csv")
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.sort_values("date").drop_duplicates("date", keep="last")
        decision_end = int(len(frame) * (1.0 - holdout_fraction))
        decision_frame = frame.iloc[:decision_end]
        decision_end_dates.append(decision_frame["date"].max())
        for estimate in estimate_asset_costs(decision_frame, order_notionals):
            rows.append({"instrument": instrument, **estimate})

    table = pd.DataFrame(rows)
    scenarios: dict[str, object] = {}
    for notional in order_notionals:
        selected = table[table["order_notional"] == notional]
        scenarios[str(int(notional))] = {
            "optimistic": float(selected["one_way_cost"].quantile(0.25)),
            "base": float(selected["one_way_cost"].median()),
            "adverse": float(selected["one_way_cost"].quantile(0.90)),
            "worst_asset": str(selected.loc[selected["one_way_cost"].idxmax(), "instrument"]),
        }
    summary: dict[str, object] = {
        "methodology": {
            "source": "daily OHLCV proxy; not historical bid/ask or order-book replay",
            "holdout_fraction": holdout_fraction,
            "holdout_used": False,
            "half_spread_proxy": "clip(2.5% * median daily high-low range, 1bp, 50bp)",
            "slippage_proxy": "clip(daily volatility * sqrt(order notional / median quote volume), 0.5bp, 200bp)",
        },
        "decision_sample_end": min(decision_end_dates).isoformat(),
        "instruments": list(instruments),
        "order_notionals": list(order_notionals),
        "scenario_one_way_costs": scenarios,
    }
    return summary, table


def main() -> None:
    source_dir = env_path("CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto/ohlcv")
    output_dir = env_path("CRYPTO_COST_CALIBRATION_DIR", "work/crypto/output/cost_calibration")
    output_dir.mkdir(parents=True, exist_ok=True)
    instruments = tuple(
        item.strip().upper()
        for item in os.getenv("CRYPTO_INSTRUMENTS", ",".join(DEFAULT_INSTRUMENTS)).split(",")
        if item.strip()
    )
    notionals = tuple(
        float(item) for item in os.getenv("CRYPTO_ORDER_NOTIONALS", "1000,10000,100000").split(",")
    )
    summary, table = calibrate(
        source_dir,
        instruments,
        holdout_fraction=float(os.getenv("CRYPTO_FINAL_HOLDOUT_FRACTION", "0.15")),
        order_notionals=notionals,
    )
    table.to_csv(output_dir / "asset_costs.csv", index=False)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
