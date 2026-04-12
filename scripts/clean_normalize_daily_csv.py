#!/usr/bin/env python

from __future__ import annotations

import csv
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fire
import pandas as pd


def _default_normalize_dir() -> Path:
    tmp_dir = Path("/tmp/qlib_us_work/normalize")
    if tmp_dir.exists():
        return tmp_dir
    return Path(__file__).resolve().parent / "data_collector" / "yahoo" / "normalize"


@dataclass
class FileSummary:
    file_name: str
    total_rows: int
    rows_with_time: int
    duplicate_days: int
    extra_rows_removed: int
    invalid_dates: int
    changed: bool
    skipped: bool
    reason: str = ""


class NormalizeDailyCsvCleaner:
    def __init__(self, normalize_dir: str | None = None):
        self.normalize_dir = Path(normalize_dir).expanduser().resolve() if normalize_dir else _default_normalize_dir()

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fp:
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _iter_csv_files(base_dir: Path) -> Iterable[Path]:
        return sorted(base_dir.glob("*.csv"))

    @staticmethod
    def _build_backup_path(backup_dir: Path, file_path: Path) -> Path:
        return backup_dir / file_path.name

    def _clean_one(self, file_path: Path, apply: bool = False, backup_dir: Path | None = None) -> FileSummary:
        df = pd.read_csv(file_path)
        if "date" not in df.columns:
            return FileSummary(file_path.name, 0, 0, 0, 0, 0, False, True, "missing `date` column")

        parsed_dates = pd.to_datetime(df["date"], errors="coerce")
        invalid_dates = int(parsed_dates.isna().sum())
        if invalid_dates:
            return FileSummary(
                file_path.name,
                int(len(df)),
                0,
                0,
                0,
                invalid_dates,
                False,
                True,
                "contains invalid dates",
            )

        normalized_dates = parsed_dates.dt.normalize()
        rows_with_time = int((parsed_dates != normalized_dates).sum())
        duplicate_mask = normalized_dates.duplicated(keep=False)
        duplicate_days = int(normalized_dates[duplicate_mask].nunique())

        cleaned_df = df.copy()
        cleaned_df["date"] = normalized_dates.dt.strftime("%Y-%m-%d")
        cleaned_df["_date_sort"] = normalized_dates
        cleaned_df = cleaned_df.sort_values(["_date_sort"], kind="stable")
        cleaned_df = cleaned_df.drop_duplicates(subset=["_date_sort"], keep="last")
        cleaned_df = cleaned_df.drop(columns=["_date_sort"])
        extra_rows_removed = int(len(df) - len(cleaned_df))

        original_hash = self._hash_file(file_path)
        changed = rows_with_time > 0 or extra_rows_removed > 0

        if apply and changed:
            if backup_dir is not None:
                backup_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, self._build_backup_path(backup_dir, file_path))
            cleaned_df.to_csv(file_path, index=False, quoting=csv.QUOTE_MINIMAL)
            changed = original_hash != self._hash_file(file_path)

        return FileSummary(
            file_path.name,
            int(len(df)),
            rows_with_time,
            duplicate_days,
            extra_rows_removed,
            invalid_dates,
            changed,
            False,
        )

    def run(
        self,
        normalize_dir: str | None = None,
        apply: bool = False,
        backup_dir: str | None = None,
        limit: int | None = None,
        only_changed: bool = True,
    ):
        target_dir = Path(normalize_dir).expanduser().resolve() if normalize_dir else self.normalize_dir
        if not target_dir.exists():
            raise FileNotFoundError(f"normalize_dir not found: {target_dir}")

        csv_files = list(self._iter_csv_files(target_dir))
        if limit is not None:
            csv_files = csv_files[: int(limit)]

        resolved_backup_dir = None
        if apply:
            if backup_dir:
                resolved_backup_dir = Path(backup_dir).expanduser().resolve()
            else:
                resolved_backup_dir = target_dir.parent / f"{target_dir.name}_backup_before_cleanup"

        summaries = [self._clean_one(file_path, apply=apply, backup_dir=resolved_backup_dir) for file_path in csv_files]

        changed_files = [s for s in summaries if s.changed]
        skipped_files = [s for s in summaries if s.skipped]
        files_with_time = [s for s in summaries if s.rows_with_time > 0]
        files_with_duplicates = [s for s in summaries if s.duplicate_days > 0]

        print(f"normalize_dir: {target_dir}")
        print(f"files_checked: {len(summaries)}")
        print(f"files_with_time_rows: {len(files_with_time)}")
        print(f"files_with_duplicate_days: {len(files_with_duplicates)}")
        print(f"files_skipped: {len(skipped_files)}")
        print(f"files_changed: {len(changed_files)}")
        print(f"total_time_rows: {sum(s.rows_with_time for s in summaries)}")
        print(f"total_duplicate_days: {sum(s.duplicate_days for s in summaries)}")
        print(f"total_extra_rows_removed: {sum(s.extra_rows_removed for s in summaries)}")

        if resolved_backup_dir is not None and apply and changed_files:
            print(f"backup_dir: {resolved_backup_dir}")

        display_rows = summaries
        if only_changed:
            display_rows = [s for s in summaries if s.changed or s.skipped]

        if display_rows:
            print("\nfile_name,total_rows,rows_with_time,duplicate_days,extra_rows_removed,invalid_dates,changed,skipped,reason")
            for summary in display_rows:
                print(
                    f"{summary.file_name},{summary.total_rows},{summary.rows_with_time},{summary.duplicate_days},"
                    f"{summary.extra_rows_removed},{summary.invalid_dates},{summary.changed},{summary.skipped},{summary.reason}"
                )


def run(
    normalize_dir: str | None = None,
    apply: bool = False,
    backup_dir: str | None = None,
    limit: int | None = None,
    only_changed: bool = True,
):
    cleaner = NormalizeDailyCsvCleaner(normalize_dir=normalize_dir)
    return cleaner.run(
        normalize_dir=normalize_dir,
        apply=apply,
        backup_dir=backup_dir,
        limit=limit,
        only_changed=only_changed,
    )


if __name__ == "__main__":
    fire.Fire({"run": run})
