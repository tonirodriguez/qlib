#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path
import argparse
import math
import sys

import pandas as pd


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _is_equal(left, right) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if isinstance(left, float) or isinstance(right, float):
        if pd.isna(left) and pd.isna(right):
            return True
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=0.0)
    return left == right


def _compare_frames(left: pd.DataFrame, right: pd.DataFrame, file_name: str, max_diffs: int) -> list[str]:
    diffs: list[str] = []
    if list(left.columns) != list(right.columns):
        diffs.append(f"{file_name}: columns differ: {list(left.columns)} != {list(right.columns)}")
        return diffs

    if len(left) != len(right):
        diffs.append(f"{file_name}: row count differs: {len(left)} != {len(right)}")
        return diffs

    for row_idx in range(len(left)):
        left_row = left.iloc[row_idx]
        right_row = right.iloc[row_idx]
        for col in left.columns:
            if not _is_equal(left_row[col], right_row[col]):
                diffs.append(
                    f"{file_name}: row {row_idx + 1}, column {col!r} differs: "
                    f"{left_row[col]!r} != {right_row[col]!r}"
                )
                if len(diffs) >= max_diffs:
                    return diffs
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two normalization output directories and report any A/B differences."
    )
    parser.add_argument("--a", required=True, help="Directory A with normalized CSV files")
    parser.add_argument("--b", required=True, help="Directory B with normalized CSV files")
    parser.add_argument("--max-diffs", type=int, default=20, help="Maximum number of differences to print")
    args = parser.parse_args()

    dir_a = Path(args.a).expanduser().resolve()
    dir_b = Path(args.b).expanduser().resolve()

    files_a = {path.name: path for path in dir_a.glob("*.csv")}
    files_b = {path.name: path for path in dir_b.glob("*.csv")}

    only_a = sorted(set(files_a) - set(files_b))
    only_b = sorted(set(files_b) - set(files_a))
    common = sorted(set(files_a) & set(files_b))

    problems: list[str] = []
    if only_a:
        problems.append(f"Only in A: {', '.join(only_a[:args.max_diffs])}")
    if only_b:
        problems.append(f"Only in B: {', '.join(only_b[:args.max_diffs])}")

    compared = 0
    for name in common:
        left = _load_csv(files_a[name])
        right = _load_csv(files_b[name])
        diffs = _compare_frames(left, right, name, args.max_diffs - len(problems))
        problems.extend(diffs)
        compared += 1
        if len(problems) >= args.max_diffs:
            break

    print(f"Compared {compared} shared files")
    if problems:
        print("Differences found:")
        for problem in problems[: args.max_diffs]:
            print(f"- {problem}")
        return 1

    print("No differences found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
