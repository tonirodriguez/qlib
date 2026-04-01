from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import numpy as np
from loguru import logger

from execution.paper_broker import PaperBroker
from infra.db import get_conn
from infra.paths import REPORTS_DIR


def generate_orders_from_targets(
    targets: pd.DataFrame,
    prices: dict[str, float],
    broker: PaperBroker,
) -> list[dict]:
    cash = broker.get_cash()
    positions = broker.get_positions()

    portfolio_value = cash
    for instrument, qty in positions.items():
        if instrument in prices:
            portfolio_value += int(qty) * float(prices[instrument])

    target_qty = {}
    for _, row in targets.iterrows():
        instrument = row["instrument"]
        weight = float(row["target_weight"])
        #price = float(prices[instrument])
        price = prices.get(instrument)

        if price is None or np.isnan(price):
            print(f"Advertencia: No se encontró precio para {instrument}. Saltando operación.")
            continue  # Salta a la siguiente acción en 'targets'

        price = float(price)
        dollars = portfolio_value * weight
        target_qty[instrument] = int(dollars // price)

    all_instruments = set(positions) | set(target_qty)
    orders = []

    for instrument in sorted(all_instruments):
        current = int(positions.get(instrument, 0))
        target = int(target_qty.get(instrument, 0))
        delta = target - current

        if delta > 0:
            orders.append(
                {"instrument": instrument, "side": "buy", "qty": delta, "price": float(prices[instrument])}
            )
        elif delta < 0:
            orders.append(
                {"instrument": instrument, "side": "sell", "qty": abs(delta), "price": float(prices[instrument])}
            )

    return orders


def execute_target_positions(target_path: str | Path, prices: dict[str, float]) -> Path:
    broker = PaperBroker()
    targets = pd.read_parquet(target_path)
    trade_date = str(targets["date"].iloc[0])

    orders = generate_orders_from_targets(targets, prices, broker)

    fills = []
    with get_conn() as conn:
        for order in orders:
            conn.execute(
                """
                INSERT INTO orders(date, instrument, side, qty, price, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_date,
                    order["instrument"],
                    order["side"],
                    int(order["qty"]),
                    float(order["price"]),
                    "created",
                ),
            )

            fill = broker.place_market_order(
                instrument=order["instrument"],
                side=order["side"],
                qty=int(order["qty"]),
                price=float(order["price"]),
                conn=conn,
            )

            conn.execute(
                """
                INSERT INTO fills(date, instrument, side, qty, price, fee, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_date,
                    fill.instrument,
                    fill.side,
                    fill.qty,
                    fill.price,
                    fill.fee,
                    fill.status,
                ),
            )

            fills.append(
                {
                    "date": trade_date,
                    "instrument": fill.instrument,
                    "side": fill.side,
                    "qty": fill.qty,
                    "price": fill.price,
                    "fee": fill.fee,
                    "status": fill.status,
                }
            )

    out = pd.DataFrame(fills)
    out_path = REPORTS_DIR / f"fills_{trade_date}.parquet"
    out.to_parquet(out_path, index=False)
    logger.info(f"Saved fills to {out_path}")
    return out_path


if __name__ == "__main__":
    import sys

    target_path = sys.argv[1]
    prices = json.loads(sys.argv[2])
    execute_target_positions(target_path, prices)
