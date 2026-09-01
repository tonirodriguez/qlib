"""
download_crypto_cryptocompare.py - Descarga historico COMPLETO (desde genesis)
de criptomonedas usando CryptoCompare API v2 /data/v2/histoday.

CryptoCompare tiene datos desde el genesis real de cada moneda
(no desde el listing del par, como Binance).

Fuente: CryptoCompare API v2 (requiere API key gratuita).
Endpoint: /data/v2/histoday?fsym={SYMBOL}&tsym=USD&limit=2000&toTs=...
Formato por vela: open, high, low, close, volumefrom, volumeto.

- Pagina hacia atras con toTs en bloques de 2000 dias hasta alcanzar el genesis.
- Respeta el rate limit del plan gratuito: 1 llamada/seg, 100/dia, 100/mes.
  (de forma segura: espera 1.2s entre llamadas y reintenta/espera ante 429).
- Genera un CSV por coin + manifest.json (mismo formato/trazabilidad que el repo).

Config:
  CRYPTOCOMPARE_API_KEY   (obligatoria; leer de .env o env vars)
  CRYPTO_OHLCV_DIR        (default: scripts/crypto/csv_data/crypto_cryptocompare/ohlcv)
  CRYPTO_INSTRUMENTS      (default: BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC)

Uso: <python> work/crypto/download_crypto_cryptocompare.py
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable: Any, **_kwargs: Any) -> Any:
        return iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)

# Orden de entrada: simbolo que usamos internamente
INSTRUMENTS = ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC")

# CryptoCompare usa el mismo simbolo como fsym (BTC, ETH, ...)
# Coinciden siempre con nuestro universo, salvo que se amplie (BNB->BNB, etc.)
SYMBOL_TO_CC: dict[str, str] = {s: s for s in INSTRUMENTS}

# Genesis de referencia (BTC es la mas antigua, 2010-07-17 en CryptoCompare)
MIN_START_TS = 1279238400  # 2010-07-16 00:00:00 UTC (margen de seguridad)


@dataclass(frozen=True)
class CCConfig:
    api_key: str
    instruments: tuple[str, ...]
    output_dir: Path
    date_column: str
    max_retries: int
    delay_between_calls: float
    request_limit: int


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


def get_config() -> CCConfig:
    api_key = os.getenv("CRYPTOCOMPARE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "ERROR: falta CRYPTOCOMPARE_API_KEY en .env o env vars. "
            "Guardala en /opt/data/qlib/.env (no se commitea)."
        )
    return CCConfig(
        api_key=api_key,
        instruments=env_list("CRYPTO_INSTRUMENTS", ",".join(INSTRUMENTS)),
        output_dir=env_path(
            "CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto_cryptocompare/ohlcv"
        ),
        date_column=os.getenv("CRYPTO_DATE_COLUMN", "date").strip(),
        max_retries=env_int("CRYPTOCOMPARE_MAX_RETRIES", 5),
        delay_between_calls=env_float("CRYPTOCOMPARE_DELAY", 1.2),
        request_limit=env_int("CRYPTOCOMPARE_REQUEST_LIMIT", 2000),
    )


def _fetch(config: CCConfig, fsym: str, to_ts: int) -> dict[str, Any]:
    """1 una llamada a /data/v2/histoday con reintentos ante rate-limit/errores."""
    import urllib.request
    import urllib.error

    url = (
        f"https://min-api.cryptocompare.com/data/v2/histoday"
        f"?fsym={fsym}&tsym=USD&limit={config.request_limit}&api_key={config.api_key}"
    )
    if to_ts:
        url += f"&toTs={to_ts}"

    last_err: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if data.get("Response") != "Success":
                msg = str(data.get("Message", ""))
                # 429 / rate limit -> esperar mas y reintentar
                if "rate limit" in msg.lower():
                    wait = 3 ** (attempt + 1)
                    print(f"    ⏳ rate-limit: esperando {wait}s...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"API error: {msg}")
            return data
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429:
                wait = 3 ** (attempt + 1)
                print(f"    ⏳ HTTP 429: esperando {wait}s...")
                time.sleep(wait)
                continue
            time.sleep(2 ** (attempt + 1))
        except (urllib.error.URLError, json.JSONDecodeError, RuntimeError) as exc:
            last_err = exc
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Fallo descargando {fsym}: {last_err}")


def download_full_history(config: CCConfig, fsym: str) -> pd.DataFrame:
    """Descarga la historia completa de una moneda paginando hacia atras."""
    from datetime import datetime, timezone

    now = int(datetime.now(timezone.utc).timestamp())
    all_rows: dict[int, dict[str, Any]] = {}
    to_ts = now
    page = 0

    print(f"\n  {fsym} (CryptoCompare) — paginando hacia atras...")
    while True:
        data = _fetch(config, fsym, to_ts)["Data"]["Data"]
        if not data:
            break
        for row in data:
            all_rows[int(row["time"])] = row
        first_t = data[0]["time"]
        page += 1
        print(f"    pág {page}: {len(data)} velas hasta {to_ts} -> primera {first_t}")
        if first_t <= MIN_START_TS:
            break
        to_ts = first_t - 1
        time.sleep(config.delay_between_calls)

    if not all_rows:
        raise RuntimeError(f"No se obtuvo historico para {fsym}")

    df = pd.DataFrame(
        list(all_rows.values()),
        columns=["time", "high", "low", "open", "volumefrom", "volumeto", "close"],
    )
    return df


def build_ohlcv_frame(config: CCConfig, cc_df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el frame de CryptoCompare al formato OHLCV del repo (Qlib).

    Recorta el padding de ceros que CryptoCompare antepone a las fechas
    previas al listing real de cada moneda, para que cada coin arranque en
    su primera fecha con precio real (no con ceros).
    """
    df = pd.DataFrame({
        "date": pd.to_datetime(cc_df["time"], unit="s", utc=True).dt.normalize(),
        "open": cc_df["open"].astype(float),
        "high": cc_df["high"].astype(float),
        "low": cc_df["low"].astype(float),
        "close": cc_df["close"].astype(float),
        # volumen en moneda BASE (volumefrom) == convencion de Binance/Qlib
        "volume": cc_df["volumefrom"].astype(float),
    })
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df = df.reset_index(drop=True)

    # Recortar padding de ceros al inicio: desde el primer precio real (high>0)
    first_real = df.index[df["high"] > 0]
    if len(first_real):
        df = df.loc[first_real[0]:]

    # Estandar/campos extra esperados por convert_crypto_qlib.py
    now = pd.Timestamp.now(tz="UTC").normalize()
    df = df[df["date"] < now]
    df["adjclose"] = df["close"]
    df["change"] = df["close"].pct_change().fillna(0.0)
    df["dividends"] = 0.0
    df["factor"] = 1.0
    df["splits"] = 0.0

    cols = ["date", "open", "high", "low", "close", "volume",
            "adjclose", "change", "dividends", "factor", "splits"]
    return df[cols]


def download_all(config: CCConfig) -> dict[str, pd.DataFrame]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: dict[str, pd.DataFrame] = {}

    for instr in tqdm(config.instruments, desc="CryptoCompare"):
        fsym = SYMBOL_TO_CC.get(instr, instr)
        try:
            raw = download_full_history(config, fsym)
            frame = build_ohlcv_frame(config, raw)
        except RuntimeError as e:
            print(f"    ✗ {instr}: {e}")
            continue

        dest = config.output_dir / f"{instr.lower()}.csv"
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        frame.to_csv(tmp, index=False)
        tmp.replace(dest)
        downloaded[instr] = frame
        print(f"    ✔ {instr}: {len(frame)} filas, "
              f"{frame['date'].min().date()} -> {frame['date'].max().date()}")
        time.sleep(config.delay_between_calls)

    if not downloaded:
        raise RuntimeError("No se descargo ninguna moneda desde CryptoCompare")
    _write_manifest(config, downloaded)
    return downloaded


def _write_manifest(config: CCConfig, downloaded: dict[str, pd.DataFrame]) -> None:
    """Escribe manifest.json con checksum SHA-256 de cada CSV."""
    manifest = {"source": "cryptocompare", "endpoint": "/data/v2/histoday",
                "instruments": {}}
    for instr, frame in downloaded.items():
        path = config.output_dir / f"{instr.lower()}.csv"
        manifest["instruments"][instr] = {
            "rows": len(frame),
            "first_date": str(frame["date"].min()),
            "last_date": str(frame["date"].max()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "file": path.name,
        }
    mp = config.output_dir / "manifest.json"
    tmp = mp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(mp)


def main() -> None:
    config = get_config()
    print(f"Cargando historico completo desde CryptoCompare -> {config.output_dir}")
    download_all(config)
    print("\nListo.")


if __name__ == "__main__":
    main()