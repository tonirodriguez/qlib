#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path


DEFAULT_SYMBOLS = ["AAPL", "MSFT", "SPY", "NVDA", "QQQ"]
DEFAULT_DATES = ["2026-03-02", "2026-03-03", "2026-03-04"]
DEFAULT_FIELDS = ["close"]


def read_calendar(data_dir: Path) -> list[str]:
    calendar_path = data_dir / "calendars" / "day.txt"
    with calendar_path.open() as fp:
        return [line.strip() for line in fp if line.strip()]


def read_bin_values(bin_path: Path) -> tuple[int, list[float]]:
    values = [item[0] for item in struct.iter_unpack("<f", bin_path.read_bytes())]
    if not values:
        raise ValueError(f"Empty bin file: {bin_path}")
    return int(values[0]), values[1:]


def load_value(data_dir: Path, calendar: list[str], symbol: str, field: str, date_str: str) -> tuple[str, float | None]:
    symbol_dir = data_dir / "features" / symbol.lower()
    bin_path = symbol_dir / f"{field}.day.bin"
    if not bin_path.exists():
        return "missing_bin", None
    if date_str not in calendar:
        return "date_not_in_calendar", None

    start_idx, values = read_bin_values(bin_path)
    rel_idx = calendar.index(date_str) - start_idx
    if rel_idx < 0 or rel_idx >= len(values):
        return "out_of_range", None

    value = values[rel_idx]
    if math.isnan(value):
        return "nan", None
    return "ok", value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check selected US qlib bin values after a rebuild.")
    parser.add_argument("--data-dir", default=str(Path.home() / ".qlib" / "qlib_data" / "us_data"))
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--dates", nargs="+", default=DEFAULT_DATES)
    parser.add_argument("--fields", nargs="+", default=DEFAULT_FIELDS)
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    calendar = read_calendar(data_dir)

    print(f"data_dir: {data_dir}")
    print(f"calendar_first: {calendar[0] if calendar else 'N/A'}")
    print(f"calendar_last: {calendar[-1] if calendar else 'N/A'}")
    print()

    failed = False
    for symbol in args.symbols:
        print(symbol.upper())
        for field in args.fields:
            for date_str in args.dates:
                status, value = load_value(data_dir, calendar, symbol, field, date_str)
                if status != "ok":
                    failed = True
                    print(f"  {field:6} {date_str}  {status}")
                else:
                    print(f"  {field:6} {date_str}  {value}")
        print()

    if failed:
        print("result: FAIL")
        return 1

    print("result: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
