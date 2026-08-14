from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import uuid

from dotenv import load_dotenv
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


load_dotenv(dotenv_path=DEFAULT_ENV_PATH, override=False)


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}
DEFAULT_QLIB_FIELDS = (
    "adjclose",
    "change",
    "close",
    "dividends",
    "factor",
    "high",
    "low",
    "open",
    "splits",
    "volume",
)
SOURCE_FIELDS = DEFAULT_QLIB_FIELDS


@dataclass(frozen=True)
class CryptoQlibConfig:
    input_csv: Path
    ohlcv_dir: Path | None
    ohlcv_file_pattern: str
    output_dir: Path
    date_column: str
    instruments: tuple[str, ...]
    qlib_fields: tuple[str, ...]
    frequency: str
    universe: str
    start_date: pd.Timestamp | None
    end_date: pd.Timestamp | None
    dropna: bool
    instrument_case: str
    write_all_universe: bool
    synthesize_missing_fields: bool
    factor_default: float
    dividends_default: float
    splits_default: float
    volume_default: float
    change_fill_value: float


def env_value(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean value, got {value!r}")


def env_float(name: str, default: float) -> float:
    raw = env_value(name, "")
    if not raw:
        return default
    return float(raw)


def env_path(name: str, default: str) -> Path:
    raw = env_value(name, default)
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def env_optional_path(name: str) -> Path | None:
    raw = env_value(name, "")
    if not raw:
        return None

    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def env_list(name: str, default: str | tuple[str, ...]) -> tuple[str, ...]:
    raw = env_value(name, ",".join(default) if isinstance(default, tuple) else default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def env_date(name: str) -> pd.Timestamp | None:
    raw = env_value(name, "")
    if not raw:
        return None
    return pd.to_datetime(raw).normalize()


def normalize_qlib_field(field: str) -> str:
    field = field.strip().lower()
    if not field:
        raise ValueError("Qlib field names cannot be empty")
    return field[1:] if field.startswith("$") else field


def normalize_qlib_fields(fields: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(normalize_qlib_field(field) for field in fields))
    if not normalized:
        raise ValueError("CRYPTO_QLIB_FIELDS cannot be empty")
    return normalized


def normalize_instrument(instrument: str, instrument_case: str) -> str:
    value = instrument.strip().replace("/", "_").replace("-", "_")
    if instrument_case == "lower":
        return value.lower()
    if instrument_case == "upper":
        return value.upper()
    if instrument_case == "preserve":
        return value
    raise ValueError("CRYPTO_INSTRUMENT_CASE must be one of: lower, upper, preserve")


def get_config() -> CryptoQlibConfig:
    frequency = env_value("CRYPTO_FREQUENCY", env_value("QLIB_FREQUENCY", "day"))
    universe = env_value("CRYPTO_UNIVERSE", env_value("QLIB_UNIVERSE", "crypto"))
    output_dir = env_path("CRYPTO_QLIB_OUTPUT_DIR", env_value("QLIB_PROVIDER_URI", "data/qlib"))
    legacy_field = env_value("CRYPTO_QLIB_FIELD", "")
    qlib_fields_default = legacy_field or ",".join(DEFAULT_QLIB_FIELDS)

    return CryptoQlibConfig(
        input_csv=env_path(
            "CRYPTO_INPUT_CSV",
            "scripts/crypto/csv_data/crypto/crypto_portfolio_daily.csv",
        ),
        ohlcv_dir=env_optional_path("CRYPTO_OHLCV_DIR"),
        ohlcv_file_pattern=env_value("CRYPTO_OHLCV_FILE_PATTERN", "{instrument}.csv"),
        output_dir=output_dir,
        date_column=env_value("CRYPTO_DATE_COLUMN", "date"),
        instruments=env_list("CRYPTO_INSTRUMENTS", "BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"),
        qlib_fields=normalize_qlib_fields(env_list("CRYPTO_QLIB_FIELDS", qlib_fields_default)),
        frequency=frequency,
        universe=universe,
        start_date=env_date("CRYPTO_START_DATE"),
        end_date=env_date("CRYPTO_END_DATE"),
        dropna=env_bool("CRYPTO_DROPNA", False),
        instrument_case=env_value("CRYPTO_INSTRUMENT_CASE", "lower").lower(),
        write_all_universe=env_bool("CRYPTO_WRITE_ALL_UNIVERSE", True),
        synthesize_missing_fields=env_bool("CRYPTO_SYNTHESIZE_MISSING_FIELDS", True),
        factor_default=env_float("CRYPTO_FACTOR_DEFAULT", 1.0),
        dividends_default=env_float("CRYPTO_DIVIDENDS_DEFAULT", 0.0),
        splits_default=env_float("CRYPTO_SPLITS_DEFAULT", 0.0),
        volume_default=env_float("CRYPTO_VOLUME_DEFAULT", 0.0),
        change_fill_value=env_float("CRYPTO_CHANGE_FILL_VALUE", 0.0),
    )


def canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={column: str(column).strip().lower() for column in df.columns})


def find_column(columns: pd.Index, *candidates: str) -> str | None:
    normalized = {str(column).strip().lower(): column for column in columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def filter_dates(df: pd.DataFrame, config: CryptoQlibConfig) -> pd.DataFrame:
    if config.start_date is not None:
        df = df[df.index >= config.start_date]
    if config.end_date is not None:
        df = df[df.index <= config.end_date]
    return df


def load_single_instrument_csv(path: Path, config: CryptoQlibConfig) -> pd.DataFrame:
    df = canonical_columns(pd.read_csv(path))
    date_column = config.date_column.lower()
    if date_column not in df.columns:
        raise ValueError(f"Date column {config.date_column!r} not found in {path}")

    df[date_column] = pd.to_datetime(df[date_column]).dt.normalize()
    df = df.drop_duplicates(subset=[date_column], keep="last")
    df = df.sort_values(date_column).set_index(date_column)

    source_columns = [field for field in SOURCE_FIELDS if field in df.columns]
    if "close" not in source_columns:
        raise ValueError(f"CSV {path} must contain at least a close column")

    return filter_dates(df[source_columns].apply(pd.to_numeric, errors="coerce"), config)


def instrument_csv_path(config: CryptoQlibConfig, instrument: str) -> Path | None:
    if config.ohlcv_dir is None:
        return None

    qlib_instrument = normalize_instrument(instrument, config.instrument_case)
    filename = config.ohlcv_file_pattern.format(
        instrument=instrument,
        instrument_lower=instrument.lower(),
        instrument_upper=instrument.upper(),
        qlib_instrument=qlib_instrument,
    )
    return config.ohlcv_dir / filename


def load_frames_from_ohlcv_dir(
    config: CryptoQlibConfig,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    frames: dict[str, pd.DataFrame] = {}
    warnings: list[str] = []

    for instrument in config.instruments:
        path = instrument_csv_path(config, instrument)
        if path is None:
            continue
        if not path.exists():
            warnings.append(f"{instrument}: OHLCV file not found at {path}")
            continue
        frames[instrument] = load_single_instrument_csv(path, config)

    return frames, warnings


def load_frames_from_wide_csv(
    config: CryptoQlibConfig,
    existing_frames: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    if not config.input_csv.exists():
        missing = [instrument for instrument in config.instruments if instrument not in existing_frames]
        if missing:
            raise FileNotFoundError(f"Input CSV not found: {config.input_csv}")
        return existing_frames, []

    raw = pd.read_csv(config.input_csv)
    date_column = find_column(raw.columns, config.date_column)
    if date_column is None:
        raise ValueError(f"Date column {config.date_column!r} not found in {config.input_csv}")

    raw[date_column] = pd.to_datetime(raw[date_column]).dt.normalize()
    raw = raw.drop_duplicates(subset=[date_column], keep="last")
    raw = raw.sort_values(date_column)
    raw = filter_dates(raw.set_index(date_column), config)

    frames = dict(existing_frames)
    warnings: list[str] = []
    missing: list[str] = []

    for instrument in config.instruments:
        if instrument in frames:
            continue

        instrument_columns: dict[str, str] = {}
        for field in SOURCE_FIELDS:
            column = find_column(
                raw.columns,
                f"{instrument}_{field}",
                f"{field}_{instrument}",
                f"{instrument}.{field}",
                f"{field}.{instrument}",
                f"{instrument}-{field}",
                f"{field}-{instrument}",
            )
            if column is not None:
                instrument_columns[field] = column

        close_column = find_column(raw.columns, instrument)
        if close_column is not None and "close" not in instrument_columns:
            instrument_columns["close"] = close_column
            warnings.append(
                f"{instrument}: using close-only portfolio column; missing OHLCV fields will be synthesized"
            )

        if "close" not in instrument_columns:
            missing.append(instrument)
            continue

        frame = pd.DataFrame(index=raw.index)
        for field, column in instrument_columns.items():
            frame[field] = pd.to_numeric(raw[column], errors="coerce")
        frames[instrument] = frame

    if missing:
        raise ValueError(f"Missing instrument data in CSV: {', '.join(missing)}")

    return frames, warnings


def load_source_frames(config: CryptoQlibConfig) -> tuple[dict[str, pd.DataFrame], list[str]]:
    frames, warnings = load_frames_from_ohlcv_dir(config)
    frames, wide_warnings = load_frames_from_wide_csv(config, frames)
    warnings.extend(wide_warnings)

    missing = [instrument for instrument in config.instruments if instrument not in frames]
    if missing:
        raise ValueError(f"Missing instrument data: {', '.join(missing)}")

    empty = [instrument for instrument, frame in frames.items() if frame.empty]
    if empty:
        raise ValueError(f"No rows remain after filtering for: {', '.join(empty)}")

    return frames, warnings


def constant_series(index: pd.DatetimeIndex, value: float) -> pd.Series:
    return pd.Series(value, index=index, dtype="float32")


def build_feature_frame(
    instrument: str,
    source: pd.DataFrame,
    config: CryptoQlibConfig,
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if "close" not in source.columns:
        raise ValueError(f"{instrument}: source data must contain close")

    close = source["close"].astype("float32")
    features = pd.DataFrame(index=source.index)

    for field in config.qlib_fields:
        if field in source.columns:
            features[field] = source[field].astype("float32")
            continue

        if field == "adjclose":
            features[field] = close
            warnings.append(f"{instrument}: synthesized adjclose from close")
        elif field == "change":
            features[field] = close.pct_change().fillna(config.change_fill_value).astype("float32")
            warnings.append(f"{instrument}: synthesized change from close.pct_change()")
        elif field == "factor":
            features[field] = constant_series(source.index, config.factor_default)
            warnings.append(f"{instrument}: synthesized factor={config.factor_default:g}")
        elif field == "dividends":
            features[field] = constant_series(source.index, config.dividends_default)
            warnings.append(f"{instrument}: synthesized dividends={config.dividends_default:g}")
        elif field == "splits":
            features[field] = constant_series(source.index, config.splits_default)
            warnings.append(f"{instrument}: synthesized splits={config.splits_default:g}")
        elif field == "volume":
            if not config.synthesize_missing_fields:
                raise ValueError(f"{instrument}: missing source field volume")
            features[field] = constant_series(source.index, config.volume_default)
            warnings.append(f"{instrument}: synthesized volume={config.volume_default:g}")
        elif field in {"open", "high", "low"} and config.synthesize_missing_fields:
            features[field] = close
            warnings.append(f"{instrument}: synthesized {field} from close")
        else:
            raise ValueError(f"{instrument}: missing source field {field}")

    if config.dropna:
        features = features.dropna(subset=list(config.qlib_fields))

    if features.empty:
        raise ValueError(f"{instrument}: no feature rows remain after null filtering")

    return features, warnings


def format_date(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%d")


def write_calendar(calendar_dir: Path, frequency: str, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    calendar_dir.mkdir(parents=True, exist_ok=True)
    calendar = pd.DatetimeIndex(sorted(pd.Timestamp(date).normalize() for date in dates.unique()))
    calendar_file = calendar_dir / f"{frequency}.txt"
    calendar_file.write_text("\n".join(format_date(date) for date in calendar) + "\n", encoding="utf-8")
    return calendar


def write_instruments(
    instruments_dir: Path,
    universe: str,
    instrument_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    write_all_universe: bool,
) -> None:
    instruments_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{instrument}\t{format_date(start)}\t{format_date(end)}"
        for instrument, (start, end) in sorted(instrument_ranges.items())
    ]

    (instruments_dir / f"{universe}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if write_all_universe and universe != "all":
        (instruments_dir / "all.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_feature_bin(
    features_dir: Path,
    instrument: str,
    field: str,
    frequency: str,
    calendar_index: pd.DatetimeIndex,
    values: pd.Series,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    series = values.astype("float32").reindex(calendar_index)
    valid = series.notna()
    if not valid.any():
        raise ValueError(f"Instrument {instrument} field {field} has no valid values")

    first_pos = int(np.argmax(valid.to_numpy()))
    last_pos = len(valid) - 1 - int(np.argmax(valid.to_numpy()[::-1]))
    trimmed = series.iloc[first_pos : last_pos + 1].to_numpy(dtype="<f4")

    payload = np.empty(len(trimmed) + 1, dtype="<f4")
    payload[0] = np.float32(first_pos)
    payload[1:] = trimmed

    instrument_dir = features_dir / instrument
    instrument_dir.mkdir(parents=True, exist_ok=True)
    (instrument_dir / f"{field}.{frequency}.bin").write_bytes(payload.tobytes())

    return calendar_index[first_pos], calendar_index[last_pos]


def write_instrument_features(
    features_dir: Path,
    qlib_instrument: str,
    feature_frame: pd.DataFrame,
    config: CryptoQlibConfig,
    calendar_index: pd.DatetimeIndex,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}

    for field in config.qlib_fields:
        ranges[field] = write_feature_bin(
            features_dir=features_dir,
            instrument=qlib_instrument,
            field=field,
            frequency=config.frequency,
            calendar_index=calendar_index,
            values=feature_frame[field],
        )

    return ranges.get("close", next(iter(ranges.values())))


def _build_qlib_provider(config: CryptoQlibConfig) -> dict[str, object]:
    source_frames, warnings = load_source_frames(config)
    feature_frames: dict[str, pd.DataFrame] = {}

    for instrument in config.instruments:
        feature_frame, frame_warnings = build_feature_frame(instrument, source_frames[instrument], config)
        feature_frames[instrument] = feature_frame
        warnings.extend(frame_warnings)

    calendar_dates = pd.DatetimeIndex([])
    for frame in feature_frames.values():
        calendar_dates = calendar_dates.union(frame.index)
    calendar_index = write_calendar(config.output_dir / "calendars", config.frequency, calendar_dates)

    features_dir = config.output_dir / "features"
    instrument_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}

    for source_instrument, feature_frame in feature_frames.items():
        qlib_instrument = normalize_instrument(source_instrument, config.instrument_case)
        start, end = write_instrument_features(
            features_dir=features_dir,
            qlib_instrument=qlib_instrument,
            feature_frame=feature_frame,
            config=config,
            calendar_index=calendar_index,
        )
        instrument_ranges[qlib_instrument] = (start, end)

    write_instruments(
        instruments_dir=config.output_dir / "instruments",
        universe=config.universe,
        instrument_ranges=instrument_ranges,
        write_all_universe=config.write_all_universe,
    )

    return {
        "rows": len(calendar_index),
        "instruments": len(config.instruments),
        "fields": len(config.qlib_fields),
        "field_names": ", ".join(config.qlib_fields),
        "start": format_date(calendar_index.min()),
        "end": format_date(calendar_index.max()),
        "output_dir": str(config.output_dir),
        "universe": config.universe,
        "frequency": config.frequency,
        "warnings": sorted(set(warnings)),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_staged_provider(config: CryptoQlibConfig, summary: dict[str, object]) -> None:
    calendar = config.output_dir / "calendars" / f"{config.frequency}.txt"
    universe = config.output_dir / "instruments" / f"{config.universe}.txt"
    if not calendar.is_file() or not universe.is_file():
        raise RuntimeError("Staged provider is missing calendar or universe files")

    calendar_lines = [line for line in calendar.read_text(encoding="utf-8").splitlines() if line]
    universe_lines = [line for line in universe.read_text(encoding="utf-8").splitlines() if line]
    if len(calendar_lines) != summary["rows"]:
        raise RuntimeError("Staged calendar row count does not match build summary")
    if len(universe_lines) != summary["instruments"]:
        raise RuntimeError("Staged universe count does not match build summary")

    expected_instruments = {
        normalize_instrument(instrument, config.instrument_case) for instrument in config.instruments
    }
    actual_instruments = {line.split("\t", 1)[0] for line in universe_lines}
    if actual_instruments != expected_instruments:
        raise RuntimeError("Staged universe does not match configured instruments")

    for instrument in expected_instruments:
        for field in config.qlib_fields:
            feature = config.output_dir / "features" / instrument / f"{field}.{config.frequency}.bin"
            if not feature.is_file() or feature.stat().st_size <= 4:
                raise RuntimeError(f"Missing or empty staged feature: {instrument}/{field}")


def write_provider_manifest(config: CryptoQlibConfig, summary: dict[str, object]) -> None:
    files = sorted(path for path in config.output_dir.rglob("*") if path.is_file())
    manifest = {
        "schema_version": 1,
        "universe": config.universe,
        "frequency": config.frequency,
        "ordered_instruments": [
            normalize_instrument(instrument, config.instrument_case) for instrument in config.instruments
        ],
        "fields": list(config.qlib_fields),
        "rows": summary["rows"],
        "start": summary["start"],
        "end": summary["end"],
        "files": {
            str(path.relative_to(config.output_dir)): {
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in files
        },
    }
    (config.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate_publish_target(target: Path) -> None:
    resolved = target.resolve()
    forbidden = {Path("/").resolve(), PROJECT_ROOT.resolve(), Path.home().resolve()}
    if resolved in forbidden or not target.name:
        raise ValueError(f"Unsafe Qlib output directory: {target}")


def convert_to_qlib(config: CryptoQlibConfig) -> dict[str, object]:
    """Build, validate and atomically publish a complete Qlib provider."""
    target = config.output_dir
    validate_publish_target(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    backup: Path | None = None

    try:
        staged_config = replace(config, output_dir=staging)
        summary = _build_qlib_provider(staged_config)
        validate_staged_provider(staged_config, summary)
        write_provider_manifest(staged_config, summary)

        if target.exists():
            backup = target.parent / f".{target.name}.backup-{uuid.uuid4().hex}"
            target.replace(backup)
        try:
            staging.replace(target)
        except Exception:
            if backup is not None and backup.exists() and not target.exists():
                backup.replace(target)
            raise

        if backup is not None:
            shutil.rmtree(backup)
        summary["output_dir"] = str(target)
        summary["manifest"] = str(target / "manifest.json")
        return summary
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    summary = convert_to_qlib(get_config())
    print("Crypto data converted to Qlib format")
    print(f"  output_dir: {summary['output_dir']}")
    print(f"  universe: {summary['universe']}")
    print(f"  instruments: {summary['instruments']}")
    print(f"  fields: {summary['fields']} ({summary['field_names']})")
    print(f"  rows: {summary['rows']}")
    print(f"  range: {summary['start']} -> {summary['end']}")
    print(f"  frequency: {summary['frequency']}")

    warnings = summary["warnings"]
    if warnings:
        print("  warnings:")
        for warning in warnings:
            print(f"    - {warning}")


if __name__ == "__main__":
    main()
