from __future__ import annotations

from pathlib import Path
import yaml
import pandas as pd

from infra.paths import ORDERS_DIR, SIGNALS_DIR
from portfolio.ranking import select_top_n


def load_strategy_config(config_path: str | Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_target_positions(signal_path: str | Path, config_path: str | Path) -> Path:
    cfg = load_strategy_config(config_path)
    signals = pd.read_parquet(signal_path)

    selected = select_top_n(
        signals,
        top_n=cfg["top_n"],
        min_score=cfg.get("min_score"),
    )

    cash_buffer = float(cfg.get("cash_buffer", 0.02))
    investable_weight = max(0.0, 1.0 - cash_buffer)

    if len(selected) == 0:
        raise ValueError("No valid assets selected after filtering.")

    weight = investable_weight / len(selected)
    max_weight = float(cfg.get("max_weight", 1.0))
    weight = min(weight, max_weight)

    selected["target_weight"] = weight

    remainder = investable_weight - selected["target_weight"].sum()
    if remainder > 0:
        selected.loc[selected.index[0], "target_weight"] += remainder

    trade_date = str(selected["date"].iloc[0])
    out_path = ORDERS_DIR / f"target_positions_{trade_date}.parquet"
    selected[["date", "instrument", "score", "rank", "target_weight"]].to_parquet(
        out_path, index=False
    )
    return out_path


if __name__ == "__main__":
    import sys

    signal_path = sys.argv[1]
    config_path = sys.argv[2]
    out = build_target_positions(signal_path, config_path)
    print(f"Target positions saved to {out}")