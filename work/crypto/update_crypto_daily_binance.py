"""
update_crypto_daily_binance.py - Actualizacion DIARIA incremental de OHLCV des de Binance.

Complementa download_crypto_cryptocompare.py:
  - CryptoCompare (una vez, manual)  -> historico COMPLETO desde genesis.
  - Binance (diario/cron)            -> actualiza SOLO lo nuevo desde la ultima
                                        fecha ya descargada hasta hoy.

Fuente: Binance public API (gratis, sin key)
  GET /api/v3/klines?symbol={SYM}USDT&interval=1d&limit=1000&startTime=...
  Formato por vela (indices):
    [0] openTime, [1] open, [2] high, [3] low, [4] close,
    [5] volume, ..., [10] ignore

Incremental:
  - Lee el CSV existente de la coin (generado por CryptoCompare o Binance).
  - Busca la ultima fecha (date) del CSV.
  - Descarga de Binance desde el dia siguiente a esa fecha hasta hoy.
  - Concatena y reescribe el CSV + manifest.json.

Config:
  CRYPTO_OHLCV_DIR       (default: scripts/crypto/csv_data/crypto_cryptocompare/ohlcv)
                         -> usa el MISMO dir que el script de genesis para mantener
                            un unico source de verdad por coin.
  CRYPTO_INSTRUMENTS     (default: BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC)
  CRYPTO_DATE_COLUMN     (default: date)

Uso: <python> work/crypto/update_crypto_daily_binance.py
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, **_kwargs):
        return iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INSTRUMENTS = ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC")

# CryptoCompare (genesis) usa simbolo plano; Binance usa par BASEUSDT
def binance_pair(symbol: str) -> str:
    return f"{symbol}USDT"


@dataclass(frozen=True)
class UpdateConfig:
    instruments: tuple[str, ...]
    output_dir: Path
    date_column: str
    max_retries: int
    delay_between_calls: float


def env_path(name: str, default: str) -> Path:
    raw = os.getenv(name, default).strip()
    path = Path(raw).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def env_list(name: str, default: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in os.getenv(name, default).split(",") if x.strip())


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default


def get_config() -> UpdateConfig:
    return UpdateConfig(
        instruments=env_list("CRYPTO_INSTRUMENTS", ",".join(INSTRUMENTS)),
        output_dir=env_path(
            "CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto_cryptocompare/ohlcv"
        ),
        date_column=os.getenv("CRYPTO_DATE_COLUMN", "date").strip(),
        max_retries=env_int("BINANCE_MAX_RETRIES", 5),
        delay_between_calls=env_float("BINANCE_DELAY", 0.55),
    )


def _fetch_klines(pair: str, start_ms: int, limit: int = 1000) -> list[list]:
    """1 una paginacion de klines Binance con reintentos."""
    import urllib.request
    import urllib.error
    import json as _json

    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={pair}&interval=1d&limit={limit}&startTime={start_ms}"
    )
    last_err: Exception | None = None
    for attempt in range(get_config().max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return _json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in (418, 429):
                # IP ban temporal / rate limit
                time.sleep(10 * (attempt + 1))
                continue
            time.sleep(2 ** (attempt + 1))
        except (urllib.error.URLError, _json.JSONDecodeError) as exc:
            last_err = exc
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Fallo {pair}: {last_err}")


def klines_to_frame(klines: list[list]) -> pd.DataFrame:
    """Convierte klines Binance al formato OHLCV del repo (misma convention que CC)."""
    recs = []
    for k in klines:
        # [0]openTime, [1]open, [2]high, [3]low, [4]close, [5]volume
        recs.append({
            "date": pd.to_datetime(k[0], unit="ms", utc=True).normalize(),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    df = pd.DataFrame(recs)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df = df[df["date"] < pd.Timestamp.now(tz="UTC").normalize()]
    return df.reset_index(drop=True)


def enrich_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Anade columnas extra (estandar convert_crypto_qlib.py) al frame OHLCV."""
    if df.empty:
        return df
    df = df.copy()
    df["adjclose"] = df["close"]
    df["change"] = df["close"].pct_change().fillna(0.0)
    df["dividends"] = 0.0
    df["factor"] = 1.0
    df["splits"] = 0.0
    cols = ["date", "open", "high", "low", "close", "volume",
            "adjclose", "change", "dividends", "factor", "splits"]
    return df[cols]


def update_coin(config: UpdateConfig, symbol: str) -> tuple[str, int, int, int]:
    """Actualiza 1 coin. Devuelve (simbolo, filas_total, filas_nuevas, filas_previas)."""
    csv_path = config.output_dir / f"{symbol.lower()}.csv"
    pair = binance_pair(symbol.upper())
    now = pd.Timestamp.now(tz="UTC").normalize()

    if csv_path.exists():
        prev = pd.read_csv(csv_path, parse_dates=[config.date_column])
        prev = prev.sort_values(config.date_column).drop_duplicates(
            subset=[config.date_column], keep="last")
        last_date = prev[config.date_column].max()
        # descargar desde el dia siguiente al ultimo conocido
        start_ms = int((last_date + pd.Timedelta(days=1)).timestamp() * 1000)
        n_prev = len(prev)
    else:
        # no existe CSV -> traer todo disponible (Binance ~ desde 2017)
        start_ms = 0
        prev = pd.DataFrame()
        n_prev = 0

    all_new: list[pd.DataFrame] = []
    cursor = start_ms
    while True:
        klines = _fetch_klines(pair, cursor)
        if not klines:
            break
        part = klines_to_frame(klines)
        part = part[part["date"] >= pd.to_datetime(cursor, unit="ms", utc=True).normalize()]
        if part.empty:
            break
        all_new.append(part)
        new_end_ms = int(part["date"].max().timestamp() * 1000)
        if new_end_ms <= cursor:
            break
        cursor = new_end_ms + 1  # siguiente dia despues de lo ya traido
        time.sleep(config.delay_between_calls)

    if all_new:
        new_frame = pd.concat(all_new).sort_values(config.date_column).drop_duplicates(
            subset=[config.date_column], keep="last")
        new_frame = new_frame[new_frame[config.date_column] < now]
        combined = pd.concat([prev, new_frame]) if n_prev else new_frame
    else:
        combined = prev

    combined = combined.sort_values(config.date_column).drop_duplicates(
        subset=[config.date_column], keep="last")
    combined = combined[combined[config.date_column] < now]
    combined = enrich_ohlcv(combined)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    combined.sort_values(config.date_column).to_csv(tmp, index=False)
    tmp.replace(csv_path)

    n_new = len(combined) - n_prev
    return (symbol, len(combined), n_new, n_prev)


def write_manifest(config: UpdateConfig, downloaded: dict[str, pd.DataFrame]) -> None:
    manifest = {"source": "binance-daily-incremental", "endpoint": "/api/v3/klines",
                "instruments": {}}
    for instr, frame in downloaded.items():
        path = config.output_dir / f"{instr.lower()}.csv"
        manifest["instruments"][instr] = {
            "rows": len(frame),
            "first_date": str(frame[config.date_column].min()),
            "last_date": str(frame[config.date_column].max()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "file": path.name,
        }
    mp = config.output_dir / "manifest.json"
    tmp = mp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(mp)


def main() -> None:
    config = get_config()
    print(f"Actualizacion incremental diaria (Binance) -> {config.output_dir}")
    downloaded: dict[str, pd.DataFrame] = {}
    for sym in tqdm(config.instruments, desc="Binance daily"):
        try:
            symbol, total, n_new, n_prev = update_coin(config, sym)
            print(f"  {symbol}: +{n_new} nuevas | total {total} (antes {n_prev})")
            downloaded[symbol] = pd.read_csv(
                config.output_dir / f"{symbol.lower()}.csv",
                parse_dates=[config.date_column])
            time.sleep(config.delay_between_calls)
        except RuntimeError as e:
            print(f"  ✗ {sym}: {e}")
    if downloaded:
        write_manifest(config, downloaded)
    print("\nListo.")


if __name__ == "__main__":
    main()