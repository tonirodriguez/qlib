from __future__ import annotations
import pandas as pd


def select_top_n(
    signals: pd.DataFrame,
    top_n: int,
    min_score: float | None = None,
) -> pd.DataFrame:
    df = signals.copy()

    if min_score is not None:
        df = df[df["score"] >= min_score].copy()

    df = df.sort_values("score", ascending=False).head(top_n).copy()
    df["rank"] = range(1, len(df) + 1)
    return df.reset_index(drop=True)