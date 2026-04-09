import sys
import os
import types
import shutil
import multiprocessing
import numpy as np
import pandas as pd
from pathlib import Path
import fire

# Resolver el repo de Qlib de forma robusta
DEFAULT_QLIB_REPO = "/mnt/d/src/qlib"
QLIB_REPO = os.environ.get("QLIB_REPO", DEFAULT_QLIB_REPO)
COLLECTOR_DIR = Path(QLIB_REPO) / "scripts" / "data_collector" / "yahoo"
if not COLLECTOR_DIR.exists():
    alt_repo = Path(__file__).resolve().parents[2] / "qlib"
    alt_collector_dir = alt_repo / "scripts" / "data_collector" / "yahoo"
    if alt_collector_dir.exists():
        COLLECTOR_DIR = alt_collector_dir
sys.path.append(str(COLLECTOR_DIR))

import collector
from collector import Run, YahooCollectorUS1d


def _install_fake_useragent_fallback():
    if "fake_useragent" in sys.modules:
        return

    fake_useragent = types.ModuleType("fake_useragent")

    class UserAgent:  # pragma: no cover - compatibility shim
        @property
        def random(self):
            return (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )

    fake_useragent.UserAgent = UserAgent
    sys.modules["fake_useragent"] = fake_useragent


def _parse_mixed_dates(values):
    parsed = pd.to_datetime(values, format="mixed", utc=True, errors="coerce")
    if isinstance(parsed, pd.Series):
        return parsed.dt.tz_convert(None)
    return parsed.tz_convert(None)


def _ensure_naive_datetime_index(values) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(pd.to_datetime(values, errors="coerce"))
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)
    return index


def _get_cached_calendar_index(calendar_list) -> pd.DatetimeIndex:
    cache = getattr(_get_cached_calendar_index, "_cache", {})
    cache_key = id(calendar_list)
    calendar_index = cache.get(cache_key)
    if calendar_index is None:
        calendar_index = _ensure_naive_datetime_index(calendar_list).unique().sort_values()
        cache[cache_key] = calendar_index
        setattr(_get_cached_calendar_index, "_cache", cache)
    return calendar_index


def _read_last_instrument_end_date(data_dir: Path) -> pd.Timestamp | None:
    ins_path = data_dir / "instruments" / "all.txt"
    if not ins_path.exists():
        return None

    df = pd.read_csv(ins_path, sep="\t", names=["symbol", "start_date", "end_date"], usecols=[0, 1, 2])
    if df.empty:
        return None

    end_dates = pd.to_datetime(df["end_date"], errors="coerce").dropna()
    if end_dates.empty:
        return None
    return end_dates.max().normalize()


def _read_last_calendar_date(data_dir: Path) -> pd.Timestamp | None:
    calendar_path = data_dir / "calendars" / "day.txt"
    if not calendar_path.exists():
        return None

    calendar_df = pd.read_csv(calendar_path, header=None)
    if calendar_df.empty:
        return None

    last_date = pd.to_datetime(calendar_df.iloc[-1, 0], errors="coerce")
    if pd.isna(last_date):
        return None
    return last_date.normalize()


def _resolve_incremental_effective_date(data_dir: Path, requested_effective_date: pd.Timestamp) -> pd.Timestamp:
    instrument_end_date = _read_last_instrument_end_date(data_dir)
    if instrument_end_date is not None:
        return min(requested_effective_date.normalize(), instrument_end_date)

    calendar_last_date = _read_last_calendar_date(data_dir)
    if calendar_last_date is not None:
        return min(requested_effective_date.normalize(), calendar_last_date)

    return requested_effective_date.normalize()


def _patch_yahoo_normalize():
    def normalize_yahoo(
        df: pd.DataFrame,
        calendar_list: list = None,
        date_field_name: str = "date",
        symbol_field_name: str = "symbol",
        last_close: float = None,
    ):
        if df.empty:
            return df

        df = df.copy()
        if date_field_name in df.columns:
            df[date_field_name] = _parse_mixed_dates(df[date_field_name])

        symbol = df.loc[df[symbol_field_name].first_valid_index(), symbol_field_name]
        df.set_index(date_field_name, inplace=True)
        df.index = _ensure_naive_datetime_index(df.index)
        df = df[~df.index.duplicated(keep="first")]

        if calendar_list is not None and not df.empty:
            calendar_index = _get_cached_calendar_index(calendar_list)
            source_index = df.index[df.index.notna()].unique().sort_values()
            if len(source_index) and not source_index.isin(calendar_index).all():
                calendar_index = calendar_index.union(source_index).sort_values()

            start_bound = pd.Timestamp(df.index.min()).normalize()
            end_bound = pd.Timestamp(df.index.max()).normalize() + pd.Timedelta(hours=23, minutes=59)
            start_pos = calendar_index.searchsorted(start_bound, side="left")
            end_pos = calendar_index.searchsorted(end_bound, side="right")
            df = df.reindex(calendar_index[start_pos:end_pos])

        df.sort_index(inplace=True)
        invalid_volume = df["volume"].isna() | (df["volume"] <= 0)
        price_columns = [col for col in df.columns if col != symbol_field_name]
        df.loc[invalid_volume, price_columns] = np.nan

        adjustment_columns = [col for col in ["high", "close", "low", "open", "adjclose"] if col in df.columns]
        warning_symbol = symbol
        count = 0
        while True:
            change_series = collector.YahooNormalize.calc_change(df, last_close)
            mask = (change_series >= 89) & (change_series <= 111)
            if not mask.any():
                break
            df.loc[mask, adjustment_columns] = df.loc[mask, adjustment_columns] / 100
            count += 1
            if count >= 10:
                collector.logger.warning(
                    f"{warning_symbol} `change` is abnormal for {count} consecutive days, please check the specific data file carefully"
                )

        df["change"] = collector.YahooNormalize.calc_change(df, last_close)
        normalized_columns = [col for col in [*collector.YahooNormalize.COLUMNS, "change"] if col in df.columns]
        df.loc[invalid_volume, normalized_columns] = np.nan

        df[symbol_field_name] = symbol
        df.index.names = [date_field_name]
        return df.reset_index()

    collector.YahooNormalize.normalize_yahoo = staticmethod(normalize_yahoo)


def _patch_mixed_date_parsing():
    original_executor = collector.Normalize._executor

    def _executor(self, file_path):
        try:
            return original_executor(self, file_path)
        except ValueError as exc:
            if "unconverted data remains when parsing with format" not in str(exc):
                raise

        file_path = Path(file_path)
        default_na = pd._libs.parsers.STR_NA_VALUES.copy()  # pylint: disable=I1101
        symbol_na = default_na.copy()
        symbol_na.remove("NA")
        columns = pd.read_csv(file_path, nrows=0).columns
        df = pd.read_csv(
            file_path,
            dtype={self._symbol_field_name: str},
            keep_default_na=False,
            na_values={col: symbol_na if col == self._symbol_field_name else default_na for col in columns},
        )

        df = self._normalize_obj.normalize(df)
        if df is not None and not df.empty:
            if self._end_date is not None:
                date_series = df[self._date_field_name]
                if pd.api.types.is_datetime64_any_dtype(date_series):
                    parsed_dates = pd.DatetimeIndex(date_series).normalize()
                else:
                    parsed_dates = _parse_mixed_dates(date_series).dt.normalize()
                end_date = pd.Timestamp(self._end_date).normalize()
                df = df[parsed_dates.notna() & (parsed_dates <= end_date)]
            df.to_csv(self._target_dir.joinpath(file_path.name), index=False)

    collector.Normalize._executor = _executor


def _patch_yahoo_normalize_extend():
    def _get_old_data(self, qlib_data_dir: [str, Path]):
        qlib_data_dir = str(Path(qlib_data_dir).expanduser().resolve())
        collector.qlib.init(provider_uri=qlib_data_dir, expression_cache=None, dataset_cache=None)
        df = collector.D.features(collector.D.instruments("all"), ["$" + col for col in self.column_list])
        df.columns = self.column_list
        if df.empty:
            return pd.DataFrame(columns=["latest_date", *self.column_list])

        valid_df = df[df["close"].notna()].reset_index()
        if valid_df.empty:
            return pd.DataFrame(columns=["latest_date", *self.column_list])

        latest_df = valid_df.groupby("instrument", sort=False, as_index=False).tail(1).copy()
        latest_df.rename(columns={"datetime": "latest_date"}, inplace=True)
        latest_df.set_index("instrument", inplace=True)
        return latest_df.loc[:, ["latest_date", *self.column_list]]

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = collector.YahooNormalize1d.normalize(self, df)
        df.set_index(self._date_field_name, inplace=True)
        symbol_name = str(df[self._symbol_field_name].iloc[0]).upper()
        if symbol_name not in self.old_qlib_data.index:
            return df.reset_index()

        old_latest_data = self.old_qlib_data.loc[symbol_name]
        latest_date = old_latest_data["latest_date"]
        df = df.loc[latest_date:]
        if df.empty:
            return df.reset_index()

        new_latest_data = df.iloc[0]
        for col in self.column_list[:-1]:
            if pd.isna(new_latest_data[col]) or pd.isna(old_latest_data[col]):
                continue
            if col == "volume":
                df[col] = df[col] / (new_latest_data[col] / old_latest_data[col])
            else:
                df[col] = df[col] * (old_latest_data[col] / new_latest_data[col])
        return df.drop(df.index[0]).reset_index()

    collector.YahooNormalize1dExtend._get_old_data = _get_old_data
    collector.YahooNormalize1dExtend.normalize = normalize


def _patch_sp500_changes_parser():
    us_index_collector = collector.importlib.import_module("data_collector.us_index.collector")

    def _flatten_column_name(column) -> str:
        if isinstance(column, tuple):
            parts = [
                str(part).strip()
                for part in column
                if str(part).strip() and not str(part).startswith("Unnamed")
            ]
            return " ".join(parts)
        return str(column).strip()

    def _get_changes(self) -> pd.DataFrame:
        us_index_collector.logger.info("get sp500 history changes......")
        headers = {"User-Agent": self._ua.random}
        response = us_index_collector.requests.get(self.WIKISP500_CHANGES_URL, headers=headers, timeout=None)
        response.raise_for_status()

        selected_df = None
        for table in reversed(us_index_collector.pd.read_html(us_index_collector.StringIO(response.text))):
            flat_columns = [_flatten_column_name(col) for col in table.columns]
            normalized = [col.lower() for col in flat_columns]
            try:
                date_idx = next(i for i, col in enumerate(normalized) if "effective date" in col or col == "date")
                add_idx = next(i for i, col in enumerate(normalized) if col.startswith("added") and "ticker" in col)
                remove_idx = next(i for i, col in enumerate(normalized) if col.startswith("removed") and "ticker" in col)
            except StopIteration:
                continue

            selected_df = table.iloc[:, [date_idx, add_idx, remove_idx]].copy()
            selected_df.columns = [self.DATE_FIELD_NAME, self.ADD, self.REMOVE]
            break

        if selected_df is None:
            raise ValueError("Could not find the SP500 changes table in the current Wikipedia page structure")

        selected_df[self.DATE_FIELD_NAME] = us_index_collector.pd.to_datetime(
            selected_df[self.DATE_FIELD_NAME], errors="coerce"
        )
        selected_df.dropna(subset=[self.DATE_FIELD_NAME], inplace=True)

        result = []
        for change_type in [self.ADD, self.REMOVE]:
            change_df = selected_df.copy()
            change_df[self.CHANGE_TYPE_FIELD] = change_type
            change_df[self.SYMBOL_FIELD_NAME] = change_df[change_type]
            change_df.dropna(subset=[self.SYMBOL_FIELD_NAME], inplace=True)
            if change_type == self.ADD:
                change_df[self.DATE_FIELD_NAME] = change_df[self.DATE_FIELD_NAME].apply(
                    lambda x: us_index_collector.get_trading_date_by_shift(self.calendar_list, x, 0)
                )
            else:
                change_df[self.DATE_FIELD_NAME] = change_df[self.DATE_FIELD_NAME].apply(
                    lambda x: us_index_collector.get_trading_date_by_shift(self.calendar_list, x, -1)
                )
            result.append(change_df[[self.DATE_FIELD_NAME, self.CHANGE_TYPE_FIELD, self.SYMBOL_FIELD_NAME]])

        us_index_collector.logger.info("end of get sp500 history changes.")
        return us_index_collector.pd.concat(result, sort=False)

    us_index_collector.SP500Index.get_changes = _get_changes


_install_fake_useragent_fallback()
_patch_yahoo_normalize()
_patch_mixed_date_parsing()
_patch_yahoo_normalize_extend()
_patch_sp500_changes_parser()


class USAllCollector(YahooCollectorUS1d):
    def get_instrument_list(self):
        print("Obteniendo lista de simbolos US_ALL exclusivamente...")
        data_dir = os.environ.get("US_ALL_INSTRUMENTS_SOURCE_DIR") or os.environ.get("US_ALL_INSTRUMENTS_DATA_DIR") or os.environ.get(
            "DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data")
        )
        effective_date = pd.Timestamp(os.environ.get("US_ALL_EFFECTIVE_DATE", pd.Timestamp.today().strftime("%Y-%m-%d")))
        use_all_symbols = os.environ.get("US_ALL_USE_ALL_SYMBOLS", "0") == "1"
        ins_path = Path(data_dir) / "instruments" / "all.txt"

        if not ins_path.exists():
            raise FileNotFoundError(
                f"No se encontro el archivo de instrumentos {ins_path}. Necesitas tener el dataset inicial US."
            )

        df = pd.read_csv(ins_path, sep="\t", names=["symbol", "start_date", "end_date"])
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
        if use_all_symbols:
            return df.loc[:, "symbol"].dropna().unique().tolist()
        active_mask = df["start_date"].le(effective_date) & df["end_date"].ge(effective_date)
        return df.loc[active_mask, "symbol"].dropna().unique().tolist()


collector.USAllCollector = USAllCollector


class USAllRun(Run):
    @staticmethod
    def _get_available_memory_gb():
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            available_pages = os.sysconf("SC_AVPHYS_PAGES")
            return (page_size * available_pages) / (1024 ** 3)
        except (AttributeError, OSError, ValueError):
            return None

    def _resolve_dump_workers(self):
        if self.max_workers is not None and self.max_workers > 1:
            return self.max_workers

        env_value = os.environ.get("QLIB_MAX_WORKERS")
        if env_value:
            try:
                return max(int(env_value), 1)
            except ValueError:
                collector.logger.warning(f"Ignoring invalid QLIB_MAX_WORKERS={env_value!r}")

        cpu_based = max(multiprocessing.cpu_count() - 2, 1)
        available_memory_gb = self._get_available_memory_gb()
        if available_memory_gb is not None and available_memory_gb < 6:
            return 1
        return min(cpu_based, 2)

    def _resolve_normalize_workers(self):
        env_value = os.environ.get("QLIB_NORMALIZE_MAX_WORKERS")
        if env_value:
            try:
                return max(int(env_value), 1)
            except ValueError:
                collector.logger.warning(f"Ignoring invalid QLIB_NORMALIZE_MAX_WORKERS={env_value!r}")

        env_value = os.environ.get("NORMALIZE_MAX_WORKERS")
        if env_value:
            try:
                return max(int(env_value), 1)
            except ValueError:
                collector.logger.warning(f"Ignoring invalid NORMALIZE_MAX_WORKERS={env_value!r}")

        if self.max_workers is not None and self.max_workers > 1:
            return self.max_workers

        cpu_based = max(multiprocessing.cpu_count() - 1, 1)
        available_memory_gb = self._get_available_memory_gb()
        if available_memory_gb is not None and available_memory_gb < 6:
            return 1
        if available_memory_gb is not None and available_memory_gb < 12:
            return min(cpu_based, 2)
        return min(cpu_based, 8)

    @staticmethod
    def _find_valid_universe_dir(base_dir: Path, target_name: str):
        candidates = []
        direct_candidate = base_dir / target_name
        candidates.append(direct_candidate)
        candidates.extend(sorted(base_dir.glob(f"{target_name}_backup_*"), reverse=True))

        for candidate in candidates:
            all_path = candidate / "instruments" / "all.txt"
            day_path = candidate / "calendars" / "day.txt"
            if (
                candidate.exists()
                and all_path.exists()
                and day_path.exists()
                and all_path.stat().st_size > 0
                and day_path.stat().st_size > 0
            ):
                return candidate
        return None

    def _refresh_us_indexes(self, qlib_data_1d_dir: str):
        get_instruments = getattr(
            collector.importlib.import_module("data_collector.us_index.collector"), "get_instruments"
        )
        for index_name in ["SP500", "NASDAQ100", "DJIA", "SP400"]:
            get_instruments(str(qlib_data_1d_dir), index_name, market_index="us_index")

    @property
    def collector_class_name(self):
        return "USAllCollector"

    def update_data_to_bin(
        self,
        qlib_data_1d_dir: str,
        trading_date: str = None,
        end_date: str = None,
        check_data_length: int = None,
        delay: float = 1,
        exists_skip: bool = False,
    ):
        if self.interval.lower() != "1d":
            collector.logger.warning("currently supports 1d data updates: --interval 1d")

        qlib_data_1d_dir = str(Path(qlib_data_1d_dir).expanduser().resolve())
        os.environ["US_ALL_INSTRUMENTS_DATA_DIR"] = qlib_data_1d_dir
        if not collector.exists_qlib_data(qlib_data_1d_dir):
            collector.GetData().qlib_data(
                target_dir=qlib_data_1d_dir, interval=self.interval, region=self.region, exists_skip=exists_skip
            )

        explicit_trading_date = trading_date is not None
        if trading_date is None:
            calendar_df = pd.read_csv(Path(qlib_data_1d_dir).joinpath("calendars/day.txt"))
            trading_date = (pd.Timestamp(calendar_df.iloc[-1, 0]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            trading_date = pd.Timestamp(trading_date).strftime("%Y-%m-%d")

        if end_date is None:
            end_date = (pd.Timestamp(trading_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = pd.Timestamp(end_date).strftime("%Y-%m-%d")
        if explicit_trading_date:
            # If the caller forces a start date, rebuild the download universe from
            # the symbols that were still active on that trading date.
            effective_date = pd.Timestamp(trading_date).normalize()
            collector.logger.info(
                f"Using explicit trading_date={trading_date} as US_ALL_EFFECTIVE_DATE for incremental universe selection"
            )
        else:
            requested_effective_date = pd.Timestamp(end_date) - pd.Timedelta(days=1)
            effective_date = _resolve_incremental_effective_date(Path(qlib_data_1d_dir), requested_effective_date)
        effective_date_str = effective_date.strftime("%Y-%m-%d")
        os.environ["US_ALL_EFFECTIVE_DATE"] = effective_date_str
        collector.logger.info(f"Using US_ALL_EFFECTIVE_DATE={effective_date_str}")

        self.download_data(delay=delay, start=trading_date, end=end_date, check_data_length=check_data_length)
        normalize_workers = self._resolve_normalize_workers()
        collector.logger.info(f"Using max_workers={normalize_workers} for incremental normalization")
        original_max_workers = self.max_workers
        self.max_workers = normalize_workers
        self.normalize_data_1d_extend(qlib_data_1d_dir)
        dump_workers = self._resolve_dump_workers()
        collector.logger.info(f"Using max_workers={dump_workers} for incremental bin dump")
        self.max_workers = dump_workers

        collector.DumpDataUpdate(
            data_path=self.normalize_dir,
            qlib_dir=qlib_data_1d_dir,
            exclude_fields="symbol,date",
            max_workers=dump_workers,
        ).dump()
        self.max_workers = original_max_workers

        self._refresh_us_indexes(qlib_data_1d_dir)

    def rebuild_data_to_bin(
        self,
        qlib_data_1d_dir: str,
        start_date: str = "1999-12-31",
        end_date: str = None,
        universe_data_dir: str = None,
        backup_existing: bool = True,
        backup_suffix: str = None,
        delay: float = 1,
    ):
        if self.interval.lower() != "1d":
            collector.logger.warning("currently supports 1d data rebuilds: --interval 1d")

        qlib_data_1d_dir = Path(qlib_data_1d_dir).expanduser().resolve()
        universe_dir = Path(universe_data_dir).expanduser().resolve() if universe_data_dir else None
        backup_dir = None

        if backup_existing and qlib_data_1d_dir.exists():
            suffix = backup_suffix or pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = qlib_data_1d_dir.parent / f"{qlib_data_1d_dir.name}_backup_{suffix}"
            if backup_dir.exists():
                raise FileExistsError(f"Backup dir already exists: {backup_dir}")
            shutil.move(str(qlib_data_1d_dir), str(backup_dir))
            collector.logger.warning(f"Existing dataset moved to backup: {backup_dir}")

        if universe_dir is None:
            if backup_dir is not None:
                universe_dir = backup_dir
            elif qlib_data_1d_dir.exists() and (qlib_data_1d_dir / "instruments" / "all.txt").exists():
                universe_dir = qlib_data_1d_dir
            else:
                universe_dir = self._find_valid_universe_dir(qlib_data_1d_dir.parent, qlib_data_1d_dir.name)

        if universe_dir is None or not (universe_dir / "instruments" / "all.txt").exists():
            raise FileNotFoundError(
                "A clean rebuild needs a valid universe source. Pass --universe_data_dir "
                "or run it over an existing dataset so its backup can be used as the universe source."
            )

        qlib_data_1d_dir.mkdir(parents=True, exist_ok=True)
        os.environ["US_ALL_INSTRUMENTS_DATA_DIR"] = str(qlib_data_1d_dir)
        os.environ["US_ALL_INSTRUMENTS_SOURCE_DIR"] = str(universe_dir)
        os.environ["US_ALL_USE_ALL_SYMBOLS"] = "1"

        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        if self.normalize_dir.exists():
            shutil.rmtree(self.normalize_dir)
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.normalize_dir.mkdir(parents=True, exist_ok=True)

        start_date = pd.Timestamp(start_date).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = pd.Timestamp.today().strftime("%Y-%m-%d")
        else:
            end_date = pd.Timestamp(end_date).strftime("%Y-%m-%d")

        effective_date = (pd.Timestamp(end_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        os.environ["US_ALL_EFFECTIVE_DATE"] = effective_date

        self.download_data(delay=delay, start=start_date, end=end_date)
        source_files = list(self.source_dir.glob("*.csv"))
        if not source_files:
            raise RuntimeError(
                "Clean rebuild aborted: no source CSV files were downloaded. "
                "The dataset will not be overwritten with empty calendars or instruments."
            )
        normalize_workers = self._resolve_normalize_workers()
        collector.logger.info(f"Using max_workers={normalize_workers} for clean rebuild normalization")
        original_max_workers = self.max_workers
        self.max_workers = normalize_workers
        self.normalize_data(end_date=end_date)
        dump_workers = self._resolve_dump_workers()
        collector.logger.info(f"Using max_workers={dump_workers} for clean rebuild bin dump")
        self.max_workers = dump_workers
        normalized_files = list(self.normalize_dir.glob("*.csv"))
        if not normalized_files:
            raise RuntimeError(
                "Clean rebuild aborted: no normalized CSV files were produced. "
                "The dataset will not be overwritten with empty calendars or instruments."
            )

        dump_bin_module = collector.importlib.import_module("dump_bin")
        dump_bin_module.DumpDataAll(
            data_path=self.normalize_dir,
            qlib_dir=str(qlib_data_1d_dir),
            exclude_fields="symbol,date",
            max_workers=dump_workers,
        ).dump()
        self.max_workers = original_max_workers

        calendar_path = qlib_data_1d_dir / "calendars" / "day.txt"
        instruments_path = qlib_data_1d_dir / "instruments" / "all.txt"
        if not calendar_path.exists() or calendar_path.stat().st_size == 0:
            raise RuntimeError("Clean rebuild failed: calendars/day.txt was generated empty.")
        if not instruments_path.exists() or instruments_path.stat().st_size == 0:
            raise RuntimeError("Clean rebuild failed: instruments/all.txt was generated empty.")

        self._refresh_us_indexes(str(qlib_data_1d_dir))


if __name__ == "__main__":
    fire.Fire(USAllRun)
