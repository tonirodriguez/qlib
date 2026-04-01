from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import pandas as pd

from execution.paper_broker import PaperBroker
from infra.paths import ORDERS_DIR, REPORTS_DIR, STATE_DIR


def generate_orders_from_targets(
    targets: pd.DataFrame,
    prices: dict[str, float],
    broker: PaperBroker,
) -> list[dict]:
    cash = broker.get_cash()
    current_positions = broker.get_positions()

    portfolio_value = cash
    for instrument, qty in current_positions.items():
        portfolio_value += qty * prices[instrument]

    orders: list[dict] = []

    target_qty = {}
    for _, row in targets.iterrows():
        instrument = row["instrument"]
        weight = float(row["target_weight"])
        price = float(prices[instrument])
        dollars = portfolio_value * weight
        qty = int(dollars // price)
        target_qty[instrument] = qty

    all_instruments = set(current_positions) | set(target_qty)

    for instrument in sorted(all_instruments):
        current = current_positions.get(instrument, 0)
        target = target_qty.get(instrument, 0)
        delta = target - current

        if delta > 0:
            orders.append(
                {"instrument": instrument, "side": "buy", "qty": delta, "price": prices[instrument]}
            )
        elif delta < 0:
            orders.append(
                {"instrument": instrument, "side": "sell", "qty": abs(delta), "price": prices[instrument]}
            )

    return orders


def execute_target_positions(
    target_path: str | Path,
    prices: dict[str, float],
) -> Path:
    targets = pd.read_parquet(target_path)
    broker = PaperBroker(state_path=STATE_DIR / "paper_broker_state.json")

    orders = generate_orders_from_targets(targets, prices, broker)

    fills = []
    for order in orders:
        fill = broker.place_market_order(
            instrument=order["instrument"],
            side=order["side"],
            qty=int(order["qty"]),
            price=float(order["price"]),
        )
        fills.append(asdict(fill))

    out = pd.DataFrame(fills)
    trade_date = str(targets["date"].iloc[0])
    out_path = REPORTS_DIR / f"fills_{trade_date}.parquet"
    out.to_parquet(out_path, index=False)
    return out_path


if __name__ == "__main__":
    import sys
    import json

    target_path = sys.argv[1]
    prices = json.loads(sys.argv[2])  # {"AAPL":190,"MSFT":420,...}
    result = execute_target_positions(target_path, prices)
    print(f"Fills saved to {result}")