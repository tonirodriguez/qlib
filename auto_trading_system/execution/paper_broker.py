from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from loguru import logger

from infra.db import get_conn


@dataclass
class Fill:
    instrument: str
    side: str
    qty: int
    price: float
    fee: float
    status: str


class PaperBroker:
    def __init__(self, initial_cash: float = 100000.0, fee_rate: float = 0.001) -> None:
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate
        self._bootstrap()

    def _bootstrap(self) -> None:
        with get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM broker_state").fetchall()
            if not rows:
                conn.execute(
                    "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
                    ("cash", str(self.initial_cash)),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
                    ("positions", json.dumps({})),
                )

    def get_cash(self, conn: sqlite3.Connection | None = None) -> float:
        if conn is None:
            with get_conn() as conn:
                row = conn.execute("SELECT value FROM broker_state WHERE key='cash'").fetchone()
                return float(row["value"])
        row = conn.execute("SELECT value FROM broker_state WHERE key='cash'").fetchone()
        return float(row["value"])

    def set_cash(self, cash: float, conn: sqlite3.Connection | None = None) -> None:
        if conn is None:
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
                    ("cash", str(cash)),
                )
            return
        conn.execute(
            "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
            ("cash", str(cash)),
        )

    def get_positions(self, conn: sqlite3.Connection | None = None) -> dict[str, int]:
        if conn is None:
            with get_conn() as conn:
                row = conn.execute("SELECT value FROM broker_state WHERE key='positions'").fetchone()
                return json.loads(row["value"])
        row = conn.execute("SELECT value FROM broker_state WHERE key='positions'").fetchone()
        return json.loads(row["value"])

    def set_positions(self, positions: dict[str, int], conn: sqlite3.Connection | None = None) -> None:
        if conn is None:
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
                    ("positions", json.dumps(positions)),
                )
            return
        conn.execute(
            "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
            ("positions", json.dumps(positions)),
        )

    def set_state(self, cash: float, positions: dict[str, int], conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
            ("cash", str(cash)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO broker_state(key, value) VALUES (?, ?)",
            ("positions", json.dumps(positions)),
        )

    def place_market_order(
        self,
        instrument: str,
        side: str,
        qty: int,
        price: float,
        conn: sqlite3.Connection | None = None,
    ) -> Fill:
        if qty <= 0:
            raise ValueError("qty must be positive")

        cash = self.get_cash(conn)
        positions = self.get_positions(conn)
        gross = qty * price
        fee = gross * self.fee_rate

        if side == "buy":
            total = gross + fee
            if total > cash:
                return Fill(instrument, side, qty, price, fee, "rejected_no_cash")
            cash -= total
            positions[instrument] = int(positions.get(instrument, 0)) + qty

        elif side == "sell":
            current = int(positions.get(instrument, 0))
            if qty > current:
                return Fill(instrument, side, qty, price, fee, "rejected_no_position")
            cash += gross - fee
            remaining = current - qty
            if remaining == 0:
                positions.pop(instrument, None)
            else:
                positions[instrument] = remaining
        else:
            raise ValueError("side must be buy/sell")

        if conn is None:
            with get_conn() as tx_conn:
                self.set_state(cash, positions, tx_conn)
        else:
            self.set_state(cash, positions, conn)
        logger.info(f"Filled {side} {qty} {instrument} @ {price:.2f}")
        return Fill(instrument, side, qty, price, fee, "filled")
