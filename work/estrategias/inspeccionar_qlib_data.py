"""inspeccionar_qlib_data.py — Qué hay realmente en el directorio de datos.

Ejecutar en WSL:  python3 inspeccionar_qlib_data.py

No necesita qlib instalado. No llama a la API. Solo lee el sistema de archivos
y te dice qué instrumentos, calendarios y features existen de verdad, para que
el backtest use los nombres correctos en vez de asumirlos.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def find_qlib_dir() -> Path | None:
    cands = [
        os.environ.get("QLIB_US_DATA"),
        str(Path.home() / ".qlib/qlib_data/us_data"),
        "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data",
    ]
    for c in cands:
        if c and Path(c).is_dir():
            return Path(c)
    return None


def size_of(path: Path) -> str:
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        for unit in ("B", "KB", "MB", "GB"):
            if total < 1024:
                return f"{total:.1f} {unit}"
            total /= 1024
        return f"{total:.1f} TB"
    except Exception:
        return "?"


def main() -> int:
    print("=" * 72)
    print(" INSPECCION DEL DIRECTORIO qlib_data")
    print("=" * 72)

    d = find_qlib_dir()
    if d is None:
        print("\nNo encuentro qlib_data en ninguna ruta conocida:")
        for c in [os.environ.get("QLIB_US_DATA"),
                  str(Path.home() / ".qlib/qlib_data/us_data"),
                  "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"]:
            print(f"   - {c}")
        print(f"\nHOME = {Path.home()}")
        print("\nContenido de ~/.qlib si existe:")
        q = Path.home() / ".qlib"
        if q.is_dir():
            for p in sorted(q.rglob("*"))[:40]:
                print(f"   {p}")
        else:
            print("   (no existe)")
        return 1

    print(f"\nEncontrado: {d}")
    print(f"Tamano total: {size_of(d)}")

    # --- Estructura ---
    print("\n" + "-" * 72)
    print(" ESTRUCTURA")
    print("-" * 72)
    for sub in ("instruments", "features", "calendars"):
        p = d / sub
        if p.is_dir():
            print(f"  OK   {sub}/")
        else:
            print(f"  FALTA {sub}/")

    # --- Instrumentos ---
    print("\n" + "-" * 72)
    print(" INSTRUMENTOS (.txt)")
    print("-" * 72)
    inst_dir = d / "instruments"
    if inst_dir.is_dir():
        txts = sorted(p for p in inst_dir.glob("*.txt"))
        if not txts:
            print("  (no hay ningun .txt)")
        for p in txts:
            try:
                n = sum(1 for _ in p.open())
            except Exception:
                n = -1
            marker = "  <-- el que espera el proyecto" if p.name == "sp500_liquid.txt" else ""
            print(f"  {p.name:<28} {n:>6} lineas{marker}")
            try:
                first = p.read_text().splitlines()[:3]
                print(f"      primeras lineas: {first}")
            except Exception:
                pass
    else:
        print("  (no existe instruments/)")

    # --- Calendarios ---
    print("\n" + "-" * 72)
    print(" CALENDARIOS")
    print("-" * 72)
    cal_dir = d / "calendars"
    if cal_dir.is_dir():
        for p in sorted(cal_dir.iterdir()):
            print(f"  {p.name}")
    else:
        print("  (no existe calendars/)")

    # --- Features: cuantos tickers y rango de fechas ---
    print("\n" + "-" * 72)
    print(" FEATURES (muestra)")
    print("-" * 72)
    feat_dir = d / "features"
    if feat_dir.is_dir():
        entries = sorted(p for p in feat_dir.iterdir() if p.is_dir())
        print(f"  tickers con features: {len(entries)}")
        for p in entries[:5]:
            print(f"    {p.name}")
        if len(entries) > 5:
            print(f"    ... y {len(entries) - 5} mas")

        # Inspeccionar el primer ticker: campos disponibles
        if entries:
            sub = sorted(entries[0].iterdir())
            print(f"\n  campos del ticker '{entries[0].name}':")
            for p in sub[:12]:
                print(f"    {p.name}")
            # Rango de fechas del calendario
            cal = d / "calendars" / "day.txt"
            if cal.exists():
                lines = cal.read_text().splitlines()
                print(f"\n  calendario day.txt: {len(lines)} fechas")
                print(f"    inicio: {lines[0]}")
                print(f"    fin:    {lines[-1]}")
    else:
        print("  (no existe features/)")

    print("\n" + "=" * 72)
    print(" CONCLUSION")
    print("=" * 72)
    inst_ok = (d / "instruments" / "sp500_liquid.txt").exists()
    any_txt = list((d / "instruments").glob("*.txt")) if (d / "instruments").is_dir() else []
    if inst_ok:
        print("  sp500_liquid.txt existe. El backtest deberia funcionar.")
    elif any_txt:
        print("  No hay sp500_liquid.txt, pero si otros universos.")
        print("  El backtest usara el primero que encuentre (ver AVISO al ejecutar).")
        print(f"  Si prefieres otro, exporta: QLIB_US_DATA={d} y ajusta el nombre.")
    else:
        print("  No hay ningun universo en instruments/. Revisa la instalacion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
