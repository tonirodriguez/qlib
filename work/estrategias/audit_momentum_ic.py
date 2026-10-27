"""audit_momentum_ic.py — Mide el IC del momentum 120d con metodologia correcta.

POR QUE EXISTE
    El +0.066 que sostiene las 3 carteras vivas (E1/E2/E3) no es reproducible:

    1. `momentum_backtest.py` NO CALCULA IC. Solo hace backtest y reporta
       Sharpe/IR. El +0.066 aparece en su docstring, no en su salida.

    2. El unico script que si lo mide, `momentum_purgedcv.py`, documenta en
       `momentum_purgedcv_resultado.md` (2026-08-22) resultados NEGATIVOS:
           label 60d : IC Spearman purged -0.062
           label 120d: IC Spearman purged -0.036
       Por pliegue (120d): -0.030, -0.132, -0.100, +0.065, +0.019

    3. Ese "purged CV" NO purga: divide por numero de FILAS, no por fecha, y
       no deja hueco entre pliegues. Con label de FWD dias, las ventanas de
       etiqueta de pliegues vecinos se solapan.

    4. Aun asi, se sigue citando +0.066 como "alpha validado" en ~15 docs.

QUE MIDE ESTE SCRIPT
    A) IC POOLED (como el script viejo): correlacion sobre todas las muestras
       (ticker x fecha) apiladas. Mezcla efecto temporal y transversal.

    B) IC CROSS-SECTIONAL POR FECHA (el que importa): para cada fecha, la
       correlacion de rango EN SECCION CRUZADA entre momentum y retorno
       futuro de los ~292 tickers. Es lo que mide si el ranking sirve para
       elegir el top-30. Se reporta media, t-stat y % de fechas positivas.

    C) PURGED CV POR FECHA con EMBARGO real: pliegues temporales separados
       por FWD dias sin observaciones (purga), midiendo IC solo en test.

UMBRAL
    IC cross-sectional medio > 0.02 con t-stat > 2 se considera senal real.

USO (en WSL, con los datos US):
    conda run -n qlib python work/estrategias/audit_momentum_ic.py
    conda run -n qlib python work/estrategias/audit_momentum_ic.py --fwd 60
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "simulation"))

MOM_W = 120
START = "2018-01-01"
END = "2026-10-22"


def load_prices(universe: str | None = None) -> pd.DataFrame:
    """Cierres ajustados por factor (splits/dividendos deshechos)."""
    import qlib
    from qlib.data import D

    from rutas_entorno import get_qlib_uri, get_universe

    uri = get_qlib_uri()
    print(f"  provider_uri: {uri}")
    qlib.init(provider_uri=uri, region="us",
              kernels=int(os.environ.get("QLIB_KERNELS", "1")))

    tickers = get_universe(verbose=True)
    # universo por fichero (sp500_liquid.txt = 292) o por nombre qlib
    df = D.features(tickers, ["$close", "$factor"], start_time=START,
                    end_time=END, freq="day")
    c = df["$close"].unstack(level=0).sort_index()
    f = df["$factor"].unstack(level=0).sort_index()
    return (c / f).dropna(axis=0, thresh=int(0.5 * c.shape[1]))


def _spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman = Pearson sobre los RANGOS.

    Implementado asi para NO depender de scipy (pandas usa scipy para
    method="spearman"; si falta, revienta). El resultado es identico.
    """
    if len(a) < 3:
        return float("nan")
    ra = a.rank()
    rb = b.rank()
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(ra.corr(rb))


def ic_pooled(x: pd.Series, y: pd.Series) -> dict:
    """IC apilado (todas las muestras). Metodo del script viejo."""
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 100:
        return {"ic_pearson": float("nan"), "ic_spearman": float("nan"),
                "n": len(d)}
    return {
        "ic_pearson": float(d.iloc[:, 0].corr(d.iloc[:, 1])),
        "ic_spearman": _spearman(d.iloc[:, 0], d.iloc[:, 1]),
        "n": int(len(d)),
    }


def ic_cross_sectional(mom: pd.DataFrame, fwd: pd.DataFrame,
                       min_names: int = 30) -> pd.Series:
    """IC de rango por FECHA, en seccion cruzada.

    Para cada fecha t: spearman(momentum[t, :], fwd[t, :]) sobre los tickers
    con dato. Es el IC que mide si el ranking elige bien el top-30.
    """
    out = {}
    for t in mom.index:
        m = mom.loc[t]
        f = fwd.loc[t]
        both = pd.concat([m, f], axis=1).dropna()
        if len(both) < min_names:
            continue
        v = _spearman(both.iloc[:, 0], both.iloc[:, 1])
        if v == v:  # not NaN
            out[t] = v
    return pd.Series(out).dropna()


def purged_cv_by_date(ics: pd.Series, n_splits: int, embargo_days: int) -> list[dict]:
    """Pliegues temporales con EMBARGO real entre ellos.

    Se ordenan las fechas, se parten en n_splits bloques y se descartan las
    `embargo_days` fechas a cada lado de los bordes (purga). Asi ninguna
    observacion de test comparte ventana de etiqueta con las vecinas.
    """
    fechas = ics.index.sort_values()
    n = len(fechas)
    if n < n_splits * 20:
        return []
    edges = np.linspace(0, n, n_splits + 1).astype(int)
    res = []
    for k in range(n_splits):
        lo, hi = edges[k], edges[k + 1]
        # purga: recortar `embargo` fechas en cada borde
        lo_p = lo + (embargo_days if k > 0 else 0)
        hi_p = hi - (embargo_days if k < n_splits - 1 else 0)
        if hi_p - lo_p < 10:
            continue
        seg = ics.iloc[lo_p:hi_p]
        res.append({
            "fold": k + 1,
            "desde": str(seg.index.min().date()),
            "hasta": str(seg.index.max().date()),
            "n_fechas": int(len(seg)),
            "ic_medio": float(seg.mean()),
            "ic_std": float(seg.std()),
            "pct_positivas": float((seg > 0).mean()),
            "t_stat": float(seg.mean() / (seg.std() / np.sqrt(len(seg))))
            if seg.std() > 0 else float("nan"),
        })
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fwd", type=int, default=120,
                    help="dias del label (el 0.066 era con 120)")
    ap.add_argument("--universe", default=None)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--out", default=str(HERE / "audit_momentum_ic.json"))
    args = ap.parse_args()

    print("=" * 78)
    print(" AUDIT DEL IC DEL MOMENTUM 120d")
    print("=" * 78)
    print(f"  momentum: {MOM_W}d | label: {args.fwd}d | periodo: {START} -> {END}")
    print(f"  valor a contrastar: +0.066 (docs) vs -0.036 (purged CV ago-2026)")

    close = load_prices(args.universe)
    print(f"  cierres: {close.shape[0]} fechas x {close.shape[1]} tickers")

    mom = close / close.shift(MOM_W) - 1
    fwd = close.shift(-args.fwd) / close - 1

    # --- A) pooled ---
    print("\n" + "-" * 78)
    print(" A) IC POOLED (metodo del script antiguo)")
    print("-" * 78)
    ms = mom.stack().rename("mom")
    fs = fwd.stack().rename("fwd")
    pooled = ic_pooled(ms, fs)
    print(f"  muestras     : {pooled['n']:,}")
    print(f"  IC Pearson   : {pooled['ic_pearson']:+.4f}")
    print(f"  IC Spearman  : {pooled['ic_spearman']:+.4f}")
    print("  (este metodo mezcla efecto temporal y transversal)")

    # --- B) cross-sectional ---
    print("\n" + "-" * 78)
    print(" B) IC CROSS-SECTIONAL POR FECHA (el que decide el ranking)")
    print("-" * 78)
    ics = ic_cross_sectional(mom, fwd)
    if len(ics) < 20:
        print(f"  FALLO: solo {len(ics)} fechas validas")
        return 1
    media = float(ics.mean())
    std = float(ics.std())
    tstat = media / (std / np.sqrt(len(ics))) if std > 0 else float("nan")
    print(f"  fechas       : {len(ics)}")
    print(f"  IC medio     : {media:+.4f}")
    print(f"  IC std       : {std:.4f}")
    print(f"  t-stat       : {tstat:+.2f}")
    print(f"  % > 0        : {100*(ics > 0).mean():.1f}%")
    print(f"  p25/p50/p75  : {ics.quantile(.25):+.4f} / "
          f"{ics.median():+.4f} / {ics.quantile(.75):+.4f}")

    # --- C) purged CV con embargo ---
    print("\n" + "-" * 78)
    print(" C) PURGED CV POR FECHA (con embargo real)")
    print("-" * 78)
    folds = purged_cv_by_date(ics, args.n_splits, embargo_days=args.fwd)
    for f in folds:
        print(f"  Pliegue {f['fold']}: {f['desde']}->{f['hasta']} "
              f"({f['n_fechas']} fechas) IC {f['ic_medio']:+.4f} "
              f"t={f['t_stat']:+.2f} pos={f['pct_positivas']*100:.0f}%")
    if folds:
        fm = float(np.mean([f["ic_medio"] for f in folds]))
        print(f"\n  IC medio de pliegues: {fm:+.4f}")

    # --- veredicto ---
    print("\n" + "=" * 78)
    print(" VEREDICTO")
    print("=" * 78)
    print(f"  {'+0.066 citado en los docs':<38} {0.066:+.4f}")
    print(f"  {'IC pooled (Pearson)':<38} {pooled['ic_pearson']:+.4f}")
    print(f"  {'IC pooled (Spearman)':<38} {pooled['ic_spearman']:+.4f}")
    print(f"  {'IC cross-sectional medio':<38} {media:+.4f}  (t={tstat:+.2f})")
    print()
    if abs(media - 0.066) < 0.02:
        print("  >> El 0.066 se sostiene con el metodo correcto.")
    elif media > 0.02 and tstat > 2:
        print(f"  >> El 0.066 NO se reproduce, pero hay senal real "
              f"({media:+.4f}, t={tstat:.1f}).")
        print(f"     Usar {media:+.3f} como referencia, no 0.066.")
    elif media > 0:
        print(f"  >> Senal DEBIL ({media:+.4f}, t={tstat:.1f}): no supera el")
        print("     umbral 0.02 con significancia. El 0.066 era optimista.")
    else:
        print(f"  >> IC NEGATIVO ({media:+.4f}): la senal no predice en este")
        print("     periodo. Coincide con el purged CV de agosto (-0.036).")
        print("     >>> Las carteras vivas se apoyan en una senal sin alpha.")

    out = {
        "fecha": pd.Timestamp.now().isoformat(),
        "momentum_dias": MOM_W, "label_dias": args.fwd,
        "periodo": [START, END],
        "tickers": int(close.shape[1]),
        "pooled": pooled,
        "cross_sectional": {
            "n_fechas": int(len(ics)), "ic_medio": media, "ic_std": std,
            "t_stat": float(tstat), "pct_positivas": float((ics > 0).mean()),
        },
        "purged_cv": folds,
        "doc_066": 0.066,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                         default=float), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
