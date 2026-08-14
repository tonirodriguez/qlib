from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time
from typing import Any

from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)


@dataclass(frozen=True)
class DownloadConfig:
    instruments: tuple[str, ...]
    quote_asset: str
    exchange_id: str
    timeframe: str
    since_days: int
    output_dir: Path
    file_pattern: str
    portfolio_csv: Path
    date_column: str
    factor_default: float
    dividends_default: float
    splits_default: float
    change_fill_value: float


def env_value(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def env_int(name: str, default: int) -> int:
    raw = env_value(name, "")
    return int(raw) if raw else default


def env_float(name: str, default: float) -> float:
    raw = env_value(name, "")
    return float(raw) if raw else default


def env_path(name: str, default: str) -> Path:
    raw = env_value(name, default)
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def env_list(name: str, default: str) -> tuple[str, ...]:
    raw = env_value(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def get_config() -> DownloadConfig:
    return DownloadConfig(
        instruments=env_list("CRYPTO_INSTRUMENTS", "BTC,ETH,SOL,XLM,ADA"),
        quote_asset=env_value("CRYPTO_QUOTE_ASSET", "USDT"),
        exchange_id=env_value("CRYPTO_EXCHANGE_ID", "binance"),
        timeframe=env_value("CRYPTO_DOWNLOAD_TIMEFRAME", env_value("CRYPTO_FREQUENCY", "1d")),
        since_days=env_int("CRYPTO_DOWNLOAD_SINCE_DAYS", 1100),
        output_dir=env_path("CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto/ohlcv"),
        file_pattern=env_value("CRYPTO_OHLCV_FILE_PATTERN", "{instrument}.csv"),
        portfolio_csv=env_path(
            "CRYPTO_INPUT_CSV",
            "scripts/crypto/csv_data/crypto/crypto_portfolio_daily.csv",
        ),
        date_column=env_value("CRYPTO_DATE_COLUMN", "date"),
        factor_default=env_float("CRYPTO_FACTOR_DEFAULT", 1.0),
        dividends_default=env_float("CRYPTO_DIVIDENDS_DEFAULT", 0.0),
        splits_default=env_float("CRYPTO_SPLITS_DEFAULT", 0.0),
        change_fill_value=env_float("CRYPTO_CHANGE_FILL_VALUE", 0.0),
    )


def make_exchange(exchange_id: str) -> Any:
    import ccxt

    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def trading_pair(instrument: str, quote_asset: str) -> str:
    return f"{instrument.upper()}/{quote_asset.upper()}"


def output_path(config: DownloadConfig, instrument: str) -> Path:
    filename = config.file_pattern.format(
        instrument=instrument,
        instrument_lower=instrument.lower(),
        instrument_upper=instrument.upper(),
        qlib_instrument=instrument.lower(),
    )
    return config.output_dir / filename


def download_historical_data(
    exchange: Any,
    symbol: str,
    timeframe: str,
    since_days: int,
) -> pd.DataFrame:
    since_timestamp = exchange.milliseconds() - since_days * 24 * 60 * 60 * 1000
    all_ohlcv: list[list[float]] = []
    current_since = since_timestamp

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        last_timestamp = ohlcv[-1][0]
        if current_since == last_timestamp:
            break
        current_since = last_timestamp + 1

        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.normalize()
    df = df.drop(columns=["timestamp"])
    df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.sort_values("date")
    return df


def enrich_for_qlib(df: pd.DataFrame, config: DownloadConfig) -> pd.DataFrame:
    if df.empty:
        return df

    enriched = df.copy()
    enriched["adjclose"] = enriched["close"]
    enriched["change"] = enriched["close"].pct_change().fillna(config.change_fill_value)
    enriched["dividends"] = config.dividends_default
    enriched["factor"] = config.factor_default
    enriched["splits"] = config.splits_default

    columns = [
        config.date_column,
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjclose",
        "change",
        "dividends",
        "factor",
        "splits",
    ]
    if config.date_column != "date":
        enriched = enriched.rename(columns={"date": config.date_column})
    return enriched[columns]


def download_all(config: DownloadConfig) -> dict[str, pd.DataFrame]:
    exchange = make_exchange(config.exchange_id)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.portfolio_csv.parent.mkdir(parents=True, exist_ok=True)

    downloaded: dict[str, pd.DataFrame] = {}
    print(f"Downloading crypto data from {config.exchange_id} into {config.output_dir}")

    for instrument in tqdm(config.instruments, desc="Downloading cryptocurrencies"):
        symbol = trading_pair(instrument, config.quote_asset)
        df = download_historical_data(exchange, symbol, config.timeframe, config.since_days)
        enriched = enrich_for_qlib(df, config)
        if enriched.empty:
            print(f"  warning: no data returned for {symbol}")
            continue

        enriched.to_csv(output_path(config, instrument), index=False)
        downloaded[instrument] = enriched

    if not downloaded:
        raise RuntimeError("No crypto data was downloaded")

    close_series = {}
    date_column = config.date_column
    for instrument, frame in downloaded.items():
        close_series[instrument] = frame.set_index(date_column)["close"]
    portfolio = pd.DataFrame(close_series).dropna()
    portfolio.to_csv(config.portfolio_csv, index_label=date_column)

    return downloaded


def main() -> None:
    config = get_config()
    downloaded = download_all(config)
    rows = {instrument: len(frame) for instrument, frame in downloaded.items()}

    print("Crypto download completed")
    print(f"  output_dir: {config.output_dir}")
    print(f"  file_pattern: {config.file_pattern}")
    print(f"  portfolio_csv: {config.portfolio_csv}")
    print(f"  instruments: {', '.join(downloaded)}")
    print(f"  rows: {rows}")


if __name__ == "__main__":
    main()
