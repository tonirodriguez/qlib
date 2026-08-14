from __future__ import annotations

from pathlib import Path
import os

from dotenv import load_dotenv
import qlib
from qlib.config import REG_US
from qlib.data import D


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def env_path(name: str, default: str) -> Path:
    raw = os.getenv(name, default).strip()
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default).strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


provider_uri = env_path("CRYPTO_QLIB_OUTPUT_DIR", os.getenv("QLIB_PROVIDER_URI", "data/qlib"))
market = os.getenv("CRYPTO_UNIVERSE", os.getenv("QLIB_UNIVERSE", "crypto")).strip()
fields = [f"${field.lstrip('$')}" for field in env_list("CRYPTO_QLIB_FIELDS", "close,volume")]

qlib.init(
    provider_uri=str(provider_uri),
    region=REG_US,
    kernels=int(os.getenv("QLIB_KERNELS", "1")),
)

instruments = D.instruments(market=market)
instrument_list = D.list_instruments(instruments, freq=os.getenv("CRYPTO_FREQUENCY", "day"), as_list=True)
print(f"Provider URI: {provider_uri}")
print(f"Universe: {market}")
print(f"Instruments: {instrument_list}")

df_qlib = D.features(
    instruments,
    fields,
    start_time=os.getenv("CRYPTO_SAMPLE_START_DATE", "2024-01-01"),
    end_time=os.getenv("CRYPTO_SAMPLE_END_DATE") or None,
    freq=os.getenv("CRYPTO_FREQUENCY", "day"),
)
print(df_qlib.head())
