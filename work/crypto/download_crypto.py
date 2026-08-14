from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import re
import time
from typing import Any

import pandas as pd
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable: Any, **_kwargs: Any) -> Any:
        return iterable

try:
    from dotenv import load_dotenv
except ImportError:  # Environment variables still work without .env support.
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


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
    max_pages: int
    max_retries: int
    incremental: bool
    overlap_days: int


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
        instruments=env_list("CRYPTO_INSTRUMENTS", "BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"),
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
        max_pages=env_int("CRYPTO_DOWNLOAD_MAX_PAGES", 10_000),
        max_retries=env_int("CRYPTO_DOWNLOAD_MAX_RETRIES", 4),
        incremental=env_value("CRYPTO_DOWNLOAD_INCREMENTAL", "true").lower()
        in {"1", "true", "yes", "on"},
        overlap_days=env_int("CRYPTO_DOWNLOAD_OVERLAP_DAYS", 7),
    )


def make_exchange(exchange_id: str) -> Any:
    import ccxt

    if not re.fullmatch(r"[a-z0-9_]+", exchange_id):
        raise ValueError(f"Invalid exchange id: {exchange_id!r}")
    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None or exchange_id not in ccxt.exchanges:
        raise ValueError(f"Unsupported ccxt exchange: {exchange_id!r}")
    return exchange_class({"enableRateLimit": True, "timeout": 30_000})


def trading_pair(instrument: str, quote_asset: str) -> str:
    return f"{instrument.upper()}/{quote_asset.upper()}"


def output_path(config: DownloadConfig, instrument: str) -> Path:
    filename = config.file_pattern.format(
        instrument=instrument,
        instrument_lower=instrument.lower(),
        instrument_upper=instrument.upper(),
        qlib_instrument=instrument.lower(),
    )
    path = Path(filename)
    if path.is_absolute() or len(path.parts) != 1 or path.name in {"", ".", ".."}:
        raise ValueError("CRYPTO_OHLCV_FILE_PATTERN must produce a plain filename")
    return config.output_dir / path


def fetch_with_retries(
    exchange: Any, symbol: str, timeframe: str, since: int, max_retries: int
) -> list[list[float]]:
    error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        except Exception as exc:  # ccxt exposes exchange-specific transient errors
            error = exc
            if attempt == max_retries:
                break
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"Failed to fetch {symbol} after {max_retries + 1} attempts") from error


def download_historical_data(
    exchange: Any,
    symbol: str,
    timeframe: str,
    since_days: int,
    max_pages: int = 10_000,
    max_retries: int = 4,
    since_timestamp: int | None = None,
) -> pd.DataFrame:
    history_start = exchange.milliseconds() - since_days * 24 * 60 * 60 * 1000
    since_timestamp = history_start if since_timestamp is None else max(history_start, since_timestamp)
    all_ohlcv: list[list[float]] = []
    current_since = since_timestamp

    for _page in range(max_pages):
        ohlcv = fetch_with_retries(exchange, symbol, timeframe, current_since, max_retries)
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        last_timestamp = ohlcv[-1][0]
        if last_timestamp < current_since:
            raise RuntimeError(f"Non-monotonic OHLCV pagination for {symbol}")
        current_since = last_timestamp + 1

        time.sleep(exchange.rateLimit / 1000)
    else:
        raise RuntimeError(f"Pagination limit ({max_pages}) reached for {symbol}")

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.normalize()
    df = df.drop(columns=["timestamp"])
    df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.sort_values("date")
    if timeframe == "1d":
        current_utc_day = pd.Timestamp.now(tz="UTC").normalize()
        df = df[df["date"] < current_utc_day]
    return df


def load_existing_data(path: Path, date_column: str) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    existing = pd.read_csv(path)
    if date_column not in existing.columns:
        raise ValueError(f"Existing file {path} is missing {date_column!r}")
    existing[date_column] = pd.to_datetime(existing[date_column], utc=True).dt.normalize()
    return existing.sort_values(date_column).drop_duplicates(date_column, keep="last")


def validate_ohlcv(frame: pd.DataFrame, instrument: str, date_column: str) -> None:
    required = {date_column, "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{instrument}: missing OHLCV columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{instrument}: no closed OHLCV candles")
    if frame[date_column].duplicated().any() or not frame[date_column].is_monotonic_increasing:
        raise ValueError(f"{instrument}: timestamps must be unique and increasing")
    numeric = frame[["open", "high", "low", "close", "volume"]]
    if numeric.isna().any().any():
        raise ValueError(f"{instrument}: OHLCV contains null values")
    if (numeric[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError(f"{instrument}: OHLC prices must be positive")
    if (numeric["volume"] < 0).any():
        raise ValueError(f"{instrument}: volume cannot be negative")
    if (numeric["high"] < numeric[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError(f"{instrument}: high is below another OHLC value")
    if (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError(f"{instrument}: low is above another OHLC value")


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
        destination = output_path(config, instrument)
        existing = load_existing_data(destination, config.date_column) if config.incremental else pd.DataFrame()
        incremental_since = None
        if not existing.empty:
            last_date = existing[config.date_column].max()
            incremental_since = int(
                (last_date - pd.Timedelta(days=config.overlap_days)).timestamp() * 1000
            )
        df = download_historical_data(
            exchange,
            symbol,
            config.timeframe,
            config.since_days,
            max_pages=config.max_pages,
            max_retries=config.max_retries,
            since_timestamp=incremental_since,
        )
        enriched = enrich_for_qlib(df, config)
        if not existing.empty:
            enriched = pd.concat([existing, enriched], ignore_index=True)
            enriched = enriched.sort_values(config.date_column).drop_duplicates(
                config.date_column, keep="last"
            )
        if config.timeframe == "1d":
            current_utc_day = pd.Timestamp.now(tz="UTC").normalize()
            enriched = enriched[enriched[config.date_column] < current_utc_day]
        if enriched.empty:
            print(f"  warning: no data returned for {symbol}")
            continue

        validate_ohlcv(enriched, instrument, config.date_column)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        enriched.to_csv(temporary, index=False)
        temporary.replace(destination)
        downloaded[instrument] = enriched

    if not downloaded:
        raise RuntimeError("No crypto data was downloaded")

    close_series = {}
    date_column = config.date_column
    for instrument, frame in downloaded.items():
        close_series[instrument] = frame.set_index(date_column)["close"]
    portfolio = pd.DataFrame(close_series).dropna()
    portfolio_tmp = config.portfolio_csv.with_suffix(config.portfolio_csv.suffix + ".tmp")
    portfolio.to_csv(portfolio_tmp, index_label=date_column)
    portfolio_tmp.replace(config.portfolio_csv)

    manifest = {
        "source": "ccxt",
        "exchange": config.exchange_id,
        "timeframe": config.timeframe,
        "quote_asset": config.quote_asset,
        "instruments": {},
    }
    for instrument, frame in downloaded.items():
        path = output_path(config, instrument)
        manifest["instruments"][instrument] = {
            "rows": len(frame),
            "first_timestamp": frame[config.date_column].min().isoformat(),
            "last_timestamp": frame[config.date_column].max().isoformat(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "file": path.name,
        }
    manifest_path = config.output_dir / "manifest.json"
    manifest_tmp = manifest_path.with_suffix(".json.tmp")
    manifest_tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_tmp.replace(manifest_path)

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
