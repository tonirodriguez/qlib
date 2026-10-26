"""test_jev_backtest_sintetico.py — Valida el MOTOR del backtest sin qlib ni API.

Ejercita run_strategy() y metrics() con datos sinteticos para detectar errores
de indice/alineacion antes de ejecutarlo con datos reales. Tambien comprueba
que la exposicion 0 realmente anula los retornos (el error mas facil de cometer).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jev_backtest_ab import run_strategy, metrics  # noqa: E402


def synthetic_prices(n_days: int = 400, n_tickers: int = 40, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    rets = rng.normal(0.0003, 0.015, (n_days, n_tickers))
    # Un ticker con momentum claro (sube siempre) para que el ranking tenga senal
    rets[:, 0] = 0.0012
    prices = 100 * np.cumprod(1 + rets, axis=0)
    return pd.DataFrame(prices, index=dates, columns=[f"T{i:03d}" for i in range(n_tickers)])


def main() -> int:
    prices = synthetic_prices()
    print(f"precios sinteticos: {prices.shape[0]} x {prices.shape[1]}")

    # --- Test 1: exposicion 0 anula retornos ---
    zero = pd.Series(0.0, index=prices.index)
    net_zero = run_strategy(prices, zero, top_n=10, lookback=60, rebalance_days=5)
    s_zero = net_zero.dropna().abs().sum()
    print(f"\nTest 1 - exposicion 0.0 -> suma de |retornos| = {s_zero:.10f}")
    print(f"  {'OK: exposicion 0 no genera retornos' if s_zero < 1e-12 else 'FALLO: hay retornos con exposicion 0'}")

    # --- Test 2: exposicion 1 replica momentum ---
    full = pd.Series(1.0, index=prices.index)
    net_full = run_strategy(prices, full, top_n=10, lookback=60, rebalance_days=5)
    m_full = metrics(net_full, full)
    print(f"\nTest 2 - exposicion 1.0 -> Sharpe={m_full['sharpe']:.3f} "
          f"CAGR={m_full['cagr']:.2%} MaxDD={m_full['max_dd']:.2%}")
    print(f"  {'OK: genera retornos' if abs(m_full['cagr']) > 0 else 'FALLO: sin retornos'}")

    # --- Test 3: media escala linealmente ---
    half = pd.Series(0.5, index=prices.index)
    net_half = run_strategy(prices, half, top_n=10, lookback=60, rebalance_days=5)
    m_half = metrics(net_half, half)
    ratio = m_half["cagr"] / m_full["cagr"] if m_full["cagr"] else np.nan
    print(f"\nTest 3 - exposicion 0.5 -> CAGR={m_half['cagr']:.2%} "
          f"(ratio vs full = {ratio:.3f})")
    print(f"  {'OK: escala aprox lineal' if 0.2 < ratio < 0.8 else 'REVISAR: escalado raro'}")

    # --- Test 4: sin NaN en el tramo operativo ---
    tail = net_full.iloc[70:]
    n_nan = int(tail.isna().sum())
    print(f"\nTest 4 - NaN tras el arranque: {n_nan} de {len(tail)}")
    print(f"  {'OK' if n_nan == 0 else 'REVISAR: huecos en la serie'}")

    # --- Test 5: la exposicion se respeta en el calculo ---
    # Si exposicion media cae a la mitad, el retorno medio debe caer ~la mitad
    r_full = net_full.dropna()
    r_half = net_half.dropna()
    common = r_full.index.intersection(r_half.index)
    ratio_mean = r_half.loc[common].mean() / r_full.loc[common].mean() if r_full.loc[common].mean() else np.nan
    print(f"\nTest 5 - ratio de retorno medio (0.5 vs 1.0): {ratio_mean:.3f}")
    print(f"  {'OK: ~0.5 como se espera' if 0.3 < ratio_mean < 0.7 else 'REVISAR'}")

    # --- Test 6: metrics con serie vacia no rompe ---
    empty = metrics(pd.Series(dtype=float))
    print(f"\nTest 6 - metrics() con serie vacia: {empty}")
    print(f"  {'OK: no lanza excepcion' if np.isnan(empty['sharpe']) else 'REVISAR'}")

    print("\n" + "=" * 70)
    print("Si todos los tests dan OK, el motor esta listo para datos reales.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
