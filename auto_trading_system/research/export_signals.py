from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import pandas as pd

from infra.paths import SIGNALS_DIR

def export_mock_signals(trade_date: str) -> Path:
    # Sustituye esto por la lectura real desde el recorder o predicciones
    rows = [
        {"date": trade_date, "instrument": "AAPL", "score": 0.021},
        {"date": trade_date, "instrument": "MSFT", "score": 0.019},
        {"date": trade_date, "instrument": "NVDA", "score": 0.018},
        {"date": trade_date, "instrument": "AMZN", "score": 0.017},
        {"date": trade_date, "instrument": "META", "score": 0.016},
        {"date": trade_date, "instrument": "GOOGL", "score": 0.015},
        {"date": trade_date, "instrument": "AVGO", "score": 0.014},
        {"date": trade_date, "instrument": "TSLA", "score": 0.013},
        {"date": trade_date, "instrument": "AMD", "score": 0.012},
        {"date": trade_date, "instrument": "NFLX", "score": 0.011},
        {"date": trade_date, "instrument": "ADBE", "score": 0.010},
    ]
    df = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    df["model_version"] = "lgbm_v1"

    out_path = SIGNALS_DIR / f"signals_{trade_date}.parquet"
    df.to_parquet(out_path, index=False)
    return out_path

if __name__ == "__main__":
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    path = export_mock_signals(today)
    print(f"Signals exported to {path}")
