from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Dict, List


@dataclass
class Fill:
    instrument: str
    side: str
    qty: int
    price: float
    fee: float
    status: str = "filled"


class PaperBroker:
    def __init__(
        self,
        initial_cash: float = 100000.0,
        fee_rate: float = 0.001,
        state_path: str | Path = "data/state/paper_broker_state.json",
    ) -> None:
        self.state_path = Path(state_path)
        self.initial_cash = initial_cash
        self.fee_rate = fee_rate
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        if self.state_path.exists():
            self._load()
        else:
            self.cash = initial_cash
            self.positions: Dict[str, int] = {}
            self._save()

    def _load(self) -> None:
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.cash = float(data["cash"])
        self.positions = {k: int(v) for k, v in data["positions"].items()}

    def _save(self) -> None:
        payload = {"cash": self.cash, "positions": self.positions}
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_positions(self) -> Dict[str, int]:
        return dict(self.positions)

    def get_cash(self) -> float:
        return self.cash

    def place_market_order(self, instrument: str, side: str, qty: int, price: float) -> Fill:
        if qty <= 0:
            raise ValueError("qty must be positive")

        gross = qty * price
        fee = gross * self.fee_rate

        if side == "buy":
            total_cost = gross + fee
            if total_cost > self.cash:
                return Fill(instrument, side, qty, price, fee, status="rejected_no_cash")
            self.cash -= total_cost
            self.positions[instrument] = self.positions.get(instrument, 0) + qty

        elif side == "sell":
            current_qty = self.positions.get(instrument, 0)
            if qty > current_qty:
                return Fill(instrument, side, qty, price, fee, status="rejected_no_position")
            self.cash += gross - fee
            new_qty = current_qty - qty
            if new_qty == 0:
                self.positions.pop(instrument, None)
            else:
                self.positions[instrument] = new_qty
        else:
            raise ValueError("side must be 'buy' or 'sell'")

        self._save()
        return Fill(instrument, side, qty, price, fee)