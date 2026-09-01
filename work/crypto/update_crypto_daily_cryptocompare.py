"""
update_crypto_daily_cryptocompare.py - Actualizacion DIARIA incremental de OHLCV
desde CryptoCompare (USD literal). Alternativa al update de Binance (USDT).

Complementa download_crypto_cryptocompare.py:
  - CryptoCompare (una vez, manual)  -> historico COMPLETO desde genesis (USD).
  - Este script (diario/cron)        -> actualiza SOLO lo nuevo desde la ultima
                                        fecha ya descargada hasta hoy, en USD.

Por que usarlo:
  - CryptoCompare devuelve tsym=USD literal (no stablecoin). Es la fuente de
    moneda ESTABLE en dolares 'puros' para todo el dataset.
  - Alternativa: update_crypto_daily_binance.py (par *USDT, stablecoin 1:1 USD).

⚠️ RATE LIMIT (plan gratuito CryptoCompare): 1 llama/seg, 100/dia, 100/mes.
   Con 9 coins (1 llama c/u al dia) se consumen ~9 llamadas/dia ->
   ~11 actualizaciones completas al mes antes de llegar al tope mensual (100).
   Disenado para correr con moderacion (o subir a un plan con mas cuota).
   El script respeta el rate limit y reintenta/espera.

Fuente: CryptoCompare API v2 /data/v2/histoday?fsym={S}&tsym=USD&limit=N
Config:
  CRYPTOCOMPARE_API_KEY   (obligatoria; en .env o env vars)
  CRYPTO_OHLCV_DIR        (default: scripts/crypto/csv_data/crypto_cryptocompare/ohlcv)
  CRYPTO_INSTRUMENTS      (default: BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC)

Uso: <python> work/crypto/update_crypto_daily_cryptocompare.py
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

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)

INSTRUMENTS = ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC")

# Moneda de cotizacion: USD literal en CryptoCompare (tsym=USD).
QUOTE_CURRENCY = "USD"

# Numero de dias a traer por llamada incremental (margen por si hubo huecos).
INCREMENTAL_DAYS = 7


@dataclass(frozen=True)
class UpdateCCConfig:
    api_key: str
    instruments: tuple[str, ...]
    output_dir: Path
    date_column: str
    max_retries: int
    delay_between_calls: float
    incremental_days: int


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


def get_config() -> UpdateCCConfig:
    api_key = os.getenv("CRYPTOCOMPARE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "ERROR: falta CRYPTOCOMPARE_API_KEY en .env o env vars. "
            "Guardala en /opt/data/qlib/.env (no se commitea)."
        )
    return UpdateCCConfig(
        api_key=api_key,
        instruments=env_list("CRYPTO_INSTRUMENTS", ",".join(INSTRUMENTS)),
        output_dir=env_path(
            "CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto_cryptocompare/ohlcv"
        ),
        date_column=os.getenv("CRYPTO_DATE_COLUMN", "date").strip(),
        max_retries=env_int("CRYPTOCOMPARE_MAX_RETRIES", 5),
        delay_between_calls=env_float("CRYPTOCOMPARE_DELAY", 1.2),
        incremental_days=env_int("CRYPTOCOMPARE_INCREMENTAL_DAYS", INCREMENTAL_DAYS),
    )


def _fetch_recent(config: UpdateCCConfig, fsym: str) -> list[dict]:
    """Trae los ultimos `incremental_days` dias desde CryptoCompare, en USD."""
    import urllib.request
    import urllib.error
    import json as _json

    url = (
        f"https://min-api.cryptocompare.com/data/v2/histoday"
        f"?fsym={fsym}&tsym={QUOTE_CURRENCY}&limit={config.incremental_days}"
        f"&api_key={config.api_key}"
    )
    last_err: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
            if data.get("Response") != "Success":
                msg = str(data.get("Message", ""))
                if "rate limit" in msg.lower():
                    wait = 3 ** (attempt + 1)
                    print(f"    ⏳ rate-limit: esperando {wait}s...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"API error: {msg}")
            return data["Data"]["Data"]
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429:
                wait = 3 ** (attempt + 1)
                time.sleep(wait)
                continue
            time.sleep(2 ** (attempt + 1))
        except (urllib.error.URLError, _json.JSONDecodeError, RuntimeError) as exc:
            last_err = exc
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Fallo {fsym}: {last_err}")


def build_ohlcv_frame(rows: list[dict]) -> pd.DataFrame:
    """Convierte filas de CryptoCompare al formato OHLCV del repo (Qlib)."""
    df = pd.DataFrame({
        "date": pd.Series(pd.to_datetime([r["time"] for r in rows], unit="s", utc=True)).dt.normalize(),
        "open": [float(r["open"]) for r in rows],
        "high": [float(r["high"]) for r in rows],
        "low": [float(r["low"]) for r in rows],
        "close": [float(r["close"]) for r in rows],
        "volume": [float(r["volumefrom"]) for r in rows],
    })
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


# Umbrales minimos de precio de cierre (USD) por moneda (mismo criterio que el de Binance).
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


def update_coin(config: UpdateCCConfig, symbol: str) -> tuple[str, int, int, int]:
    """Actualiza 1 coin. Devuelve (simbolo, filas_total, filas_nuevas, filas_previas)."""
    csv_path = config.output_dir / f"{symbol.lower()}.csv"
    now = pd.Timestamp.now(tz="UTC").normalize()

    if csv_path.exists():
        prev = pd.read_csv(csv_path, parse_dates=[config.date_column])
        prev = prev.sort_values(config.date_column).drop_duplicates(
            subset=[config.date_column], keep="last")
        prev = prev[prev[config.date_column] < now]
        n_prev = len(prev)
    else:
        prev = pd.DataFrame()
        n_prev = 0

    # Guarda de moneda sobre el historico ya descargado
    _assert_usd_plausible(symbol, prev)

    rows = _fetch_recent(config, symbol.upper())
    new_frame = build_ohlcv_frame(rows)
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


def write_manifest(config: UpdateCCConfig, downloaded: dict[str, pd.DataFrame]) -> None:
    manifest = {"source": "cryptocompare-daily-incremental",
                "endpoint": "/data/v2/histoday", "instruments": {}}
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
    print(f"Actualizacion incremental diaria (CryptoCompare, USD) -> {config.output_dir}")
    downloaded: dict[str, pd.DataFrame] = {}
    for sym in tqdm(config.instruments, desc="CryptoCompare daily"):
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