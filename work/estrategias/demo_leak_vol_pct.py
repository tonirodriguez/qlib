"""demo_leak_vol_pct.py — Demuestra el leak de vol_pct con datos sinteticos.

NO necesita qlib ni datos reales. Reproduce EXACTAMENTE la formula de
extract_estados.py lineas 62-64 y compara con una version causal.

Objetivo: medir cuanto se separa el percentil "full-range" del percentil
causal, y en que direccion. Si la diferencia es grande y sistematica, el
backtest queda contaminado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VOL_WIN = 20


def build_series(n: int = 1500, seed: int = 42) -> pd.Series:
    """Serie de retornos con un regimen de crisis a mitad (mas volatilidad)."""
    rng = np.random.default_rng(seed)
    rets = np.empty(n)
    rets[: n // 2] = rng.normal(0.0004, 0.008, n // 2)          # calma
    rets[n // 2:] = rng.normal(-0.0006, 0.024, n - n // 2)      # crisis
    return pd.Series(rets, index=pd.bdate_range("2018-01-01", periods=n))


def vol_from_returns(rets: pd.Series) -> pd.Series:
    return rets.rolling(VOL_WIN).std() * np.sqrt(252)


# ---------------------------------------------------------------------------
# VERSION ACTUAL (extract_estados.py, lineas 62-64): LEAK
# ---------------------------------------------------------------------------
def vol_pct_full_range(vol: pd.Series) -> pd.Series:
    """Percentil calculado contra la ventana ENTERA... pero es rolling."""
    return vol.rolling(252, min_periods=120).apply(
        lambda x: (x.iloc[-1] > x).mean(), raw=False
    )


# ---------------------------------------------------------------------------
# VERSION CAUSAL: mismo resultado matematicamente, pero explicita
# ---------------------------------------------------------------------------
def vol_pct_causal(vol: pd.Series, win: int = 252, min_periods: int = 120) -> pd.Series:
    """Percentil de HOY dentro de la ventana que TERMINA HOY.

    Es identico a vol_pct_full_range porque `rolling` ya es causal. Se escribe
    aparte para poder testear que NO hay diferencia, y para dejar claro que
    el calculo solo mira hacia atras.
    """
    out = pd.Series(index=vol.index, dtype=float)
    vals = vol.to_numpy()
    for i in range(len(vals)):
        start = max(0, i - win + 1)
        window = vals[start : i + 1]
        window = window[~np.isnan(window)]
        if len(window) < min_periods:
            continue
        out.iloc[i] = float((window[-1] > window).mean())
    return out


def main() -> None:
    rets = build_series()
    vol = vol_from_returns(rets)

    a = vol_pct_full_range(vol)
    b = vol_pct_causal(vol)

    both = pd.concat([a.rename("actual"), b.rename("causal")], axis=1).dropna()
    diff = (both["actual"] - both["causal"]).abs()

    print("=" * 70)
    print("TEST 1: ¿es rolling() causal o mira al futuro?")
    print("=" * 70)
    print(f"  fechas comparadas: {len(both)}")
    print(f"  max |diferencia|:  {diff.max():.12f}")
    print(f"  filas con diff>0:  {(diff > 0).sum()}")
    print()
    if diff.max() < 1e-12:
        print("  => IDENTICOS. rolling() NO mira al futuro.")
        print("     vol_pct tal como esta en extract_estados.py ES CAUSAL.")
    else:
        print("  => DIFIEREN. Hay fuga de informacion futura.")
        print("     VERIFICA antes de seguir: revisa la implementacion.")

    # Ilustracion adicional: que pasaria con un percentil GLOBAL (no rolling).
    print()
    print("=" * 70)
    print("TEST 2: contraste con un percentil GLOBAL (ese SI filtraria futuro)")
    print("=" * 70)
    vol_global = vol.rank(pct=True)  # usa TODA la serie para rankear
    comp = pd.concat([vol_global.rename("global"), b.rename("causal")], axis=1).dropna()
    d2 = (comp["global"] - comp["causal"]).abs()
    print(f"  max |global - causal|: {d2.max():.4f}")
    print(f"  media |global - causal|: {d2.mean():.4f}")
    print(f"  correlacion: {comp['global'].corr(comp['causal']):.4f}")
    print()
    print("  Esto muestra por que el percentil GLOBAL es el problematico:")
    print("  usa el maximo historico de TODA la serie (incluido el futuro).")

    # Cuantos puntos extremos cambian de decision
    thr = 0.90
    crisis_causal = (b >= thr)
    crisis_global = (vol_global >= thr)
    both_idx = crisis_causal.index.intersection(crisis_global.index)
    agree = (crisis_causal.loc[both_idx] == crisis_global.loc[both_idx]).mean()
    print()
    print("=" * 70)
    print(f"TEST 3: con umbral p90 (el que usa el vol_gate), ¿coinciden?")
    print("=" * 70)
    print(f"  acuerdo global vs causal: {agree:.2%}")
    print(f"  dias 'crisis' segun causal: {crisis_causal.sum()}")
    print(f"  dias 'crisis' segun global: {crisis_global.sum()}")


if __name__ == "__main__":
    main()
