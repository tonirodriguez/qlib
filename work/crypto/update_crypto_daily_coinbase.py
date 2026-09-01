"""
update_crypto_daily_coinbase.py - Actualizacion DIARIA incremental de OHLCV
desde Coinbase Exchange en pares *-USD reales (USD literal).

Complementa download_crypto_cryptocompare.py:
  - CryptoCompare (una vez, manual)  -> historico COMPLETO desde genesis (USD).
  - Este script (diario/cron)        -> actualiza SOLO lo nuevo desde la ultima
                                        fecha ya descargada hasta hoy, en USD.

Por que este script:
  - Coinbase expone pares *-USD REALES (BTC-USD, ETH-USD, ...) en USD literal.
  - API publica gratuita SIN API key y SIN la limitacion de CryptoCompare
    (100 llamadas/mes). Ideal para la operativa diaria en dolares sin topes.
  - Formato consistente y simple: [time, low, high, open, close, volume].

Alternativas:
  - update_crypto_daily_cryptocompare.py -> USD literal pero topes 100/mes.
  - update_crypto_daily_binance.py       -> USDT (1:1 USD) sin limite.

Fuente: Coinbase Exchange REST
  GET /products/{SYM}-USD/candles?granularity=86400
  Devuelve hasta ~300 velas por peticion (objetos [time, low, high, open, close, volume]).
  Para incremental diario usamos start=fecha-siguiente-a-la-ultima y end=hoy lo cual
  devuelve los dias pendientes en una sola peticion.

Rate limit Coinbase exchange (publical): ~10 rps / 100000 en 10min por IP, mas que
suficiente para 9 coins/dia.

Config:
  CRYPTO_OHLCV_DIR        (default: scripts/crypto/csv_data/crypto_cryptocompare/ohlcv)
  CRYPTO_INSTRUMENTS      (default: BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC)
  CRYPTO_DATE_COLUMN      (default: date)

Uso: <python> work/crypto/update_crypto_daily_coinbase.py
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

# Moneda de cotizacion: USD literal. Coinbase usa pares {SYM}-USD reales.
QUOTE_CURRENCY = "USD"


def coinbase_product(symbol: str) -> str:
    """Coinbase usa pares {SYMBOL}-USD (BTC-USD, ETH-USD...)."""
    return f"{symbol.upper()}-{QUOTE_CURRENCY}"


@dataclass(frozen=True)
class UpdateCBConfig:
    instruments: tuple[str, ...]
    output_dir: Path
    date_column: str
    max_retries: int
    delay_between_calls: float
    http_timeout: int


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


def get_config() -> UpdateCBConfig:
    return UpdateCBConfig(
        instruments=env_list("CRYPTO_INSTRUMENTS", ",".join(INSTRUMENTS)),
        output_dir=env_path(
            "CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto_cryptocompare/ohlcv"
        ),
        date_column=os.getenv("CRYPTO_DATE_COLUMN", "date").strip(),
        max_retries=env_int("COINBASE_MAX_RETRIES", 5),
        delay_between_calls=env_float("COINBASE_DELAY", 0.4),
        http_timeout=env_int("COINBASE_TIMEOUT", 30),
    )


def _fetch_candles(config: UpdateCBConfig, product: str, start_iso: str, end_iso: str) -> list[list]:
    """Trae velas diarias USD de Coinbase en [start, end] (una peticion si cabe)."""
    import urllib.request
    import urllib.error
    import json as _json

    url = (
        f"https://api.exchange.coinbase.com/products/{product}/candles"
        f"?granularity=86400&start={start_iso}&end={end_iso}"
    )
    last_err: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=config.http_timeout) as resp:
                data = _json.loads(resp.read().decode())
            if isinstance(data, dict) and "message" in data:
                # puede ser rate-limit {"message": ...}
                if "rate" in str(data["message"]).lower() or "throttl" in str(data["message"]).lower():
                    wait = 3 ** (attempt + 1)
                    print(f"    ⏳ {product}: rate-limit, esperando {wait}s...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"Coinbase error {product}: {data['message']}")
            return data  # list of [time, low, high, open, close, volume]
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in (429, 504, 502):
                wait = 3 ** (attempt + 1)
                time.sleep(wait)
                continue
            if exc.code == 404:
                raise RuntimeError(f"{product}: par no existe (404)")
            time.sleep(2 ** (attempt + 1))
        except (urllib.error.URLError, _json.JSONDecodeError, RuntimeError) as exc:
            last_err = exc
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Fallo {product}: {last_err}")


def candles_to_frame(candles: list[list]) -> pd.DataFrame:
    """Convierte velas Coinbase [time, low, high, open, close, volume] a OHLCV."""
    recs = []
    for c in candles:
        # c = [time, low, high, open, close, volume]
        recs.append({
            "date": pd.Series(pd.to_datetime([c[0]], unit="s", utc=True)).iloc[0].normalize(),
            "open": float(c[3]),
            "high": float(c[2]),
            "low": float(c[1]),
            "close": float(c[4]),
            "volume": float(c[5]),
        })
    df = pd.DataFrame(recs)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df = df[df["date"] < pd.Timestamp.now(tz="UTC").normalize()]
    return df.reset_index(drop=True)


def enrich_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
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


# Umbrales minimos de precio de cierre (USD) por moneda (mismo criterio).
USD_FLOOR_BY_SYMBOL: dict[str, float] = {
    "BTC": 1000.0, "ETH": 100.0, "SOL": 1.0, "XLM": 0.005, "ADA": 0.01,
    "XRP": 0.01, "DOGE": 0.0005, "LINK": 0.5, "LTC": 1.0,
}


def _assert_usd_plausible(symbol: str, df: pd.DataFrame) -> None:
    """Aborta si el ultimo precio de cierre no es coherente con una cotizacion en USD."""
    if df is None or df.empty:
        return
    floor = USD_FLOOR_BY_SYMBOL.get(symbol.upper())
    if floor is None:
        return
    last_close = float(df[df["close"].notna()]["close"].iloc[-1])
    if last_close < floor:
        raise RuntimeError(
            f"{symbol}: ultimo close={last_close:.6f} < floor USD {floor} "
            f"-> los datos NO parecen estar en dolares. Abortada actualizacion."
        )


def update_coin(config: UpdateCBConfig, symbol: str) -> tuple[str, int, int, int]:
    """Actualiza 1 coin. Devuelve (simbolo, filas_total, filas_nuevas, filas_previas)."""
    csv_path = config.output_dir / f"{symbol.lower()}.csv"
    product = coinbase_product(symbol.upper())
    now = pd.Timestamp.now(tz="UTC").normalize()
    today_iso = now.strftime("%Y-%m-%d")
    yesterday_iso = (now - pd.Timedelta(days=2)).strftime("%Y-%m-%d")  # margen

    if csv_path.exists():
        prev = pd.read_csv(csv_path, parse_dates=[config.date_column])
        prev = prev.sort_values(config.date_column).drop_duplicates(
            subset=[config.date_column], keep="last")
        prev = prev[prev[config.date_column] < now]
        n_prev = len(prev)
        if not prev.empty:
            start_iso = (prev[config.date_column].max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            start_iso = yesterday_iso
    else:
        prev = pd.DataFrame()
        n_prev = 0
        start_iso = yesterday_iso  # sin CSV: trae un rescaneo reciente (backfill se hace con CryptoCompare)

    _assert_usd_plausible(symbol, prev)

    candles = _fetch_candles(config, product, start_iso, today_iso)
    new_frame = candles_to_frame(candles)
    _assert_usd_plausible(symbol, new_frame)

    if prev.empty:
        combined = new_frame
    else:
        combined = pd.concat([prev, new_frame]).sort_values(config.date_column).drop_duplicates(
            subset=[config.date_column], keep="last")

    combined = combined[combined[config.date_column] < now]
    combined = enrich_ohlcv(combined)
    combined = combined.sort_values(config.date_column)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    combined.to_csv(tmp, index=False)
    tmp.replace(csv_path)

    n_new = len(combined) - n_prev
    return (symbol, len(combined), n_new, n_prev)


def write_manifest(config: UpdateCBConfig, downloaded: dict[str, pd.DataFrame]) -> None:
    manifest = {"source": "coinbase-daily-incremental",
                "endpoint": "/products/{SYM}-USD/candles", "instruments": {}}
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
    print(f"Actualizacion incremental diaria (Coinbase, USD real) -> {config.output_dir}")
    downloaded: dict[str, pd.DataFrame] = {}
    for sym in tqdm(config.instruments, desc="Coinbase daily"):
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