from __future__ import annotations

from pathlib import Path
import pandas as pd
import qlib
from qlib.workflow import R
from loguru import logger

from infra.paths import SIGNALS_DIR
from infra.db import get_conn


def export_latest_predictions(
    experiment_name: str,
    recorder_id: str | None = None,
    provider_uri: str = "~/.qlib/qlib_data/us_data",
    region: str = "us",
    model_version: str = "lgbm_v2",
) -> Path:
    qlib.init(provider_uri=provider_uri, region=region)

    if recorder_id:
        recorder = R.get_recorder(recorder_id=recorder_id, experiment_name=experiment_name)
    else:
        recorder = R.get_recorder(experiment_name=experiment_name)

    pred_df = recorder.load_object("pred.pkl")

    if isinstance(pred_df, pd.Series):
        pred_df = pred_df.to_frame("score")
    elif "score" not in pred_df.columns:
        pred_df.columns = ["score"]

    pred_df = pred_df.reset_index()

    # Esperamos columnas tipo: datetime, instrument, score
    if "datetime" in pred_df.columns:
        pred_df["date"] = pd.to_datetime(pred_df["datetime"]).dt.strftime("%Y-%m-%d")
    elif "date" in pred_df.columns:
        pred_df["date"] = pd.to_datetime(pred_df["date"]).dt.strftime("%Y-%m-%d")
    else:
        raise ValueError("Prediction dataframe has no datetime/date column")

    latest_date = pred_df["date"].max()
    latest = pred_df[pred_df["date"] == latest_date].copy()

    if "instrument" not in latest.columns:
        raise ValueError("Prediction dataframe has no instrument column")

    latest = latest.sort_values("score", ascending=False).reset_index(drop=True)
    latest["rank"] = latest.index + 1
    latest["model_version"] = model_version

    out = latest[["date", "instrument", "score", "rank", "model_version"]]
    out_path = SIGNALS_DIR / f"signals_{latest_date}.parquet"
    out.to_parquet(out_path, index=False)

    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO signals(date, instrument, score, rank, model_version)
            VALUES (?, ?, ?, ?, ?)
            """,
            out.itertuples(index=False, name=None),
        )

    logger.info(f"Exported {len(out)} signals for {latest_date} to {out_path}")
    return out_path


if __name__ == "__main__":
    export_latest_predictions(experiment_name="backtest_analysis")