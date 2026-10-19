"""Recupera los simbolos que un clean rebuild dejo fuera del dataset US (Fallo 6).

Fase A: vuelve a pedir a Yahoo, con el historico completo, los simbolos perdidos que
        seguian activos (end_date >= --download_since) y los miembros actuales de
        sp500/nasdaq100 sin features. Los que devuelven datos siguen cotizando y se
        vuelcan con DumpDataUpdate como simbolos nuevos.
Fase B: el resto (delistados que Yahoo ya no sirve) se copia desde --restore_dir con su
        historico y su end_date original (_restore_missing_from_backup). Debe ser un
        backup sin .bin desalineados: los de 2026-10-13 y 2026-10-16 tienen ~216 valores
        de mas por el append ciego de DumpDataUpdate; el de 2026-09-12 esta limpio.

Por defecto es un dry-run: descarga a un directorio de trabajo e informa, sin tocar el
dataset. Con --apply escribe. Lanzar con el lock del pipeline:

    /usr/bin/flock -n /tmp/qlib_us_pipeline.lock python scripts/recover_lost_symbols.py \\
        --backup_dirs /opt/qlib_home/qlib_data/us_data_backup_20261016_220705,/opt/qlib_home/qlib_data/us_data_backup_20260912_010103 \\
        --restore_dir /opt/qlib_home/qlib_data/us_data_backup_20260912_010103 --apply
"""

import os
import shutil
import sys
from pathlib import Path

import fire
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_us_all as uua  # noqa: E402

logger = uua.collector.logger


def main(
    backup_dirs,
    restore_dir: str,
    target_dir: str = "~/.qlib/qlib_data/us_data",
    work_dir: str = "/opt/qlib_work/recover",
    download_since: str = "2026-09-01",
    start_date: str = "1999-12-31",
    delay: float = 1,
    min_rows: int = 20,
    apply: bool = False,
):
    target = Path(target_dir).expanduser().resolve()
    if isinstance(backup_dirs, str):
        backup_dirs = backup_dirs.split(",")
    backups = [Path(b).expanduser().resolve() for b in backup_dirs]
    restore = Path(restore_dir).expanduser().resolve()
    work = Path(work_dir).expanduser().resolve()

    new_df = uua._read_instruments_df(target / "instruments" / "all.txt")
    old_df = pd.concat([uua._read_instruments_df(b / "instruments" / "all.txt") for b in backups])
    old_df = old_df.sort_values("end_date").drop_duplicates("symbol", keep="last")
    lost_df = old_df.loc[~old_df["symbol"].isin(set(new_df["symbol"]))]
    lost = set(lost_df["symbol"])
    missing_members = {
        s.replace(".", "-")
        for s in uua._current_index_members(target)
        if not (target / "features" / uua.code_to_fname(s.replace(".", "-")).lower()).is_dir()
    }
    recent = set(lost_df.loc[pd.to_datetime(lost_df["end_date"], errors="coerce") >= pd.Timestamp(download_since), "symbol"])
    to_download = sorted(recent | missing_members)
    logger.info(
        f"Perdidos respecto al backup: {len(lost)}; activos desde {download_since}: {len(recent)}; "
        f"miembros de indices sin features: {sorted(missing_members)}"
    )

    # --- Fase A: descarga ---
    for sub in ("source", "normalize"):
        if (work / sub).exists():
            shutil.rmtree(work / sub)
        (work / sub).mkdir(parents=True)
    run = uua.USAllRun(source_dir=work / "source", normalize_dir=work / "normalize", max_workers=4)
    end_date = pd.Timestamp.today().strftime("%Y-%m-%d")
    symbols_file = work / "symbols.txt"
    symbols_file.write_text("\n".join(to_download) + "\n")
    os.environ["US_ALL_SYMBOLS_FILE"] = str(symbols_file)
    try:
        run.download_data(delay=delay, start=start_date, end=end_date)
    finally:
        os.environ.pop("US_ALL_SYMBOLS_FILE", None)
    os.environ.setdefault("QLIB_MISSING_RETRY_WAITS", "30,120")
    still_missing = set(run._retry_missing_downloads(to_download, start=start_date, end=end_date, delay=delay))
    # Normalizar siempre (en el directorio de trabajo): Yahoo devuelve 1 sola fila para
    # muchos warrants/derechos muertos y eso no es historico. Solo cuenta como
    # recuperado lo que sobrevive a la normalizacion con un minimo de sesiones.
    run.max_workers = 4
    run.normalize_data(end_date=end_date)
    last_calendar_day = pd.Timestamp(uua._read_calendar_list(target)[-1])
    uua._sanitize_normalize_dir(work / "normalize", max_date=last_calendar_day)
    downloaded = []
    for csv_path in (work / "normalize").glob("*.csv"):
        rows = len(pd.read_csv(csv_path, usecols=["date"]))
        symbol = csv_path.stem.upper()
        if rows >= min_rows:
            downloaded.append(symbol)
        else:
            csv_path.unlink()
    downloaded = sorted(downloaded)
    logger.info(
        f"Fase A: {len(downloaded)} de {len(to_download)} con >= {min_rows} sesiones en Yahoo: {downloaded[:60]}"
    )

    from_backup = sorted(lost - set(downloaded))
    restorable = set(uua._read_instruments_df(restore / "instruments" / "all.txt")["symbol"])
    logger.info(
        f"Fase B: {len(from_backup)} pendientes; {len(set(from_backup) & restorable)} estan en {restore.name}, "
        f"{len(set(from_backup) - restorable)} no (altas posteriores sin datos en Yahoo)"
    )

    if not apply:
        logger.warning("Dry-run: no se ha modificado el dataset. Repetir con --apply para escribir.")
        return

    # --- Escritura ---
    if downloaded:
        uua.collector.DumpDataUpdate(
            data_path=work / "normalize",
            qlib_dir=str(target),
            exclude_fields="symbol,date",
            max_workers=4,
        ).dump()
    uua._restore_missing_from_backup(target, restore, symbols=from_backup)

    uua._check_recent_coverage(target, lookback=25)
    problems = uua._check_universe_after_rebuild(target, restore)
    logger.info(f"Recuperacion terminada. Problemas pendientes: {len(problems)}")


if __name__ == "__main__":
    fire.Fire(main)
