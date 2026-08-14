from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from work.crypto.download_crypto import DownloadConfig, download_historical_data, get_config, output_path


class FakeExchange:
    rateLimit = 0

    def __init__(self, pages):
        self.pages = iter(pages)

    def milliseconds(self):
        return 100_000_000

    def fetch_ohlcv(self, *_args, **_kwargs):
        return next(self.pages)


def base_config(tmp_path: Path) -> DownloadConfig:
    return DownloadConfig(
        instruments=("BTC",), quote_asset="USDT", exchange_id="binance",
        timeframe="1d", since_days=1, output_dir=tmp_path,
        file_pattern="{instrument}.csv", portfolio_csv=tmp_path / "portfolio.csv",
        date_column="date", factor_default=1.0, dividends_default=0.0,
        splits_default=0.0, change_fill_value=0.0, max_pages=10, max_retries=0,
        incremental=True, overlap_days=7,
    )


def test_output_pattern_cannot_escape_directory(tmp_path):
    with pytest.raises(ValueError, match="plain filename"):
        output_path(replace(base_config(tmp_path), file_pattern="../{instrument}.csv"), "BTC")


def test_default_universe_contains_the_four_validated_additions(monkeypatch):
    monkeypatch.delenv("CRYPTO_INSTRUMENTS", raising=False)
    assert get_config().instruments == (
        "BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC"
    )


def test_download_is_utc_sorted_and_deduplicated():
    exchange = FakeExchange([
        [[20_000_000, 1, 2, 0, 1.4, 2], [21_000_000, 1, 2, 0, 1.5, 3]],
        [],
    ])
    frame = download_historical_data(exchange, "BTC/USDT", "1d", 1, max_retries=0)
    assert list(frame.columns) == ["open", "high", "low", "close", "volume", "date"]
    assert frame["date"].dt.tz is not None
    assert frame["date"].is_monotonic_increasing
