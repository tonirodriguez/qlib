"""
download_crypto_coingecko.py - Descarga historico COMPLETO de criptomonedas desde CoinGecko

CoinGecko tiene datos desde el genesis de cada moneda, a diferencia de Binance
que solo tiene datos desde el listing del par.

Fuente: CoinGecko API v3 (publica, sin API key necesaria, limite ~10-30 llamadas/min)
Endpoint: /coins/{id}/ohlc (devuelve [timestamp_ms, open, high, low, close])

Mapping de simbolos a CoinGecko IDs:
  BTC -> bitcoin, ETH -> ethereum, SOL -> solana, XLM -> stellar,
  ADA -> cardano, XRP -> ripple, DOGE -> dogecoin, LINK -> chainlink, LTC -> litecoin

Uso: conda run -n qlib python work/crypto/download_crypto_coingecko.py

Configuracion via variables de entorno (mismas que download_crypto.py):
  CRYPTO_INSTRUMENTS, CRYPTO_OHLCV_DIR, CRYPTO_INPUT_CSV
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
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
except ImportError:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)

# Mapping de simbolo a CoinGecko ID
SYMBOL_TO_COINGECKO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XLM": "stellar",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "BNB": "binancecoin",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "ATOM": "cosmos",
    "UNI": "uniswap",
    "TRX": "tron",
    "ETC": "ethereum-classic",
    "XMR": "monero",
    "VET": "vechain",
    "FIL": "filecoin",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "SUI": "sui",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "NEAR": "near",
    "ALGO": "algorand",
    "FTM": "fantom",
    "EGLD": "elrond-erd-2",
    "AAVE": "aave",
    "GRT": "the-graph",
}

MAX_DAYS_PER_CALL = 365


@dataclass(frozen=True)
class CoinGeckoConfig:
    instruments: tuple[str, ...]
    output_dir: Path
    portfolio_csv: Path
    date_column: str
    max_retries: int
    delay_between_calls: float
    days_per_call: int
    start_date: str | None
    factor_default: float
    dividends_default: float
    splits_default: float
    change_fill_value: float


def env_value(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


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
    return tuple(item.strip() for item in env_value(name, default).split(",") if item.strip())


def env_int(name: str, default: int) -> int:
    raw = env_value(name, "")
    return int(raw) if raw else default


def get_config() -> CoinGeckoConfig:
    return CoinGeckoConfig(
        instruments=env_list("CRYPTO_INSTRUMENTS", "BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"),
        output_dir=env_path("CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto_coingecko/ohlcv"),
        portfolio_csv=env_path(
            "CRYPTO_INPUT_CSV",
            "scripts/crypto/csv_data/crypto_coingecko/crypto_portfolio_daily.csv",
        ),
        date_column=env_value("CRYPTO_DATE_COLUMN", "date"),
        max_retries=env_int("CRYPTO_DOWNLOAD_MAX_RETRIES", 5),
        delay_between_calls=env_float("CRYPTO_DOWNLOAD_DELAY", 2.5),
        days_per_call=MAX_DAYS_PER_CALL,
        start_date=env_value("CRYPTO_START_DATE", "2010-01-01"),
        factor_default=env_float("CRYPTO_FACTOR_DEFAULT", 1.0),
        dividends_default=env_float("CRYPTO_DIVIDENDS_DEFAULT", 0.0),
        splits_default=env_float("CRYPTO_SPLITS_DEFAULT", 0.0),
        change_fill_value=env_float("CRYPTO_CHANGE_FILL_VALUE", 0.0),
    )


def coingecko_id(symbol: str) -> str:
    upper = symbol.upper()
    if upper in SYMBOL_TO_COINGECKO_ID:
        return SYMBOL_TO_COINGECKO_ID[upper]
    return symbol.lower()


def output_path(config: CoinGeckoConfig, instrument: str) -> Path:
    return config.output_dir / f"{instrument.lower()}.csv"


def fetch_ohlc_range(cg_id: str, from_ts: int, to_ts: int, max_retries: int) -> list[list[float]]:
    import urllib.request
    import urllib.error

    url = (
        f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc"
        f"?vs_currency=usd&days={MAX_DAYS_PER_CALL}"
    )

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if not isinstance(data, list):
                raise ValueError(f"Unexpected response: {data}")
            result = [row for row in data if from_ts <= row[0] <= to_ts]
            return result
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            if attempt == max_retries:
                break
            time.sleep(min(2 ** (attempt + 1), 30))
    raise RuntimeError(f"Failed to fetch {cg_id} OHLC after {max_retries + 1} attempts") from last_error


def download_all(config: CoinGeckoConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.portfolio_csv.parent.mkdir(parents=True, exist_ok=True)

    downloaded: dict[str, pd.DataFrame] = {}
    now_utc = pd.Timestamp.now(tz="UTC").normalize()
    today_ms = int(now_utc.timestamp() * 1000)

    if config.start_date:
        start_dt = pd.Timestamp(config.start_date, tz="UTC").normalize()
    else:
        start_dt = pd.Timestamp("2010-01-01", tz="UTC")
    start_ms = int(start_dt.timestamp() * 1000)

    print(f"Downloading crypto data from CoinGecko into {config.output_dir}")
    print(f"  Periodo solicitado: {start_dt.date()} -> {now_utc.date()}")
    print(f"  Delay entre llamadas: {config.delay_between_calls}s")
    print()

    for instrument in tqdm(config.instruments, desc="Downloading from CoinGecko"):
        cg_id = coingecko_id(instrument)
        destination = output_path(config, instrument)
        print(f"\n  {instrument} (CoinGecko ID: {cg_id})")

        all_ohlcv: list[list[float]] = []
        current_end = today_ms
        max_iterations = 100
        iteration = 0

        while current_end > start_ms and iteration < max_iterations:
            try:
                ohlcv = fetch_ohlc_range(cg_id, start_ms, current_end, config.max_retries)
            except RuntimeError as e:
                print(f"    Error: {e}")
                break

            if not ohlcv:
                break

            first_ts = ohlcv[0][0]
            last_ts = ohlcv[-1][0]

            existing_timestamps = {row[0] for row in all_ohlcv}
            new_rows = [row for row in ohlcv if row[0] not in existing_timestamps]
            all_ohlcv.extend(new_rows)

            n_new = len(new_rows)
            first_date = pd.Timestamp(first_ts, unit="ms", tz="UTC").date()
            last_date = pd.Timestamp(last_ts, unit="ms", tz="UTC").date()
            print(f"    Bloque: {first_date} -> {last_date}  ({n_new} nuevas)")

            if first_ts <= start_ms:
                break

            current_end = first_ts - 1
            time.sleep(config.delay_between_calls)
            iteration += 1

        if not all_ohlcv:
            print(f"    No se obtuvieron datos para {instrument}")
            continue

        all_ohlcv.sort(key=lambda row: row[0])

        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.normalize()
        df = df.drop(columns=["timestamp"])
        df = df.drop_duplicates(subset=["date"], keep="last")
        df = df.sort_values("date")
        df = df[df["date"] < now_utc]
        df["volume"] = 0.0

        df["adjclose"] = df["close"]
        df["change"] = df["close"].pct_change().fillna(config.change_fill_value)
        df["dividends"] = config.dividends_default
        df["factor"] = config.factor_default
        df["splits"] = config.splits_default

        columns_out = [
            config.date_column, "open", "high", "low", "close", "volume",
            "adjclose", "change", "dividends", "factor", "splits",
        ]
        df_out = df[columns_out]

        if df_out.empty:
            print(f"    warning: sin datos tras procesar para {instrument}")
            continue

        print(f"    Total: {len(df_out)} filas, {df_out['date'].min().date()} -> {df_out['date'].max().date()}")

        temporary = destination.with_suffix(destination.suffix + ".tmp")
        df_out.to_csv(temporary, index=False)
        temporary.replace(destination)
        downloaded[instrument] = df_out

    if not downloaded:
        raise RuntimeError("No se descargo ninguna cripto desde CoinGecko")

    close_series = {}
    for instrument, frame in downloaded.items():
        close_series[instrument] = frame.set_index(config.date_column)["close"]
    portfolio = pd.DataFrame(close_series).dropna(how="all").sort_index()
    portfolio.index.name = config.date_column
    portfolio_tmp = config.portfolio_csv.with_suffix(config.portfolio_csv.suffix + ".tmp")
    portfolio.to_csv(portfolio_tmp, index_label=config.date_column)
    portfolio_tmp.replace(config.portfolio_csv)

    manifest = {
        "source": "coingecko",
        "endpoint": "/coins/{id}/ohlc",
        "days_per_call": config.days_per_call,
        "instruments": {},
    }
    for instrument, frame in downloaded.items():
        path = output_path(config, instrument)
        manifest["instruments"][instrument] = {
            "rows": len(frame),
            "first_date": frame[config.date_column].min(),
            "last_date": frame[config.date_column].max(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "file": path.name,
        }
    manifest_path = config.output_dir / "manifest.json"
    manifest_tmp = manifest_path.with_suffix(".json.tmp")
    manifest_tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_tmp.replace(manifest_path)

    print(f"\nDescarga completada desde CoinGecko")
    print(f"  output_dir: {config.output_dir}")
    print(f"  portfolio: {config.portfolio_csv}")
    for instrument, frame in downloaded.items():
        print(f"  {instrument}: {len(frame)} filas, {frame[config.date_column].min().date()} -> {frame[config.date_column].max().date()}")

    return downloaded


def main() -> None:
    config = get_config()
    download_all(config)


if __name__ == "__main__":
    main()