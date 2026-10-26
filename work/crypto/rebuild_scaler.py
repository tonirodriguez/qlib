#!/usr/bin/env python3
"""rebuild_scaler.py — Reconstruye scaler.pkl y clip_bounds.pkl con la ventana
exacta con la que se entrenó sfm_top3.pth.

Problema que resuelve:
  qlib_sfm_pipeline.v8.py entrena con clip_bounds + MinMaxScaler ajustados
  sobre el 60% inicial (train), pero NUNCA guarda esos objetos. El scaler.pkl
  que había en output/sfm_v8/ lo generó sfm_daily_signal.py ajustándolo sobre
  TODA la matriz sin clipping → distribución distinta a la de entrenamiento
  → sesgo sistemático en las predicciones.

Uso:
    python work/crypto/rebuild_scaler.py            # escribe los artefactos
    python work/crypto/rebuild_scaler.py --dry-run  # solo comprueba, no escribe
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib.util

# Importar el pipeline v8 sin ejecutar main (está guardado por __main__)
_spec = importlib.util.spec_from_file_location(
    "v8", str(Path(__file__).resolve().parent / "qlib_sfm_pipeline.v8.py")
)
v8 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v8)

from crypto.research_utils import fit_clip_bounds  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "sfm_v8"

# Parámetros EXACTOS del entrenamiento original (run_v8.log, 2026-09-01 16:47)
START_DATE = "2015-01-01"
END_DATE = "2026-09-01"
FWD_DAYS = 1
CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
TRAIN_FRAC = 0.60


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no escribir artefactos")
    ap.add_argument("--end-date", default=END_DATE)
    args = ap.parse_args()

    import qlib
    from qlib.config import REG_US

    qlib.init(provider_uri="data/qlib", region=REG_US, kernels=1)

    print(f"Cargando datos {START_DATE} -> {args.end_date} (fwd={FWD_DAYS}) ...")
    market_data, labels_data, dates_idx = v8.load_and_process_crypto_data(
        CRYPTOS, START_DATE, args.end_date, fwd_days=FWD_DAYS
    )
    n_total = len(market_data)
    train_end = int(n_total * TRAIN_FRAC)
    market_train = market_data[:train_end]

    d0 = dates_idx[0].strftime("%Y-%m-%d")
    d1 = dates_idx[train_end - 1].strftime("%Y-%m-%d")
    print(f"Filas totales: {n_total} | TRAIN: {train_end} ({d0} -> {d1})")
    print(f"Matriz train: {market_train.shape}")

    bounds = fit_clip_bounds(market_train)
    clipped = np.clip(market_train, bounds.lower, bounds.upper)
    scaler = MinMaxScaler(feature_range=(-1, 1))
    scaled = scaler.fit_transform(clipped)

    print(f"clip_bounds: lower {bounds.lower.min():.4f}..{bounds.lower.max():.4f}")
    print(f"clip_bounds: upper {bounds.upper.min():.4f}..{bounds.upper.max():.4f}")
    print(f"scaled: min {scaled.min():.4f} max {scaled.max():.4f} "
          f"(esperado ~[-1, 1])")
    outside = ((scaled < -1.0001) | (scaled > 1.0001)).sum()
    print(f"celdas fuera de [-1,1] tras clipping: {outside}")

    if args.dry_run:
        print("\n[dry-run] no se escriben artefactos.")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(OUTPUT_DIR / "clip_bounds.pkl", "wb") as f:
        pickle.dump({"lower": bounds.lower, "upper": bounds.upper}, f)
    with open(OUTPUT_DIR / "scaler_meta.json", "w") as f:
        import json
        json.dump({
            "trained_on": {"start": START_DATE, "end": args.end_date},
            "train_rows": train_end,
            "train_range": [d0, d1],
            "n_features": int(market_train.shape[1]),
            "cryptos": CRYPTOS,
            "fwd_days": FWD_DAYS,
        }, f, indent=2)

    print(f"\n✅ Artefactos escritos en {OUTPUT_DIR}/")
    print("   scaler.pkl, clip_bounds.pkl, scaler_meta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
