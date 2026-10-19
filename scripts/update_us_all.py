import sys
import os
from pathlib import Path
import types
import shutil
import csv
import time
import multiprocessing
import numpy as np
import pandas as pd
import fire

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
for _path in (REPO_ROOT, SCRIPTS_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

try:
    from scripts.data_collector.base import _write_csv_with_retry
except ModuleNotFoundError:
    from data_collector.base import _write_csv_with_retry

# Resolver el repo de Qlib de forma robusta
DEFAULT_QLIB_REPO = REPO_ROOT
QLIB_REPO = Path(os.environ.get("QLIB_REPO", DEFAULT_QLIB_REPO)).expanduser().resolve()
COLLECTOR_DIR = Path(QLIB_REPO) / "scripts" / "data_collector" / "yahoo"
if not COLLECTOR_DIR.exists():
    alt_repo = REPO_ROOT
    alt_collector_dir = alt_repo / "scripts" / "data_collector" / "yahoo"
    if alt_collector_dir.exists():
        COLLECTOR_DIR = alt_collector_dir
sys.path.append(str(COLLECTOR_DIR))

import collector
from collector import Run, YahooCollectorUS1d
from qlib.utils import code_to_fname, fname_to_code


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


def _last_closed_session_date() -> pd.Timestamp:
    """Ultima fecha cuya sesion ya ha cerrado en NY (16:00 ET, con 15 min de margen).

    Yahoo devuelve barras del dia en curso para algunos simbolos; si se volcaran,
    el dia entra en el calendario con datos intradia y cobertura parcial, y
    DumpDataUpdate no reescribe fechas ya volcadas (queda NaN permanente).
    """
    now_ny = pd.Timestamp.now(tz="America/New_York")
    close_today = now_ny.normalize() + pd.Timedelta(hours=16, minutes=15)
    last = now_ny.normalize() if now_ny >= close_today else now_ny.normalize() - pd.Timedelta(days=1)
    return last.tz_localize(None)


def _sanitize_normalized_daily_csv(file_path: Path, max_date: pd.Timestamp = None) -> dict | None:
    df = pd.read_csv(file_path)
    if df.empty or "date" not in df.columns:
        return None

    # format="mixed": sin esto pandas infiere el formato de la primera fila y convierte
    # en NaT las que traen hora, descartandolas en silencio.
    parsed_dates = pd.to_datetime(df["date"], format="mixed", errors="coerce")
    if getattr(parsed_dates.dt, "tz", None) is not None:
        parsed_dates = parsed_dates.dt.tz_localize(None)
    valid_mask = parsed_dates.notna()
    if not valid_mask.all():
        df = df.loc[valid_mask].copy()
        parsed_dates = parsed_dates.loc[valid_mask]
    if df.empty:
        return None

    normalized_dates = parsed_dates.dt.normalize()
    future_rows = 0
    if max_date is not None:
        future_mask = normalized_dates > max_date
        future_rows = int(future_mask.sum())
        if future_rows:
            df = df.loc[~future_mask].copy()
            parsed_dates = parsed_dates.loc[~future_mask]
            normalized_dates = normalized_dates.loc[~future_mask]
            if df.empty:
                file_path.write_text(",".join(df.columns) + "\n")
                return {"file_name": file_path.name, "rows_with_time": 0, "duplicate_rows_removed": 0, "future_rows_removed": future_rows}
    duplicate_rows = int(normalized_dates.duplicated(keep=False).sum())
    rows_with_time = int((parsed_dates != normalized_dates).sum())
    if duplicate_rows == 0 and rows_with_time == 0 and future_rows == 0:
        return None

    cleaned_df = df.copy()
    cleaned_df["date"] = normalized_dates.dt.strftime("%Y-%m-%d")
    cleaned_df["_date_sort"] = normalized_dates
    cleaned_df = cleaned_df.sort_values(["_date_sort"], kind="stable")
    cleaned_df = cleaned_df.drop_duplicates(subset=["_date_sort"], keep="last")
    cleaned_df = cleaned_df.drop(columns=["_date_sort"])
    cleaned_df.to_csv(file_path, index=False, quoting=csv.QUOTE_MINIMAL)

    return {
        "file_name": file_path.name,
        "rows_with_time": rows_with_time,
        "duplicate_rows_removed": int(len(df) - len(cleaned_df)),
        "future_rows_removed": future_rows,
    }


def _sanitize_normalize_dir(normalize_dir: Path, max_date: pd.Timestamp = None):
    if max_date is None:
        max_date = _last_closed_session_date()
    collector.logger.info(f"Discarding rows after the last closed session: {max_date.date()}")
    summaries = []
    for file_path in sorted(normalize_dir.glob("*.csv")):
        summary = _sanitize_normalized_daily_csv(file_path, max_date=max_date)
        if summary is not None:
            summaries.append(summary)

    if summaries:
        total_time_rows = sum(item["rows_with_time"] for item in summaries)
        total_removed = sum(item["duplicate_rows_removed"] for item in summaries)
        total_future = sum(item.get("future_rows_removed", 0) for item in summaries)
        collector.logger.warning(
            "Sanitized normalized daily CSV files before dump_bin: "
            f"files={len(summaries)}, rows_with_time={total_time_rows}, "
            f"duplicate_rows_removed={total_removed}, future_rows_removed={total_future}"
        )
    else:
        collector.logger.info("Normalized daily CSV files are already deduplicated by date")


def _check_recent_coverage(
    qlib_data_1d_dir: Path, lookback: int = 5, min_ratio: float = 0.6, sample_size: int = 800
) -> list:
    """Avisa si algun dia recien volcado tiene cobertura anomala.

    Un dia que entra en el calendario con datos de pocos simbolos (p. ej. barras del dia
    en curso) deja NaN permanente en el resto: DumpDataUpdate no reescribe fechas ya
    volcadas. Detectarlo el mismo dia permite corregirlo antes de que se acumule.
    """
    qlib_data_1d_dir = Path(qlib_data_1d_dir)
    calendar_path = qlib_data_1d_dir / "calendars" / "day.txt"
    instruments_path = qlib_data_1d_dir / "instruments" / "all.txt"
    if not calendar_path.exists() or not instruments_path.exists():
        return []

    calendar = pd.read_csv(calendar_path, header=None)[0].tolist()
    if not calendar:
        return []
    recent = calendar[-lookback:]
    recent_idx = {d: len(calendar) - lookback + i for i, d in enumerate(recent)}

    # Solo simbolos activos: all.txt conserva los delistados (sin dato reciente por
    # definicion) y meterlos en la muestra bajaria la cobertura sin que haya fallo.
    symbols = sorted(_active_symbols(qlib_data_1d_dir, days=30))
    if not symbols:
        return []
    step = max(1, len(symbols) // sample_size)
    symbols = symbols[::step][:sample_size]

    counts = {d: 0 for d in recent}
    checked = 0
    for symbol in symbols:
        bin_path = qlib_data_1d_dir / "features" / code_to_fname(symbol).lower() / "close.day.bin"
        if not bin_path.exists():
            continue
        try:
            arr = np.fromfile(bin_path, dtype="<f4")
        except OSError:
            continue
        if arr.size < 2:
            continue
        checked += 1
        start = int(arr[0])
        values = arr[1:]
        for d, idx in recent_idx.items():
            pos = idx - start
            if 0 <= pos < values.size and not np.isnan(values[pos]):
                counts[d] += 1

    if not checked:
        return []

    anomalies = []
    for d in recent:
        ratio = counts[d] / checked
        msg = f"{d}: {counts[d]}/{checked} simbolos con dato ({ratio:.0%})"
        if ratio < min_ratio:
            anomalies.append((d, counts[d], checked, ratio))
            collector.logger.error(f"COBERTURA ANOMALA -> {msg}")
        else:
            collector.logger.info(f"cobertura {msg}")

    if anomalies:
        collector.logger.error(
            "Hay dias con cobertura anomala. DumpDataUpdate no reescribe fechas ya volcadas: "
            "corrige esos dias explicitamente (parche dirigido o clean rebuild --full)."
        )
    return anomalies


def _read_instruments_df(instruments_path: Path) -> pd.DataFrame:
    # keep_default_na=False: "NA" (Nano Labs) es un ticker real, no un nulo
    df = pd.read_csv(
        instruments_path,
        sep="\t",
        names=["symbol", "start_date", "end_date"],
        usecols=[0, 1, 2],
        dtype=str,
        keep_default_na=False,
    )
    return df.loc[df["symbol"] != ""].reset_index(drop=True)


def _read_calendar_list(qlib_data_1d_dir: Path) -> list:
    calendar_path = Path(qlib_data_1d_dir) / "calendars" / "day.txt"
    if not calendar_path.exists():
        return []
    return pd.read_csv(calendar_path, header=None, dtype=str)[0].tolist()


def _active_symbols(qlib_data_1d_dir: Path, days: int = 10) -> set:
    """Simbolos cuyo end_date esta a <= `days` dias naturales del ultimo end_date."""
    instruments_path = Path(qlib_data_1d_dir) / "instruments" / "all.txt"
    if not instruments_path.exists():
        return set()
    df = _read_instruments_df(instruments_path)
    end_dates = pd.to_datetime(df["end_date"], errors="coerce")
    if end_dates.dropna().empty:
        return set()
    cutoff = end_dates.max() - pd.Timedelta(days=days)
    return set(df.loc[end_dates >= cutoff, "symbol"])


def _current_index_members(qlib_data_1d_dir: Path, index_names=("sp500", "nasdaq100")) -> set:
    members = set()
    for name in index_names:
        path = Path(qlib_data_1d_dir) / "instruments" / f"{name}.txt"
        if not path.exists():
            continue
        df = _read_instruments_df(path)
        end_dates = pd.to_datetime(df["end_date"], errors="coerce")
        if end_dates.dropna().empty:
            continue
        members |= set(df.loc[end_dates >= end_dates.max(), "symbol"])
    return members


def _source_file_name(symbol: str) -> str:
    # Mismo nombre que YahooCollectorUS.save_instrument: code_to_fname(symbol).upper()
    return f"{code_to_fname(symbol).upper()}.csv"


def _remap_bin_to_calendar(arr: np.ndarray, old_calendar: list, new_index: dict) -> np.ndarray | None:
    """Reubica un .bin (cabecera = posicion de inicio en el calendario) en otro calendario.

    Devuelve None si algun valor no nulo cae en una fecha que no existe en el nuevo.
    """
    start = int(arr[0])
    values = arr[1:]
    if values.size == 0:
        return None
    dates = old_calendar[start : start + values.size]
    if len(dates) != values.size:
        return None
    positions = np.array([new_index.get(d, -1) for d in dates])
    valid = ~np.isnan(values)
    if (positions[valid] < 0).any():
        return None
    keep = positions >= 0
    positions, values = positions[keep], values[keep]
    new_start = int(positions.min())
    out = np.full(int(positions.max()) - new_start + 1, np.nan, dtype="<f4")
    out[positions - new_start] = values
    return np.concatenate([np.array([new_start], dtype="<f4"), out])


def _restore_missing_from_backup(target_dir: Path, backup_dir: Path, symbols=None) -> list:
    """Copia al dataset nuevo el historico de los simbolos que estaban en el backup y faltan.

    Un clean rebuild solo contiene lo que Yahoo devolvio en esa ejecucion: los delistados
    que Yahoo ya no sirve y los simbolos que fallaron de forma transitoria desaparecian
    (Fallo 6: 2.387 simbolos, entre ellos ABT). Aqui se conservan con su end_date original;
    los que siguen cotizando se ponen al dia en el siguiente incremental/resync.
    """
    target_dir, backup_dir = Path(target_dir), Path(backup_dir)
    target_ins = target_dir / "instruments" / "all.txt"
    backup_ins = backup_dir / "instruments" / "all.txt"
    if not target_ins.exists() or not backup_ins.exists() or target_dir.resolve() == backup_dir.resolve():
        return []

    new_df = _read_instruments_df(target_ins)
    old_df = _read_instruments_df(backup_ins).drop_duplicates("symbol", keep="last")
    present = set(new_df["symbol"])
    candidates = old_df.loc[~old_df["symbol"].isin(present)]
    if symbols is not None:
        candidates = candidates.loc[candidates["symbol"].isin(set(symbols))]
    if candidates.empty:
        collector.logger.info("Restauracion desde backup: no falta ningun simbolo")
        return []

    old_calendar = _read_calendar_list(backup_dir)
    new_calendar = _read_calendar_list(target_dir)
    same_prefix = len(old_calendar) <= len(new_calendar) and new_calendar[: len(old_calendar)] == old_calendar
    new_index = None if same_prefix else {d: i for i, d in enumerate(new_calendar)}

    restored, skipped, corrupt = [], [], []
    for row in candidates.itertuples(index=False):
        fname = code_to_fname(row.symbol).lower()
        src = backup_dir / "features" / fname
        dst = target_dir / "features" / fname
        if not src.is_dir() or dst.exists():
            skipped.append(row.symbol)
            continue
        # Un .bin mas largo que su calendario viene del append ciego de DumpDataUpdate
        # (fechas desplazadas): copiarlo propagaria datos corruptos.
        if any(
            int(a[0]) + a.size - 1 > len(old_calendar)
            for a in (np.fromfile(p, dtype="<f4") for p in src.glob("*.bin"))
            if a.size
        ):
            corrupt.append(row.symbol)
            continue
        if same_prefix:
            shutil.copytree(src, dst)
        else:
            remapped = {}
            for bin_path in src.glob("*.bin"):
                out = _remap_bin_to_calendar(np.fromfile(bin_path, dtype="<f4"), old_calendar, new_index)
                if out is None:
                    break
                remapped[bin_path.name] = out
            else:
                dst.mkdir(parents=True)
                for name, out in remapped.items():
                    out.astype("<f4").tofile(dst / name)
            if not dst.exists():
                skipped.append(row.symbol)
                continue
        restored.append((row.symbol, row.start_date, row.end_date))

    if restored:
        with open(target_ins, "a", encoding="utf-8") as fh:
            for symbol, start_date, end_date in restored:
                fh.write(f"{symbol}\t{start_date}\t{end_date}\n")
    collector.logger.warning(
        f"Restauracion desde {backup_dir.name}: {len(restored)} simbolos recuperados, "
        f"{len(skipped)} sin features utilizables en el backup, {len(corrupt)} descartados por .bin "
        f"desalineado ({'copia directa' if same_prefix else 'reubicados en el calendario nuevo'})"
    )
    if corrupt:
        collector.logger.error(f"Backup con .bin desalineados, no restaurados: {sorted(corrupt)[:50]}")
    if skipped:
        collector.logger.warning(f"No restaurados: {sorted(skipped)[:50]}")
    return [s for s, _, _ in restored]


def _check_universe_after_rebuild(target_dir: Path, previous_dir: Path = None) -> list:
    """Compara el universo resultante con el anterior y comprueba los miembros de indices."""
    target_dir = Path(target_dir)
    problems = []
    new_symbols = set(_read_instruments_df(target_dir / "instruments" / "all.txt")["symbol"])
    if previous_dir is not None and (Path(previous_dir) / "instruments" / "all.txt").exists():
        old_symbols = set(_read_instruments_df(Path(previous_dir) / "instruments" / "all.txt")["symbol"])
        lost = old_symbols - new_symbols
        collector.logger.info(
            f"Universo: {len(old_symbols)} antes -> {len(new_symbols)} ahora "
            f"(+{len(new_symbols - old_symbols)} / -{len(lost)})"
        )
        if lost:
            problems.append(f"{len(lost)} simbolos del dataset anterior no estan: {sorted(lost)[:30]}")

    # Los ficheros de indices usan "BRK.B"; Yahoo y features/ usan "brk-b"
    missing_members = sorted(
        s for s in _current_index_members(target_dir)
        if not (target_dir / "features" / code_to_fname(s.replace(".", "-")).lower()).is_dir()
    )
    if missing_members:
        problems.append(f"miembros actuales de sp500/nasdaq100 sin features: {missing_members}")

    for problem in problems:
        collector.logger.error(f"UNIVERSO INCOMPLETO -> {problem}")
    return problems


ADJUST_STATE_FILE = "adjust_state.csv"


def _load_adjust_state(qlib_data_1d_dir: Path) -> dict:
    """symbol -> ultima fecha cuyos ajustes (dividendos/splits) estan en todo su historico.

    El resync enlaza cada ventana con lo ya guardado, asi que un dividendo nuevo no
    reajusta el historico anterior a la ventana. Este estado dice desde cuando un
    simbolo necesita reconstruirse entero. Si falta el fichero, la base es
    QLIB_ADJ_BASELINE o, en su defecto, el ultimo dia del calendario.
    """
    path = Path(qlib_data_1d_dir) / ADJUST_STATE_FILE
    if path.exists():
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return {r.symbol: pd.Timestamp(r.full_as_of) for r in df.itertuples(index=False) if r.symbol}
    baseline = os.environ.get("QLIB_ADJ_BASELINE")
    if not baseline:
        calendar = _read_calendar_list(qlib_data_1d_dir)
        baseline = calendar[-1] if calendar else None
    if not baseline:
        return {}
    collector.logger.warning(f"No existe {ADJUST_STATE_FILE}: se toma {baseline} como base para todos los simbolos")
    symbols = _read_instruments_df(Path(qlib_data_1d_dir) / "instruments" / "all.txt")["symbol"]
    return {s: pd.Timestamp(baseline) for s in symbols}


def _save_adjust_state(qlib_data_1d_dir: Path, state: dict):
    path = Path(qlib_data_1d_dir) / ADJUST_STATE_FILE
    df = pd.DataFrame(
        sorted((s, d.strftime("%Y-%m-%d")) for s, d in state.items()), columns=["symbol", "full_as_of"]
    )
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _symbols_with_new_adjustments(source_dir: Path, state: dict, default_as_of: pd.Timestamp, max_date) -> dict:
    """Simbolos cuya descarga trae un dividendo o split posterior a su full_as_of.

    Devuelve symbol -> fecha del ultimo evento. Yahoo reajusta adjclose de todo el
    historico anterior al evento; enlazar solo la ventana dejaria el resto sin ajustar.
    """
    flagged = {}
    for csv_path in Path(source_dir).glob("*.csv"):
        try:
            df = pd.read_csv(csv_path, usecols=lambda c: c in ("date", "dividends", "splits"))
        except (ValueError, pd.errors.EmptyDataError):
            continue
        if "date" not in df or not ({"dividends", "splits"} & set(df.columns)):
            continue
        event = pd.Series(False, index=df.index)
        for col in ("dividends", "splits"):
            if col in df:
                event |= pd.to_numeric(df[col], errors="coerce").fillna(0) != 0
        if not event.any():
            continue
        dates = _parse_mixed_dates(df.loc[event, "date"]).dt.normalize().dropna()
        if max_date is not None:
            dates = dates[dates <= max_date]
        if dates.empty:
            continue
        symbol = fname_to_code(csv_path.stem.lower()).upper()
        last_event = dates.max()
        if last_event > state.get(symbol, default_as_of):
            flagged[symbol] = last_event
    return flagged


def _should_use_tmp_work_dir(path: Path) -> bool:
    resolved = Path(path).expanduser().resolve()
    return resolved.as_posix().startswith("/mnt/")


def _resolve_work_base_dir() -> Path:
    env_value = os.environ.get("QLIB_US_WORK_DIR") or os.environ.get("QLIB_WORK_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    default_base_dir = Path(__file__).resolve().parent / "data_collector" / "yahoo"
    if _should_use_tmp_work_dir(default_base_dir):
        return Path("/tmp/qlib_us_work")
    return default_base_dir


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
        df = df[~df.index.duplicated(keep="last")]

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
            _write_csv_with_retry(df, self._target_dir.joinpath(file_path.name), index=False)

    collector.Normalize._executor = _executor


def _patch_yahoo_normalize_extend():
    def _get_old_data(self, qlib_data_dir: [str, Path]):
        """Ultimo valor guardado de cada simbolo (y, en el resync, los de la ventana).

        Antes cargaba con D.features el historico completo de todos los simbolos
        (~15.000 x 6.700 dias x 7 campos) para quedarse con la ultima fila: el
        incremental del 2026-10-16 murio por OOM (Killed) en este paso. Ahora lee de
        cada .bin solo lo necesario con memmap.
        """
        qlib_data_dir = Path(qlib_data_dir).expanduser().resolve()
        calendar = pd.DatetimeIndex(pd.to_datetime(_read_calendar_list(qlib_data_dir)))
        rewrite_from = os.environ.get("US_ALL_REWRITE_FROM")
        window_pos = int(calendar.searchsorted(pd.Timestamp(rewrite_from))) if rewrite_from else None
        self.old_qlib_window = {}
        rows = {}
        for symbol in _read_instruments_df(qlib_data_dir / "instruments" / "all.txt")["symbol"]:
            fdir = qlib_data_dir / "features" / code_to_fname(symbol).lower()
            close_path = fdir / "close.day.bin"
            if not close_path.exists():
                continue
            close = np.memmap(close_path, dtype="<f4", mode="r")
            if close.size < 2:
                continue
            start = int(close[0])
            valid = np.flatnonzero(~np.isnan(close[1:]))
            if valid.size == 0:
                continue
            last = int(valid[-1])
            if start + last >= len(calendar):
                continue
            last_pos = start + last  # posicion en el calendario del ultimo cierre valido
            columns = {}
            for col in self.column_list:
                path = fdir / f"{col}.day.bin"
                columns[col] = np.memmap(path, dtype="<f4", mode="r") if path.exists() else None

            def _slice(arr, lo_pos, hi_pos):
                """Valores de arr para las posiciones de calendario [lo_pos, hi_pos]."""
                out = np.full(hi_pos - lo_pos + 1, np.nan)
                if arr is None or arr.size < 2:
                    return out
                a_start = int(arr[0])
                a_lo, a_hi = max(lo_pos, a_start), min(hi_pos, a_start + arr.size - 2)
                if a_lo <= a_hi:
                    out[a_lo - lo_pos : a_hi - lo_pos + 1] = arr[1 + a_lo - a_start : 2 + a_hi - a_start]
                return out

            key = str(symbol).upper()
            rows[key] = [calendar[last_pos]] + [float(_slice(arr, last_pos, last_pos)[0]) for arr in columns.values()]
            if window_pos is not None and last_pos >= window_pos:
                lo_pos = max(window_pos, start)
                frame = pd.DataFrame(
                    {col: _slice(arr, lo_pos, last_pos) for col, arr in columns.items()},
                    index=calendar[lo_pos : last_pos + 1],
                )
                frame = frame[frame["close"].notna()]
                if not frame.empty:
                    self.old_qlib_window[key] = frame
        if not rows:
            return pd.DataFrame(columns=["latest_date", *self.column_list])
        latest_df = pd.DataFrame.from_dict(rows, orient="index", columns=["latest_date", *self.column_list])
        latest_df.index.name = "instrument"
        return latest_df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = collector.YahooNormalize1d.normalize(self, df)
        df.set_index(self._date_field_name, inplace=True)
        symbol_name = str(df[self._symbol_field_name].iloc[0]).upper()
        if symbol_name not in self.old_qlib_data.index:
            return df.reset_index()

        rewrite_from = os.environ.get("US_ALL_REWRITE_FROM")
        old_window = getattr(self, "old_qlib_window", {}).get(symbol_name) if rewrite_from else None
        if old_window is not None:
            window = df.loc[pd.Timestamp(rewrite_from) :]
            common = [d for d in window.index[window["close"].notna()] if d in old_window.index]
            if common:
                df = window.copy()
                # Ancla = primer dia de la ventana con dato en ambos lados. Se escala la
                # ventana entera para que coincida ahi y se devuelve completa (el resync
                # la reescribe), ancla incluida.
                anchor = common[0]
                for col in self.column_list[:-1]:
                    new_v, old_v = df.at[anchor, col], old_window.at[anchor, col]
                    if pd.isna(new_v) or pd.isna(old_v) or new_v == 0:
                        continue
                    df[col] = df[col] * (old_v / new_v)
                return df.reset_index()
            # sin dia comun: se enlaza con el ultimo dato guardado, como en el incremental

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        }
        response = us_index_collector.requests.get(self.WIKISP500_CHANGES_URL, headers=headers, timeout=60)
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
            us_index_collector.logger.warning(
                "SP500: tabla de cambios no encontrada en Wikipedia; "
                "se genera solo la composicion actual (sin historico de altas/bajas)."
            )
            return us_index_collector.pd.DataFrame(
                columns=[self.DATE_FIELD_NAME, self.CHANGE_TYPE_FIELD, self.SYMBOL_FIELD_NAME]
            )

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
# _patch_sp500_changes_parser()  # Opcion B: se usa SP500Index.get_changes (dataset historico) de collector.py


class USAllCollector(YahooCollectorUS1d):
    """Universo US = fuente externa fresca (NASDAQ Trader/NYSE) union historico local.

    La implementacion anterior leia unicamente instruments/all.txt y lo filtraba por
    fecha, de modo que el universo solo podia encogerse: nunca incorporaba altas nuevas
    ni recuperaba simbolos podados por error. Ahora se parte del universo real que
    devuelve YahooCollectorUS.get_instrument_list() y se le suma el historico local para
    conservar las fechas point-in-time de las bajas ya registradas.
    """

    @staticmethod
    def _read_historical_symbols(ins_path: Path) -> set:
        """Simbolos ya presentes en instruments/all.txt (los que tienen datos)."""
        if not ins_path.exists():
            return set()
        # keep_default_na=False: "NA" (Nano Labs) es un ticker real, no un nulo
        df = pd.read_csv(
            ins_path, sep="\t", names=["symbol", "start_date", "end_date"], keep_default_na=False
        )
        return {s for s in df["symbol"].unique().tolist() if s}

    def get_instrument_list(self):
        data_dir = os.environ.get("US_ALL_INSTRUMENTS_SOURCE_DIR") or os.environ.get("US_ALL_INSTRUMENTS_DATA_DIR") or os.environ.get(
            "DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data")
        )
        ins_path = Path(data_dir) / "instruments" / "all.txt"

        # US_ALL_SYMBOLS_FILE: lista explicita (un simbolo por linea). La usan los
        # reintentos de descargas fallidas y scripts/recover_lost_symbols.py.
        symbols_file = os.environ.get("US_ALL_SYMBOLS_FILE")
        if symbols_file:
            forced = [s.strip() for s in Path(symbols_file).read_text().splitlines() if s.strip()]
            print(f"Universo (lista forzada): {len(forced)} simbolos de {symbols_file}")
            return sorted(set(forced))

        # US_ALL_UNIVERSE_MODE=known: solo los simbolos activos que ya tienen datos. Evita
        # reintentar cada dia los ~4.600 que la fuente lista pero Yahoo no sirve, y
        # ahorra ademas la consulta a la fuente externa (~13 min). Las altas nuevas
        # entran en el resync semanal, que corre en modo "full". Se excluyen los que
        # llevan mas de US_ALL_KNOWN_ACTIVE_DAYS sin dato: all.txt conserva los delistados
        # (ver _restore_missing_from_backup) y pedirlos cada noche solo cuesta tiempo.
        universe_mode = os.environ.get("US_ALL_UNIVERSE_MODE", "full").strip().lower()
        if universe_mode == "known":
            active_days = int(os.environ.get("US_ALL_KNOWN_ACTIVE_DAYS", "30"))
            known = _active_symbols(Path(data_dir), days=active_days)
            if known:
                print(
                    f"Universo (modo known): {len(known)} simbolos con dato en los ultimos "
                    f"{active_days} dias en {ins_path.name}"
                )
                return sorted(known)
            print(f"Modo known sin historico utilizable en {ins_path}; se usa el universo completo.")

        print("Obteniendo lista de simbolos US_ALL (fuente externa + historico local)...")
        fresh_symbols = set(super().get_instrument_list())

        historical_symbols = self._read_historical_symbols(ins_path)
        if not ins_path.exists():
            print(f"Aviso: no existe {ins_path}; se usa solo el universo de la fuente externa.")

        combined = fresh_symbols | historical_symbols
        print(
            f"Universo: {len(fresh_symbols)} de fuente actual + {len(historical_symbols)} historicos "
            f"= {len(combined)} total"
        )
        if not combined:
            raise RuntimeError(
                "El universo US quedo vacio: la fuente externa no devolvio simbolos y no hay "
                f"historico en {ins_path}."
            )
        return sorted(combined)


collector.USAllCollector = USAllCollector


class USAllRun(Run):
    def __init__(self, source_dir=None, normalize_dir=None, max_workers=1, interval="1d", region="us"):
        work_base_dir = _resolve_work_base_dir()
        using_tmp_work_dir = _should_use_tmp_work_dir(Path(__file__).resolve().parent / "data_collector" / "yahoo")

        if source_dir is None:
            source_dir = work_base_dir / "source"
        if normalize_dir is None:
            normalize_dir = work_base_dir / "normalize"

        super().__init__(source_dir=source_dir, normalize_dir=normalize_dir, max_workers=max_workers, interval=interval, region=region)

        if using_tmp_work_dir:
            collector.logger.info(
                f"Using temporary work directories outside /mnt for Yahoo source/normalize data: {work_base_dir}"
            )

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

    def _retry_missing_downloads(self, expected_symbols, start: str, end: str, delay: float = 1) -> list:
        """Vuelve a pedir los simbolos esperados que no dejaron CSV en source_dir.

        get_data_from_remote se traga los errores de red y los trata como "may be
        delisted" (2 intentos en ~30 s). Un corte de Yahoo de un minuto bastaba para
        perder un simbolo vivo en un clean rebuild (ABT, 2026-10-16). Aqui se reintenta
        por rondas, con esperas crecientes, mientras cada ronda recupere algo.
        Devuelve los simbolos que siguen sin datos.
        """
        waits = [
            int(w) for w in os.environ.get("QLIB_MISSING_RETRY_WAITS", "60,300,900").split(",") if w.strip()
        ]
        missing = sorted(s for s in expected_symbols if not (self.source_dir / _source_file_name(s)).exists())
        if not missing:
            return []
        collector.logger.warning(f"{len(missing)} simbolos esperados sin datos tras la descarga: {missing[:30]}")

        symbols_file = self.source_dir.parent / "retry_symbols.txt"
        previous = os.environ.get("US_ALL_SYMBOLS_FILE")
        try:
            for round_no, wait in enumerate(waits, start=1):
                collector.logger.info(f"Reintento {round_no}/{len(waits)} en {wait}s para {len(missing)} simbolos")
                time.sleep(wait)
                symbols_file.write_text("\n".join(missing) + "\n")
                os.environ["US_ALL_SYMBOLS_FILE"] = str(symbols_file)
                self.download_data(delay=max(delay, 1), start=start, end=end)
                still = [s for s in missing if not (self.source_dir / _source_file_name(s)).exists()]
                collector.logger.info(f"Reintento {round_no}: recuperados {len(missing) - len(still)}, faltan {len(still)}")
                if len(still) == len(missing):
                    break
                missing = still
                if not missing:
                    break
        finally:
            if previous is None:
                os.environ.pop("US_ALL_SYMBOLS_FILE", None)
            else:
                os.environ["US_ALL_SYMBOLS_FILE"] = previous
            symbols_file.unlink(missing_ok=True)

        if missing:
            collector.logger.warning(f"Siguen sin datos tras los reintentos ({len(missing)}): {missing[:50]}")
        return missing

    def update_data_to_bin(
        self,
        qlib_data_1d_dir: str,
        trading_date: str = None,
        end_date: str = None,
        check_data_length: int = None,
        delay: float = 1,
        exists_skip: bool = False,
        rewrite_window: bool = False,
    ):
        """rewrite_window=True (resync semanal): reescribe todas las fechas >= trading_date
        y reconstruye entero cualquier simbolo con un dividendo/split nuevo o que no
        estuviera en el dataset (ver _rebuild_full_history)."""
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
        collector.logger.info(f"Incremental effective date={effective_date_str}")

        # Directorios de trabajo limpios: save_instrument concatena con el CSV que ya
        # exista, asi que sin esto se acumulaban las descargas de todas las noches (y los
        # historicos completos del ultimo rebuild): ~88 M filas que normalizar y cargar.
        for work_dir in (self.source_dir, self.normalize_dir):
            if work_dir.exists():
                shutil.rmtree(work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)

        self.download_data(delay=delay, start=trading_date, end=end_date, check_data_length=check_data_length)
        # Solo los miembros de indices: el resto de huecos de un dia los cubre el resync
        # del sabado, y reintentar ~900 simbolos sin barra cada noche costaria horas.
        # Solo los que ya existen: un simbolo nuevo creado con una ventana de 2 dias se
        # quedaria sin historico (DumpDataUpdate no rellena hacia atras); esos van por
        # scripts/recover_lost_symbols.py o el resync.
        known = set(_read_instruments_df(Path(qlib_data_1d_dir) / "instruments" / "all.txt")["symbol"])
        index_members = {s.replace(".", "-") for s in _current_index_members(Path(qlib_data_1d_dir))} & known
        self._retry_missing_downloads(index_members, start=trading_date, end=end_date, delay=delay)
        normalize_workers = self._resolve_normalize_workers()
        collector.logger.info(f"Using max_workers={normalize_workers} for incremental normalization")
        original_max_workers = self.max_workers
        self.max_workers = normalize_workers
        if rewrite_window:
            os.environ["US_ALL_REWRITE_FROM"] = trading_date
            collector.logger.info(f"Resync: se reescriben todas las fechas >= {trading_date}")
        try:
            self.normalize_data_1d_extend(qlib_data_1d_dir)
        finally:
            os.environ.pop("US_ALL_REWRITE_FROM", None)
        max_date = _last_closed_session_date()
        _sanitize_normalize_dir(Path(self.normalize_dir), max_date=max_date)
        dump_workers = self._resolve_dump_workers()
        collector.logger.info(f"Using max_workers={dump_workers} for incremental bin dump")
        self.max_workers = dump_workers

        if not any(
            sum(1 for _ in open(f)) > 1 for f in Path(self.normalize_dir).glob("*.csv")
        ):
            # Sin sesiones nuevas (festivo, o ya volcado): DumpDataUpdate falla con
            # "No objects to concatenate" si no hay ninguna fila que volcar.
            collector.logger.warning("No hay filas nuevas que volcar; el dataset no cambia")
            self.max_workers = original_max_workers
            _check_recent_coverage(Path(qlib_data_1d_dir))
            return

        if rewrite_window:
            adjust_state = _load_adjust_state(Path(qlib_data_1d_dir))
        collector.DumpDataUpdate(
            data_path=self.normalize_dir,
            qlib_dir=qlib_data_1d_dir,
            exclude_fields="symbol,date",
            max_workers=dump_workers,
            rewrite_from=trading_date if rewrite_window else None,
        ).dump()

        if rewrite_window:
            default_as_of = pd.Timestamp(os.environ.get("QLIB_ADJ_BASELINE") or trading_date)
            flagged = _symbols_with_new_adjustments(self.source_dir, adjust_state, default_as_of, max_date)
            new_symbols = {
                fname_to_code(p.stem.lower()).upper() for p in Path(self.normalize_dir).glob("*.csv")
            } - set(adjust_state)
            collector.logger.info(
                f"Resync: {len(flagged)} simbolos con dividendo/split nuevo y {len(new_symbols)} nuevos "
                "en el dataset -> reconstruccion de su historico completo"
            )
            # QLIB_RESYNC_FULL_ON_ADJUST=0 desactiva la reconstruccion por dividendo/split
            # (los simbolos nuevos se reconstruyen siempre). Con la normalizacion por el
            # primer cierre, un dividendo nuevo no cambia los valores anteriores a la
            # ventana y el enlace ya reproduce un rebuild (verificado el 2026-10-19 con
            # JEPI, O, KO y AAPL: diferencias <= 2e-6); la reconstruccion es una red de
            # seguridad frente a revisiones de Yahoo, a costa de 1-2 h por semana.
            if os.environ.get("QLIB_RESYNC_FULL_ON_ADJUST", "1") == "0":
                collector.logger.info("Resync: reconstruccion por ajustes desactivada (QLIB_RESYNC_FULL_ON_ADJUST=0)")
                flagged = {}
            rebuilt = self._rebuild_full_history(
                Path(qlib_data_1d_dir), sorted(set(flagged) | new_symbols), end=end_date, delay=delay
            )
            calendar_last = pd.Timestamp(_read_calendar_list(Path(qlib_data_1d_dir))[-1])
            for symbol in set(_read_instruments_df(Path(qlib_data_1d_dir) / "instruments" / "all.txt")["symbol"]):
                adjust_state.setdefault(symbol, default_as_of)
            for symbol in rebuilt:
                adjust_state[symbol] = calendar_last
            _save_adjust_state(Path(qlib_data_1d_dir), adjust_state)
            pending = sorted(set(flagged) - set(rebuilt))
            if pending:
                collector.logger.warning(
                    f"Resync: {len(pending)} simbolos con ajuste nuevo sin reconstruir (se reintentan el "
                    f"proximo sabado): {pending[:50]}"
                )
        self.max_workers = original_max_workers

        self._refresh_us_indexes(qlib_data_1d_dir)
        _check_recent_coverage(Path(qlib_data_1d_dir))

    def _rebuild_full_history(self, qlib_data_1d_dir: Path, symbols, end: str, delay: float = 1) -> list:
        """Descarga desde REBUILD_START_DATE y sustituye entero el historico de `symbols`.

        Mismo calculo que un clean rebuild (YahooNormalize1d, normalizado por el primer
        cierre), pero solo para estos simbolos. Solo se sustituye un simbolo si la
        descarga completa llega al menos hasta su end_date actual; si no, se queda con
        la ventana enlazada y su estado no avanza (se reintenta la semana siguiente).
        """
        if not symbols:
            return []
        work = self.source_dir.parent / "full_history"
        for sub in ("source", "normalize", "batches"):
            if (work / sub).exists():
                shutil.rmtree(work / sub)
            (work / sub).mkdir(parents=True)
        start = os.environ.get("REBUILD_START_DATE", "1999-12-31")
        runner = USAllRun(source_dir=work / "source", normalize_dir=work / "normalize", max_workers=self.max_workers)
        symbols_file = work / "symbols.txt"
        symbols_file.write_text("\n".join(symbols) + "\n")
        previous = os.environ.get("US_ALL_SYMBOLS_FILE")
        os.environ["US_ALL_SYMBOLS_FILE"] = str(symbols_file)
        try:
            runner.download_data(delay=delay, start=start, end=end)
        finally:
            if previous is None:
                os.environ.pop("US_ALL_SYMBOLS_FILE", None)
            else:
                os.environ["US_ALL_SYMBOLS_FILE"] = previous
        runner.max_workers = self._resolve_normalize_workers()
        runner.normalize_data(end_date=end)
        calendar_last = pd.Timestamp(_read_calendar_list(qlib_data_1d_dir)[-1])
        _sanitize_normalize_dir(work / "normalize", max_date=calendar_last)

        current = _read_instruments_df(qlib_data_1d_dir / "instruments" / "all.txt").set_index("symbol")
        accepted = []
        batch_size = int(os.environ.get("QLIB_FULL_HISTORY_BATCH", "300"))
        for csv_path in sorted((work / "normalize").glob("*.csv")):
            symbol = fname_to_code(csv_path.stem.lower()).upper()
            dates = pd.to_datetime(pd.read_csv(csv_path, usecols=["date"])["date"], errors="coerce").dropna()
            current_end = pd.Timestamp(current.at[symbol, "end_date"]) if symbol in current.index else None
            if dates.empty or (current_end is not None and dates.max() < current_end):
                csv_path.unlink()
                continue
            batch_dir = work / "batches" / f"{len(accepted) // batch_size:04d}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(csv_path), str(batch_dir / csv_path.name))
            accepted.append(symbol)
        # Por lotes: DumpDataUpdate carga en memoria todo lo que hay en data_path y un
        # historico completo son ~6.700 filas por simbolo.
        for batch_dir in sorted((work / "batches").glob("*")) if accepted else []:
            collector.DumpDataUpdate(
                data_path=batch_dir,
                qlib_dir=str(qlib_data_1d_dir),
                exclude_fields="symbol,date",
                max_workers=self._resolve_dump_workers(),
                full_replace=True,
            ).dump()
        collector.logger.info(
            f"Historico completo reconstruido para {len(accepted)} de {len(symbols)} simbolos"
        )
        return sorted(accepted)

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
        universe_matches_target = universe_dir == qlib_data_1d_dir if universe_dir is not None else False
        backup_dir = None

        if backup_existing and qlib_data_1d_dir.exists():
            suffix = backup_suffix or pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = qlib_data_1d_dir.parent / f"{qlib_data_1d_dir.name}_backup_{suffix}"
            if backup_dir.exists():
                raise FileExistsError(f"Backup dir already exists: {backup_dir}")
            shutil.move(str(qlib_data_1d_dir), str(backup_dir))
            collector.logger.warning(f"Existing dataset moved to backup: {backup_dir}")
            if universe_matches_target:
                universe_dir = backup_dir

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

        self.download_data(delay=delay, start=start_date, end=end_date)
        expected = _active_symbols(universe_dir) | {
            s.replace(".", "-") for s in _current_index_members(universe_dir)
        }
        self._retry_missing_downloads(expected, start=start_date, end=end_date, delay=delay)
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
        _sanitize_normalize_dir(Path(self.normalize_dir))
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

        # all.txt solo crece: lo que estaba en el dataset anterior y Yahoo no ha devuelto
        # (delistados, fallos transitorios) se conserva con su historico y su end_date.
        if universe_dir != qlib_data_1d_dir:
            _restore_missing_from_backup(qlib_data_1d_dir, universe_dir)

        # Tras un clean rebuild todo el historico esta ajustado hasta el ultimo dia
        calendar_last = pd.Timestamp(_read_calendar_list(qlib_data_1d_dir)[-1])
        _save_adjust_state(
            qlib_data_1d_dir,
            {s: calendar_last for s in _read_instruments_df(instruments_path)["symbol"]},
        )

        self._refresh_us_indexes(str(qlib_data_1d_dir))
        _check_recent_coverage(Path(qlib_data_1d_dir))
        _check_universe_after_rebuild(
            qlib_data_1d_dir, universe_dir if universe_dir != qlib_data_1d_dir else None
        )


if __name__ == "__main__":
    fire.Fire(USAllRun)
