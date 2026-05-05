import argparse
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPORT_DIR = Path("data_lake/reports/latest")
DEFAULT_QLIB_DATA_DIR = Path(os.environ.get("DATA_DIR", "~/.qlib/qlib_data/us_data")).expanduser()

REQUIRED_COLUMNS = {
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def _csv_count(path: Path) -> int:
    return len(list(path.glob("*.csv"))) if path.exists() else 0


def default_source_candidates() -> list[Path]:
    candidates = []

    for env_name in ("QLIB_US_SOURCE_DIR", "SOURCE_DIR"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value).expanduser())

    for env_name in ("QLIB_US_WORK_DIR", "QLIB_WORK_DIR"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value).expanduser() / "source")

    candidates.extend(
        [
            Path("/tmp/qlib_us_work/source"),
            SCRIPT_DIR / "data_collector" / "yahoo" / "source",
        ]
    )
    return candidates


def resolve_source_dir(source_dir: str | None = None) -> Path:
    if source_dir:
        resolved = Path(source_dir).expanduser().resolve()
        if _csv_count(resolved) == 0:
            raise ValueError(f"No CSV files found in {resolved}")
        return resolved

    searched = []
    for candidate in default_source_candidates():
        resolved = candidate.expanduser().resolve()
        searched.append(resolved)
        if _csv_count(resolved) > 0:
            return resolved

    searched_text = "\n".join(f"  - {path}" for path in searched)
    raise ValueError(f"No CSV files found. Searched:\n{searched_text}")


def normalize_symbol(symbol: str) -> str:
    symbol = str(symbol).strip().upper()
    if symbol.startswith("_QLIB_"):
        symbol = symbol.removeprefix("_QLIB_")
    symbol = symbol.replace(".", "-")
    return symbol


def resolve_universe_path(universe: str, qlib_data_dir: str | Path) -> Path:
    universe_path = Path(universe).expanduser()
    if universe_path.exists():
        return universe_path.resolve()

    instruments_dir = Path(qlib_data_dir).expanduser().resolve() / "instruments"
    candidates = [
        instruments_dir / universe,
        instruments_dir / f"{universe}.txt",
        instruments_dir / f"{universe.lower()}.txt",
        instruments_dir / f"{universe.upper()}.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched_text = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(f"Universe file not found for {universe!r}. Searched:\n{searched_text}")


def load_universe_symbols(universe: str | None, qlib_data_dir: str | Path = DEFAULT_QLIB_DATA_DIR) -> set[str] | None:
    if not universe:
        return None

    universe_path = resolve_universe_path(universe, qlib_data_dir)
    df = pd.read_csv(universe_path, sep="\t", header=None, usecols=[0], names=["symbol"])
    symbols = {normalize_symbol(symbol) for symbol in df["symbol"].dropna()}
    if not symbols:
        raise ValueError(f"Universe file has no symbols: {universe_path}")
    return symbols


def price_csv_paths(
    source_dir: str | Path,
    limit_files: int | None = None,
    universe_symbols: set[str] | None = None,
) -> list[Path]:
    source_dir = Path(source_dir).expanduser().resolve()
    csv_paths = sorted(source_dir.glob("*.csv"))
    if universe_symbols is not None:
        csv_paths = [path for path in csv_paths if normalize_symbol(path.stem) in universe_symbols]
    if limit_files is not None:
        csv_paths = csv_paths[:limit_files]
    return csv_paths


def load_price_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["source_file"] = path.name

    if "symbol" not in df.columns:
        df["symbol"] = path.stem.upper()

    df.columns = [c.lower() for c in df.columns]
    return df


def iter_price_csvs(
    source_dir: str | Path,
    limit_files: int | None = None,
    universe_symbols: set[str] | None = None,
):
    csv_paths = price_csv_paths(source_dir, limit_files=limit_files, universe_symbols=universe_symbols)
    for path in csv_paths:
        yield path, load_price_csv(path)


def load_price_csvs(
    source_dir: str | Path,
    limit_files: int | None = None,
    universe_symbols: set[str] | None = None,
) -> pd.DataFrame:
    frames = [df for _, df in iter_price_csvs(source_dir, limit_files=limit_files, universe_symbols=universe_symbols)]

    if not frames:
        raise ValueError(f"No CSV files found in {source_dir}")

    out = pd.concat(frames, ignore_index=True)

    return out


def parse_daily_dates(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", utc=True, errors="coerce")
    if isinstance(parsed, pd.DatetimeIndex):
        parsed = pd.Series(parsed, index=values.index)
    return parsed.dt.tz_convert(None).dt.normalize()


def validate_raw_prices(
    df: pd.DataFrame,
    min_price: float = 0.5,
    max_abs_daily_return: float = 0.40,
    max_missing_ratio_per_symbol: float = 0.05,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    issues = []

    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df.copy()
    df["symbol"] = df["symbol"].astype(str).str.upper()
    raw_dates = df["date"].copy()
    df["date"] = parse_daily_dates(raw_dates)
    invalid_date = df["date"].isna()
    if invalid_date.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[invalid_date, "symbol"],
                "date": pd.NaT,
                "issue": "invalid_date",
                "severity": "error",
                "value": raw_dates.loc[invalid_date],
            })
        )

    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Duplicates
    dup_mask = df.duplicated(["symbol", "date"], keep=False)
    if dup_mask.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[dup_mask, "symbol"],
                "date": df.loc[dup_mask, "date"],
                "issue": "duplicate_symbol_date",
                "severity": "error",
                "value": np.nan,
            })
        )

    # Basic missingness
    for col in ["open", "high", "low", "close", "volume"]:
        mask = df[col].isna()
        if mask.any():
            issues.append(
                pd.DataFrame({
                    "symbol": df.loc[mask, "symbol"],
                    "date": df.loc[mask, "date"],
                    "issue": f"missing_{col}",
                    "severity": "error" if col in ["close", "volume"] else "warning",
                    "value": np.nan,
                })
            )

    # Price sanity
    checks = {
        "non_positive_open": df["open"] <= 0,
        "non_positive_high": df["high"] <= 0,
        "non_positive_low": df["low"] <= 0,
        "non_positive_close": df["close"] <= 0,
        "negative_volume": df["volume"] < 0,
        "high_less_than_low": df["high"] < df["low"],
        "open_outside_high_low": (df["open"] > df["high"]) | (df["open"] < df["low"]),
        "close_outside_high_low": (df["close"] > df["high"]) | (df["close"] < df["low"]),
        "very_low_price": df["close"] < min_price,
    }

    for issue_name, mask in checks.items():
        if mask.any():
            severity = "error" if issue_name not in ["very_low_price"] else "warning"
            issues.append(
                pd.DataFrame({
                    "symbol": df.loc[mask, "symbol"],
                    "date": df.loc[mask, "date"],
                    "issue": issue_name,
                    "severity": severity,
                    "value": df.loc[mask, "close"],
                })
            )

    # Returns
    df = df.sort_values(["symbol", "date"])
    df["ret_1d"] = df.groupby("symbol")["close"].pct_change(fill_method=None)

    ret_mask = df["ret_1d"].abs() > max_abs_daily_return
    if ret_mask.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[ret_mask, "symbol"],
                "date": df.loc[ret_mask, "date"],
                "issue": "large_raw_return",
                "severity": "warning",
                "value": df.loc[ret_mask, "ret_1d"],
            })
        )

    # Volume anomalies
    df["volume_median_20"] = (
        df.groupby("symbol")["volume"]
        .transform(lambda s: s.rolling(20, min_periods=10).median())
    )

    vol_spike = (
        (df["volume_median_20"] > 0)
        & (df["volume"] > 50 * df["volume_median_20"])
    )

    if vol_spike.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[vol_spike, "symbol"],
                "date": df.loc[vol_spike, "date"],
                "issue": "volume_spike_gt_50x_20d_median",
                "severity": "warning",
                "value": df.loc[vol_spike, "volume"],
            })
        )

    zero_vol = df["volume"] == 0
    if zero_vol.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[zero_vol, "symbol"],
                "date": df.loc[zero_vol, "date"],
                "issue": "zero_volume",
                "severity": "warning",
                "value": 0,
            })
        )

    # Per-symbol missing ratio
    symbol_summary = (
        df.groupby("symbol")
        .agg(
            first_date=("date", "min"),
            last_date=("date", "max"),
            rows=("date", "size"),
            missing_close=("close", lambda s: s.isna().sum()),
            missing_volume=("volume", lambda s: s.isna().sum()),
            min_close=("close", "min"),
            max_abs_ret=("ret_1d", lambda s: s.abs().max()),
            zero_volume_days=("volume", lambda s: (s == 0).sum()),
        )
        .reset_index()
    )

    symbol_summary["missing_close_ratio"] = (
        symbol_summary["missing_close"] / symbol_summary["rows"]
    )

    bad_missing = symbol_summary[
        symbol_summary["missing_close_ratio"] > max_missing_ratio_per_symbol
    ]

    if not bad_missing.empty:
        issues.append(
            pd.DataFrame({
                "symbol": bad_missing["symbol"],
                "date": pd.NaT,
                "issue": "high_missing_close_ratio",
                "severity": "error",
                "value": bad_missing["missing_close_ratio"],
            })
        )

    issue_df = (
        pd.concat(issues, ignore_index=True)
        if issues
        else pd.DataFrame(columns=["symbol", "date", "issue", "severity", "value"])
    )

    return df, issue_df


def validate_price_csv_dir(
    source_dir: Path,
    report_dir: Path,
    limit_files: int | None = None,
    universe_symbols: set[str] | None = None,
) -> dict:
    csv_paths = price_csv_paths(source_dir, limit_files=limit_files, universe_symbols=universe_symbols)
    if not csv_paths:
        raise ValueError(f"No CSV files found in {source_dir} for the selected universe")

    issues_path = report_dir / "raw_issues.csv"
    issue_columns = ["symbol", "date", "issue", "severity", "value"]
    pd.DataFrame(columns=issue_columns).to_csv(issues_path, index=False)

    rows = 0
    symbols = set()
    errors = 0
    warnings = 0
    processed_symbols = 0

    progress = tqdm(csv_paths, desc="Validating symbols", unit="symbol")
    for processed_symbols, path in enumerate(progress, start=1):
        df_raw = load_price_csv(path)
        current_symbols = df_raw["symbol"].dropna().astype(str).str.upper().unique()
        display_symbol = current_symbols[0] if len(current_symbols) == 1 else path.stem.upper()
        progress.set_postfix(symbol=display_symbol, errors=errors, warnings=warnings)

        clean_df, issues = validate_raw_prices(df_raw)
        rows += int(len(clean_df))
        symbols.update(clean_df["symbol"].dropna().unique().tolist())
        errors += int((issues["severity"] == "error").sum())
        warnings += int((issues["severity"] == "warning").sum())
        progress.set_postfix(symbol=display_symbol, errors=errors, warnings=warnings)

        if not issues.empty:
            issues.to_csv(issues_path, mode="a", header=False, index=False)

    return {
        "rows": rows,
        "symbols": len(symbols),
        "errors": errors,
        "warnings": warnings,
        "files": processed_symbols,
        "symbols_processed": processed_symbols,
        "universe_symbols": len(universe_symbols) if universe_symbols is not None else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Yahoo price CSV files before loading them into Qlib.")
    parser.add_argument(
        "--source-dir",
        default=None,
        help="Directory containing Yahoo price CSVs. Defaults to the current Qlib pipeline source directory.",
    )
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="Directory where raw_issues.csv and raw_summary.json will be written.",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=None,
        help="Validate only the first N CSV files. Useful for quick smoke tests.",
    )
    parser.add_argument(
        "--universe",
        default=None,
        help="Universe name or instruments file path to validate, e.g. sp500, nasdaq100, all.",
    )
    parser.add_argument(
        "--qlib-data-dir",
        default=str(DEFAULT_QLIB_DATA_DIR),
        help="Qlib data directory used to resolve --universe names.",
    )
    args = parser.parse_args()

    source_dir = resolve_source_dir(args.source_dir)
    universe_symbols = load_universe_symbols(args.universe, args.qlib_data_dir)
    report_dir = Path(args.report_dir).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading price CSVs from {source_dir}", flush=True)
    if args.universe:
        print(f"Filtering validation to universe {args.universe!r}: {len(universe_symbols)} historical symbols", flush=True)
    summary = validate_price_csv_dir(
        source_dir,
        report_dir,
        limit_files=args.limit_files,
        universe_symbols=universe_symbols,
    )

    with open(report_dir / "raw_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(summary)

    if summary["errors"] > 0:
        raise SystemExit("Blocking data errors found. Check raw_issues.csv")
