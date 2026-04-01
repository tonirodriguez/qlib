from __future__ import annotations

from pathlib import Path
import yaml
import pandas as pd
from loguru import logger


from infra.paths import ORDERS_DIR
from infra.db import get_conn
from portfolio.ranking import select_top_n


def load_config(config_path: str | Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_target_positions(signal_path: str | Path, config_path: str | Path) -> Path:
    cfg = load_config(config_path)
    signals = pd.read_parquet(signal_path)

    selected = select_top_n(
        signals,
        top_n=int(cfg["top_n"]),
        min_score=cfg.get("min_score"),
    )

    if selected.empty:
        raise ValueError("No assets selected")

    cash_buffer = float(cfg.get("cash_buffer", 0.02))
    investable = 1.0 - cash_buffer

    weight_mode = cfg.get("weight_mode", "equal")
    max_weight = float(cfg.get("max_weight", 1.0))

    if weight_mode != "equal":
        raise NotImplementedError("Only equal weight is implemented in v2")

    base_weight = min(investable / len(selected), max_weight)
    selected["target_weight"] = base_weight

    remainder = investable - selected["target_weight"].sum()
    if remainder > 0:
        selected.loc[selected.index[0], "target_weight"] += remainder

    trade_date = selected["date"].iloc[0]
    out = selected[["date", "instrument", "target_weight", "score", "rank"]].copy()
    out_path = ORDERS_DIR / f"target_positions_{trade_date}.parquet"
    out.to_parquet(out_path, index=False)

    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO target_positions(date, instrument, target_weight, score, rank)
            VALUES (?, ?, ?, ?, ?)
            """,
            out.itertuples(index=False, name=None),
        )

    logger.info(f"Built {len(out)} target positions for {trade_date}")
    return out_path