"""
dump_coingecko_to_qlib.py — Actualiza Qlib binario con datos incrementales de CoinGecko.

Lee los CSVs descargados por download_crypto_coingecko.py (scripts/crypto/csv_data/crypto_coingecko/ohlcv/)
y AÑADE solo los días nuevos al dataset Qlib existente (data/qlib/).

NO regenera todo desde cero — solo añade los días que faltan.

Uso:
  conda run -n qlib python work/crypto/dump_coingecko_to_qlib.py
"""

import struct
from pathlib import Path
from datetime import datetime, date
import numpy as np
import pandas as pd

CSV_DIR = Path("scripts/crypto/csv_data/crypto_coingecko/ohlcv")
QLIB_DIR = Path("data/qlib")
FEATURES_DIR = QLIB_DIR / "features"
CALENDARS_DIR = QLIB_DIR / "calendars"
INSTRUMENTS_DIR = QLIB_DIR / "instruments"

FIELDS_F32 = ["open", "high", "low", "close", "volume", "adjclose"]
FIELDS_F64 = ["factor"]


def read_bin_float32(filepath):
    """Lee un .day.bin y devuelve lista de valores float32."""
    if not filepath.exists():
        return []
    with open(filepath, "rb") as f:
        data = f.read()
    n = struct.unpack("<i", data[:4])[0]
    values = []
    for i in range(n):
        offset = 4 + i * 4
        val = struct.unpack("<f", data[offset:offset+4])[0]
        values.append(val)
    return values


def read_bin_float64(filepath):
    """Para factor (float64)."""
    if not filepath.exists():
        return []
    with open(filepath, "rb") as f:
        data = f.read()
    n = struct.unpack("<i", data[:4])[0]
    values = []
    for i in range(n):
        offset = 4 + i * 8
        val = struct.unpack("<d", data[offset:offset+8])[0]
        values.append(val)
    return values


def write_bin_float32(filepath, values):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<i", len(values)))
        for val in values:
            f.write(struct.pack("<f", float(val)))


def write_bin_float64(filepath, values):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<i", len(values)))
        for val in values:
            f.write(struct.pack("<d", float(val)))


def read_calendar():
    cal_path = CALENDARS_DIR / "day.txt"
    if not cal_path.exists():
        return []
    with open(cal_path) as f:
        return [line.strip() for line in f if line.strip()]


def write_calendar(dates):
    CALENDARS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CALENDARS_DIR / "day.txt", "w") as f:
        for d in dates:
            f.write(d + "\n")


def main():
    print(f"\n{'='*55}")
    print("🔄 Actualización incremental Qlib desde CoinGecko")
    print(f"{'='*55}")

    if not CSV_DIR.exists():
        print(f"❌ No existe: {CSV_DIR}")
        print(f"   Ejecuta primero: download_crypto_coingecko.py")
        return

    csv_files = sorted(CSV_DIR.glob("*.csv"))
    if not csv_files:
        print(f"❌ No hay CSVs en {CSV_DIR}")
        return

    # Calendario actual
    calendar = read_calendar()
    if not calendar:
        print("❌ No hay calendario en data/qlib/. Ejecuta primero dump completo.")
        return

    existing_dates = set(calendar)
    print(f"   📅 Calendario actual: {len(calendar)} días")
    print(f"      {calendar[0]} → {calendar[-1]}")

    total_new = 0
    symbols_updated = []

    for csv_path in csv_files:
        symbol = csv_path.stem.lower()
        print(f"   {symbol:>5s}...", end=" ")

        df = pd.read_csv(csv_path, parse_dates=["date"])
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
        df = df.sort_values("date").drop_duplicates(subset="date")

        # Fechas nuevas que no están en el calendario
        new_dates = [d for d in df["date"].dt.date.values if d.isoformat() not in existing_dates]
        if not new_dates:
            print(f"✅ actualizado (sin días nuevos)")
            continue

        # Leer binarios existentes
        for field in FIELDS_F32:
            bin_path = FEATURES_DIR / symbol / f"{field}.day.bin"
            existing_vals = read_bin_float32(bin_path)

            # Añadir valores de los días nuevos
            for nd in new_dates:
                mask = df["date"].dt.date == nd
                if mask.any():
                    val = df.loc[mask, field].values[0]
                else:
                    val = 0.0
                existing_vals.append(float(val))

            write_bin_float32(bin_path, existing_vals)

        for field in FIELDS_F64:
            bin_path = FEATURES_DIR / symbol / f"{field}.day.bin"
            existing_vals = read_bin_float64(bin_path)
            for nd in new_dates:
                mask = df["date"].dt.date == nd
                if mask.any() and field in df.columns:
                    val = df.loc[mask, field].values[0]
                else:
                    val = 1.0 if field == "factor" else 0.0
                existing_vals.append(float(val))
            write_bin_float64(bin_path, existing_vals)

        # Actualizar instrumentos
        first = new_dates[0].isoformat()
        last = new_dates[-1].isoformat()
        inst_path = INSTRUMENTS_DIR / "all.txt"
        crypto_path = INSTRUMENTS_DIR / "crypto.txt"
        for fpath in [inst_path, crypto_path]:
            if fpath.exists():
                lines = fpath.read_text().splitlines()
                found = False
                for i, line in enumerate(lines):
                    parts = line.split("\t")
                    if parts[0] == symbol:
                        # Actualizar última fecha
                        parts[2] = last
                        lines[i] = "\t".join(parts)
                        found = True
                        break
                if not found:
                    lines.append(f"{symbol}\t{first}\t{last}")
                fpath.write_text("\n".join(lines) + "\n")

        total_new += len(new_dates)
        symbols_updated.append(symbol)
        print(f"✅ +{len(new_dates)} días [{new_dates[0]} → {new_dates[-1]}]")

    # Actualizar calendario global
    if total_new > 0:
        all_dates = sorted(set(calendar).union(
            d.isoformat() for d in df["date"].dt.date.values
        ))
        write_calendar(all_dates)
        print(f"\n   📅 Calendario actualizado: {len(all_dates)} días (+{total_new})")

    print(f"\n{'='*55}")
    print(f"✅ Completado: {len(symbols_updated)} criptos actualizados, {total_new} días nuevos")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()