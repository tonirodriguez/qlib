"""Leakage-aware correlation and clustering analysis for the crypto universe."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INSTRUMENTS = ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC")


def env_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_market_data(source_dir: Path, instruments: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
    closes: dict[str, pd.Series] = {}
    quote_volumes: dict[str, pd.Series] = {}
    for instrument in instruments:
        path = source_dir / f"{instrument}.csv"
        frame = pd.read_csv(path)
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame = frame.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
        closes[instrument] = pd.to_numeric(frame["close"], errors="raise")
        quote_volumes[instrument] = pd.to_numeric(frame["volume"], errors="raise") * closes[instrument]
    return pd.DataFrame(closes).dropna(), pd.DataFrame(quote_volumes).dropna()


def cluster_assets(correlation: pd.DataFrame, distance_threshold: float = 0.35) -> dict[str, int]:
    if not 0 < distance_threshold < 1:
        raise ValueError("distance_threshold must be in (0, 1)")
    distance = (1.0 - correlation.abs()).clip(lower=0.0, upper=1.0)
    np.fill_diagonal(distance.values, 0.0)
    tree = linkage(squareform(distance.values, checks=True), method="average")
    labels = fcluster(tree, t=distance_threshold, criterion="distance")
    return {asset: int(label) for asset, label in zip(correlation.index, labels)}


def pair_statistics(returns: pd.DataFrame, left: str, right: str) -> dict[str, float | str]:
    rolling = returns[left].rolling(90).corr(returns[right]).dropna()
    return {
        "pair": f"{left}/{right}",
        "pearson": float(returns[left].corr(returns[right], method="pearson")),
        "spearman": float(returns[left].corr(returns[right], method="spearman")),
        "rolling_90d_median": float(rolling.median()),
        "rolling_90d_min": float(rolling.min()),
        "rolling_90d_max": float(rolling.max()),
    }


def analyze(
    closes: pd.DataFrame,
    quote_volumes: pd.DataFrame,
    holdout_fraction: float = 0.15,
    cluster_distance: float = 0.35,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    if not 0 < holdout_fraction < 0.5:
        raise ValueError("holdout_fraction must be in (0, 0.5)")
    decision_end = int(len(closes) * (1.0 - holdout_fraction))
    decision_closes = closes.iloc[:decision_end]
    decision_volumes = quote_volumes.reindex(decision_closes.index)
    returns = decision_closes.pct_change().dropna()
    pearson = returns.corr(method="pearson")
    spearman = returns.corr(method="spearman")
    clusters = cluster_assets(pearson, distance_threshold=cluster_distance)

    pairs = pearson.where(np.triu(np.ones(pearson.shape), k=1).astype(bool)).stack()
    ranked_pairs = sorted(
        (
            {"pair": f"{left}/{right}", "correlation": float(value)}
            for (left, right), value in pairs.items()
        ),
        key=lambda item: abs(item["correlation"]),
        reverse=True,
    )
    annual_volatility = returns.std() * np.sqrt(365)
    median_quote_volume = decision_volumes.median()

    summary: dict[str, object] = {
        "methodology": {
            "holdout_fraction": holdout_fraction,
            "holdout_used": False,
            "cluster_distance": cluster_distance,
            "distance_metric": "1 - abs(Pearson correlation)",
            "linkage": "average",
        },
        "decision_sample": {
            "rows": len(decision_closes),
            "start": decision_closes.index.min().isoformat(),
            "end": decision_closes.index.max().isoformat(),
        },
        "reserved_holdout": {
            "rows": len(closes) - decision_end,
            "start": closes.index[decision_end].isoformat(),
            "end": closes.index.max().isoformat(),
        },
        "clusters": clusters,
        "cluster_members": {
            str(cluster): sorted(asset for asset, label in clusters.items() if label == cluster)
            for cluster in sorted(set(clusters.values()))
        },
        "highest_absolute_correlations": ranked_pairs[:10],
        "focus_pairs": [
            pair_statistics(returns, "XRP", "XLM"),
            pair_statistics(returns, "LTC", "BTC"),
        ],
        "asset_statistics": {
            asset: {
                "annualized_volatility": float(annual_volatility[asset]),
                "median_daily_quote_volume": float(median_quote_volume[asset]),
                "observations": int(returns[asset].count()),
            }
            for asset in returns.columns
        },
    }
    return summary, pearson, spearman


def save_heatmap(correlation: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(10, 8))
    image = axis.imshow(correlation.values, vmin=-1, vmax=1, cmap="coolwarm")
    axis.set_xticks(range(len(correlation)), correlation.columns, rotation=45, ha="right")
    axis.set_yticks(range(len(correlation)), correlation.index)
    for row in range(len(correlation)):
        for column in range(len(correlation)):
            axis.text(column, row, f"{correlation.iloc[row, column]:.2f}", ha="center", va="center", fontsize=8)
    axis.set_title("Crypto return correlation — decision sample only")
    fig.colorbar(image, ax=axis, shrink=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    instruments = tuple(
        item.strip().upper()
        for item in os.getenv("CRYPTO_INSTRUMENTS", ",".join(DEFAULT_INSTRUMENTS)).split(",")
        if item.strip()
    )
    source_dir = env_path("CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto/ohlcv")
    output_dir = env_path("CRYPTO_UNIVERSE_ANALYSIS_DIR", "work/crypto/output/universe_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    closes, quote_volumes = load_market_data(source_dir, instruments)
    summary, pearson, spearman = analyze(
        closes,
        quote_volumes,
        holdout_fraction=float(os.getenv("CRYPTO_FINAL_HOLDOUT_FRACTION", "0.15")),
        cluster_distance=float(os.getenv("CRYPTO_CLUSTER_DISTANCE", "0.35")),
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pearson.to_csv(output_dir / "pearson_correlation.csv")
    spearman.to_csv(output_dir / "spearman_correlation.csv")
    save_heatmap(pearson, output_dir / "correlation_heatmap.png")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"Universe analysis written to {output_dir}")


if __name__ == "__main__":
    main()
