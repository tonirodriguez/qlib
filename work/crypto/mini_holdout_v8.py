"""
mini_holdout_v8.py — Mini-holdout para validar la optimizacion de la config v8.

Objetivo: verificar si la configuracion ganadora de la sensibilidad generaliza a
un periodo NO usado para elegirla (descartar sobreajuste).

Diseño honesto (time-split):
  - DATOS: predicciones causales del modelo sfm_top3.pth en 2025-01-01 -> 2026-08-30.
  - PERIODO DE SELECCION:  2025-01-01 -> 2025-12-31
    Se re-ejecuta la sensibilidad SOLO en este tramo y se elige la mejor config.
  - PERIODO DE VALIDACION (holdout real): 2026-01-01 -> 2026-08-30
    Nunca se toco durante la seleccion de config. Aqui se evaluan:
       a) BASE (config actual del paper)
       b) La mejor config elegida en 2025
    Si la mejor config de 2025 tambien gana en 2026 (vs base), generaliza.

Todas las variantes usan costes Binance + yield cash USDT (igual que la sensibilidad).

Uso: <python> work/crypto/mini_holdout_v8.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

import backtest_v8_2025 as bt  # noqa: E402
from research_utils import performance_metrics  # noqa: E402
from research_utils import fit_clip_bounds, apply_clip_bounds  # noqa: E402
from sklearn.preprocessing import MinMaxScaler  # noqa: E402

LOOKBACK = bt.MODEL_PARAMS["lookback"]
YIELD = bt.CASH_YIELD_APY

# Periodos
SEL_START, SEL_END = "2025-01-01", "2025-12-31"
VAL_START, VAL_END = "2026-01-01", "2026-08-30"

# Las mismas configs que la sensibilidad
CONFIGS = [
    ("BASE (actual)",           0.025, 0.015, 0, 2),
    ("Histeresis sell=0.00",    0.025, 0.000, 0, 2),
    ("Umbral sube a 0.04",      0.040, 0.015, 0, 2),
    ("Umbral sube a 0.06",      0.060, 0.015, 0, 2),
    ("Max posiciones 3",        0.025, 0.015, 0, 3),
    ("Max posiciones 4",        0.025, 0.015, 0, 4),
    ("Histeresis+Umbral+Hold",  0.040, 0.000, 3, 3),
    ("Hold 5d + histeresis",    0.035, 0.005, 5, 3),
]


def _build_result(days_list, pred_list, df_close, cfg, name):
    """Corre la simulacion sobre una sub-muestra de predicciones y devuelve metricas.

    days_list: fechas reales (Timestamp) correspondientes a cada prediccion.
    pred_list: las predicciones [n,9].
    """
    curve, opers, interest = bt.simulate_portfolio(
        days_list, pred_list, df_close,
        cash_yield_apy=YIELD,
        buy_threshold=cfg[1], sell_threshold=cfg[2],
        min_holding_days=cfg[3], max_positions=cfg[4],
    )
    vals = np.array([v for _, v in curve])
    rets = np.diff(vals) / vals[:-1] if len(vals) > 1 else np.array([0.0])
    rets = np.insert(rets, 0, vals[0] / bt.INITIAL_CAPITAL_USD - 1)
    m = performance_metrics(rets)
    final_usd = float(vals[-1])
    ret_usd = (final_usd / bt.INITIAL_CAPITAL_USD - 1) * 100
    final_eur = final_usd / bt.EURUSD_END
    ret_eur = (final_eur / bt.INITIAL_CAPITAL_EUR - 1) * 100
    return {
        "name": name,
        "return_usd_pct": round(ret_usd, 2),
        "return_eur_pct": round(ret_eur, 2),
        "sharpe": round(m["sharpe"], 3),
        "max_drawdown_pct": round(m["max_drawdown"] * 100, 2),
        "n_trades": len(opers),
        "days": len(days_list),
    }


def main():
    import qlib
    from qlib.config import REG_US
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)

    df_close = bt.load_closes()
    model = bt.load_model()

    # Generar predicciones causales una sola vez (2025 -> ago-2026)
    full_days, preds = [], []
    all_days = list(df_close.index)
    for i in range(LOOKBACK + 25, len(all_days)):
        day = all_days[i]
        if day < pd.Timestamp("2025-01-01"):
            continue
        if day > pd.Timestamp("2026-08-30"):
            break
        window = df_close.loc[:day]
        if len(window) < LOOKBACK + 5:
            continue
        matrix = bt.build_features_matrix(window)
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scaler = MinMaxScaler(feature_range=(-1, 1)); scaled = scaler.fit_transform(matrix)
        x = torch.tensor(scaled[-LOOKBACK:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred = model(x).numpy()[0]
        full_days.append(day); preds.append(pred)
    preds = np.array(preds)
    print(f"Predicciones totales: {len(full_days)} ({full_days[0].date()} -> {full_days[-1].date()})")

    # Indices por periodo
    sel_idx = [i for i, d in enumerate(full_days) if pd.Timestamp(SEL_START) <= d <= pd.Timestamp(SEL_END)]
    val_idx = [i for i, d in enumerate(full_days) if pd.Timestamp(VAL_START) <= d <= pd.Timestamp(VAL_END)]
    print(f"Seleccion (2025): {len(sel_idx)} dias | Validacion (2026): {len(val_idx)} dias")

    # Fase 1: seleccionar la mejor config en 2025
    print("\n" + "=" * 80)
    print("FASE 1 — Seleccion de la mejor config SOLO en el periodo 2025 (sin tocar 2026)")
    print("=" * 80)
    sel_results = []
    for cfg_tuple in CONFIGS:
        name, buy, sell, hold, maxp = cfg_tuple
        res = _build_result([full_days[i] for i in sel_idx], preds[sel_idx],
                            df_close, cfg_tuple, name)
        sel_results.append(res)
        print(f"  {name:28s} retUSD={res['return_usd_pct']:>7.2f}%  sharpe={res['sharpe']:>6.3f}  "
              f"trades={res['n_trades']:>4d}")

    best_sel = max(sel_results, key=lambda r: r["sharpe"])
    print(f"\n  -> Mejor config en 2025 (por Sharpe): {best_sel['name']} ({best_sel['sharpe']})")

    # Reconstruir el dict de la config ganadora
    best_cfg = next((c for c in CONFIGS if c[0] == best_sel["name"]), CONFIGS[0])

    # Fase 2: validar en 2026 (holdout) — BASE vs mejor config
    print("\n" + "=" * 80)
    print("FASE 2 — VALIDACION en 2026 (holdout real, NO usado para elegir)")
    print("=" * 80)
    base = _build_result([full_days[i] for i in val_idx], preds[val_idx], df_close, CONFIGS[0], CONFIGS[0][0])
    challenger = _build_result([full_days[i] for i in val_idx], preds[val_idx], df_close, best_cfg, "MEJOR 2025: " + best_cfg[0])
    print(f"  {base['name']:28s} retUSD={base['return_usd_pct']:>7.2f}%  sharpe={base['sharpe']:>6.3f}  trades={base['n_trades']}")
    print(f"  {challenger['name']:28s} retUSD={challenger['return_usd_pct']:>7.2f}%  sharpe={challenger['sharpe']:>6.3f}  trades={challenger['n_trades']}")

    win = challenger["sharpe"] > base["sharpe"]
    verdict = (
        "VALIDADO: la config optimizada generaliza (gana a la base en el holdout 2026)."
        if win else
        "NO VALIDADO: en el holdout 2026 la config optimizada no supera a la base (posible sobreajuste a 2025)."
    )
    print("\n  VEREDICTO:", verdict)

    # Guardar
    out = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "mini_holdout_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "periodo_seleccion": f"{SEL_START} -> {SEL_END}",
        "periodo_validacion": f"{VAL_START} -> {VAL_END}",
        "mejor_2025": best_sel,
        "config_ganadora": {"buy": best_cfg[0], "sell": best_cfg[1],
                            "hold": best_cfg[2], "pos": best_cfg[3]},
        "validacion_2026": {"base": base, "desafiante": challenger},
        "veredicto": verdict,
        "validado": win,
    }, indent=2) + "\n", encoding="utf-8")
    print("\nGuardado:", out)


if __name__ == "__main__":
    main()