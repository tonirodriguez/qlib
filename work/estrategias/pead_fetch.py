"""pead_fetch.py — Descarga datos de earnings (sorpresa) para el universo.

POR QUE UN SCRIPT NUEVO
    Los existentes tienen rutas de otra maquina:
      pead_fetch_full.py   -> /opt/data/.../sp500_liquid.txt (no existe)
      pead_fetch_append.py -> idem
      simulation/backfill_pead.py -> idem
    Este usa `rutas_entorno` para resolverlo, y escribe en la ruta correcta
    del repo (work/estrategias/), no en /opt/data/.

QUE DESCARGA
    De Yahoo (via `yahooquery`), por ticker:
      ticker, quarter, actual, estimate, surprise_pct, reported_ts
    Es lo que consume `sim_utils.load_last_surprise()` y el filtro PEAD.

SALIDA
    work/estrategias/pead_earnings_data_full.csv   (historial completo)

USO
    conda run -n qlib python work/estrategias/pead_fetch.py
    conda run -n qlib python work/estrategias/pead_fetch.py --limit 50
    conda run -n qlib python work/estrategias/pead_fetch.py --resume

NOTAS
    - Yahoo limita peticiones: el script espacia ~0.8s y reintenta con backoff.
    - Tarda ~15-25 min para 500 tickers.
    - `--resume` reutiliza el CSV existente y solo baja los que faltan.
    - Los tickers sin earnings (ETFs, clases nuevas) se saltan sin reintentar.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "simulation"))

from rutas_entorno import get_universe                       # noqa: E402

OUT = HERE / "pead_earnings_data_full.csv"
MAX_RETRIES = 5
RETRY_DELAY = 3.0
SLEEP_BETWEEN = 0.8


def fetch_earnings(ticker: str) -> list[dict] | None:
    """Earnings trimestrales de un ticker, o None si no hay."""
    from yahooquery import Ticker

    tk = Ticker(ticker)
    try:
        er = tk.earnings
    except Exception:
        raise
    if not isinstance(er, dict) or ticker not in er or not er[ticker]:
        return None
    q = er[ticker].get("earningsChart", {}).get("quarterly", [])
    rows = []
    for trim in q:
        actual = trim.get("actual")
        est = trim.get("estimate")
        report_ts = trim.get("reportedDate")
        surp = trim.get("surprisePct")
        if actual is None or est is None or surp is None:
            continue
        rows.append({
            "ticker": ticker,
            "quarter": trim.get("date"),
            "actual": actual,
            "estimate": est,
            "surprise_pct": float(surp),
            "reported_ts": report_ts,
        })
    return rows or None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="Procesar solo N tickers (prueba)")
    ap.add_argument("--resume", action="store_true",
                    help="Reutilizar el CSV existente y bajar solo los que faltan")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--min-dollar-vol", type=float, default=0.0,
                    help="Filtro de liquidez (0 = sin filtro)")
    args = ap.parse_args()

    print("=" * 74)
    print(" DESCARGA DE EARNINGS (PEAD)")
    print("=" * 74)

    try:
        import yahooquery  # noqa: F401
    except ImportError:
        print("\n  FALLO: falta 'yahooquery'.")
        print("  Instala con:  pip install yahooquery")
        return 1

    # --- universo ---
    mdv = args.min_dollar_vol or None
    tickers = get_universe(min_dollar_vol=mdv)
    if args.limit:
        tickers = tickers[:args.limit]
    print(f"  universo: {len(tickers)} tickers")

    # --- resume ---
    out_path = Path(args.out)
    existentes: set[str] = set()
    df_prev = pd.DataFrame()
    if args.resume and out_path.exists():
        df_prev = pd.read_csv(out_path)
        existentes = set(df_prev["ticker"].unique())
        print(f"  resume: {len(existentes)} tickers ya en {out_path.name}")
        tickers = [t for t in tickers if t not in existentes]
        print(f"  pendientes: {len(tickers)}")

    if not tickers:
        print("\n  Nada que descargar.")
        return 0

    # --- descarga ---
    print(f"\n  descargando (retries={MAX_RETRIES}, sleep={SLEEP_BETWEEN}s)...")
    all_rows: list[dict] = []
    ok = 0
    sin_datos = 0
    fallos = 0
    t0 = time.time()

    for i, t in enumerate(tickers, 1):
        rows = None
        for attempt in range(MAX_RETRIES):
            try:
                rows = fetch_earnings(t)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == MAX_RETRIES - 1:
                    fallos += 1
                    print(f"    {t}: FALLO tras {MAX_RETRIES} intentos "
                          f"({str(exc)[:60]})")
                else:
                    time.sleep(RETRY_DELAY * (attempt + 1))
        if rows:
            all_rows.extend(rows)
            ok += 1
        elif rows is None and fallos == 0:
            sin_datos += 1

        if i % 25 == 0 or i == len(tickers):
            el = time.time() - t0
            ritmo = i / el if el else 0
            restante = (len(tickers) - i) / ritmo if ritmo else 0
            print(f"    {i}/{len(tickers)} | con datos: {ok} | sin: {sin_datos} "
                  f"| fallos: {fallos} | ETA {restante/60:.1f} min")

        time.sleep(SLEEP_BETWEEN)

    # --- guardar ---
    df_new = pd.DataFrame(all_rows)
    df = pd.concat([df_prev, df_new], ignore_index=True) if len(df_prev) else df_new

    print("\n" + "=" * 74)
    print(" RESULTADO")
    print("=" * 74)
    print(f"  tickers con earnings : {ok}")
    print(f"  tickers sin earnings : {sin_datos}")
    print(f"  tickers con fallo    : {fallos}")
    print(f"  trimestres nuevos    : {len(df_new)}")
    print(f"  trimestres totales   : {len(df)}")

    if df.empty:
        print("\n  NO se obtuvo ningun dato.")
        print("  Posibles causas: sin red, Yahoo bloqueando, o nombres invalidos.")
        return 1

    df.to_csv(out_path, index=False)
    print(f"\n  Guardado en: {out_path}")
    print(f"  tickers unicos: {df['ticker'].nunique()}")

    # --- validacion para el filtro PEAD ---
    print("\n" + "=" * 74)
    print(" VALIDACION PARA EL FILTRO PEAD")
    print("=" * 74)
    cols = set(df.columns)
    requeridas = {"ticker", "surprise_pct", "reported_ts"}
    faltan = requeridas - cols
    if faltan:
        print(f"  ALERTA: faltan columnas {faltan}")
        print(f"  sim_utils necesita: {requeridas}")
    else:
        print(f"  OK: columnas necesarias presentes")
        n_sorp = df["surprise_pct"].notna().sum()
        n_ts = df["reported_ts"].notna().sum()
        print(f"  surprise_pct validos: {n_sorp}/{len(df)}")
        print(f"  reported_ts validos : {n_ts}/{len(df)}")
        print(f"  rango surprise_pct  : {df['surprise_pct'].min():.2f} .. "
              f"{df['surprise_pct'].max():.2f}")
        # cuantos tickers tienen sorpresas NEGATIVAS (las que filtra el PEAD)
        neg = df[df["surprise_pct"] < -5.0]["ticker"].nunique()
        print(f"  tickers con sorpresa < -5%: {neg}")
        if neg == 0:
            print("  AVISO: ningun ticker con sorpresa fuertemente negativa")
            print("         -> el filtro PEAD no excluiria a nadie")

    print("\n  Siguiente paso:")
    print("    conda run -n qlib python work/estrategias/simulation/simulate_pead.py")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
