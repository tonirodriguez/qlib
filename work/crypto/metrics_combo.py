"""metrics_combo.py — Sharpe, Sortino, drawdown de la estrategia COMBO, por período y total.

Reutiliza la simulación COMBO (régimen-switch gate + v8 selección) y calcula las métricas de
riesgo diarias (Sharpe, Sortino, Calmar, max drawdown) con research_utils.performance_metrics.
Unifica el resultado con la comparativa de retornos ya existente (comparativa_500eur_todas.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import qlib  # noqa
import torch  # noqa
from qlib.config import REG_US  # noqa

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from regime_switch_v2 import load_proxy, regime_signal_v2  # noqa: E402
from backtest_v8_regimen import (  # noqa: E402
    CRYPTOS, MODEL_PARAMS, MODEL_FILE, build_features_matrix,
    SFMModelRefined, COST, MAX_POSITIONS, HIGH_CONF_THRESHOLD,
)
from research_utils import performance_metrics  # noqa: E402
from sklearn.preprocessing import MinMaxScaler  # noqa: E402
from qlib.data import D  # noqa: E402

INITIAL_USD = 500.0 * 1.12   # 500 EUR -> USD
CASH_YIELD_APY = 0.045
BUY = 0.025
PERIODOS = {
    "Bull2021": ("2020-11-01", "2021-11-30"),
    "Giro2022": ("2021-06-01", "2022-12-31"),
    "Rally2024": ("2024-01-01", "2024-12-31"),
    "Base2025": ("2025-01-01", "2026-08-30"),
    "TODO": ("2020-11-01", "2026-10-08"),
}


def load_datos():
    close_dict = {}
    for c in CRYPTOS:
        df = D.features([c], ["$close"], start_time="2019-01-01", end_time="2026-12-31")
        df = df.reset_index()
        s = df.pivot(index="datetime", columns="instrument", values="$close")[c]
        close_dict[c.upper()] = s
    df_close = pd.DataFrame(close_dict).sort_index()
    return df_close[df_close.index <= pd.Timestamp("2026-10-31")]


def load_model():
    model = SFMModelRefined(54, MODEL_PARAMS["hidden_dim"], MODEL_PARAMS["freq_components"],
                            len(CRYPTOS), MODEL_PARAMS["dropout_rate"])
    model.load_state_dict(torch.load(MODEL_FILE, map_location="cpu", weights_only=True))
    model.eval()
    return model


def simular_combo_curve(pred_map, df_close, start, end, regime_map):
    """Simula el COMBO devolviendo la CURVA DE EQUITY diaria (lista de valores)."""
    daily_rate = (1.0 + CASH_YIELD_APY) ** (1.0 / 365.0) - 1.0
    s0, s1 = pd.Timestamp(start), pd.Timestamp(end)
    days = [d for d in df_close.index if s0 <= d <= s1 and d in pred_map]
    cash = INITIAL_USD
    shares = {}
    idx_map = {c.upper(): i for i, c in enumerate(CRYPTOS)}
    curve = []
    for day in days:
        scores = pred_map[day]
        close_row = df_close.loc[day]
        long_now = regime_map.get(day, True)
        if daily_rate > 0 and cash > 0:
            cash += cash * daily_rate
        if not long_now:
            for s in list(shares.keys()):
                if s in close_row.index:
                    px = float(close_row[s]); g = shares[s]["sh"] * px
                    cash += g - g * COST
                    del shares[s]
            curve.append(cash)
            continue
        for s in list(shares.keys()):
            ci = idx_map[s]
            if scores[ci] < BUY and s in close_row.index:
                px = float(close_row[s]); g = shares[s]["sh"] * px
                cash += g - g * COST
                del shares[s]
        available = MAX_POSITIONS - len(shares)
        if available > 0:
            cands = [(c.upper(), scores[CRYPTOS.index(c)]) for c in CRYPTOS
                     if c.upper() not in shares and scores[CRYPTOS.index(c)] > BUY]
            cands.sort(key=lambda kv: -kv[1])
            for cu, _ in cands[:available]:
                if cu in close_row.index:
                    px = float(close_row[cu])
                    if px and px == px:
                        cp = cash / (available + 1)
                        nav = max(cp - cp * COST, 0.0)
                        sh = nav / px
                        cost = sh * px + cp * COST
                        if cost <= cash:
                            shares[cu] = {"sh": sh}; cash -= cost
        val = cash
        for s in shares:
            if s in close_row.index:
                val += shares[s]["sh"] * float(close_row[s])
        curve.append(val)
    return np.array(curve)


def main():
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)
    df_close = load_datos()
    model = load_model()
    lookback = MODEL_PARAMS["lookback"]

    # predicciones por día (una pasada)
    pred_map = {}
    all_days = list(df_close.index)
    for i in range(lookback + 25, len(all_days)):
        day = all_days[i]
        if day > pd.Timestamp("2026-10-31"):
            break
        window = df_close.loc[:day]
        if len(window) < lookback + 5:
            continue
        matrix = build_features_matrix(window)
        clip_b = np.quantile(matrix, 0.0005, axis=0); clip_u = np.quantile(matrix, 0.9995, axis=0)
        matrix = np.clip(matrix, clip_b, clip_u)
        scale = MinMaxScaler(feature_range=(-1, 1)); scaled = scale.fit_transform(matrix)
        x = torch.tensor(scaled[-lookback:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred_map[day] = model(x).numpy()[0]

    # régimen sobre BTC (serie completa) -> normalizar a tz-naive para coincidir con df_close
    btc = load_proxy("btc")
    sig_full = regime_signal_v2(btc, vital_dd=0.30, exit_dd=0.30, ma_win=75, under_ma_days=10)
    sig_map = {d.tz_localize(None) if getattr(d, "tz", None) else d: bool(v) for d, v in sig_full.items()}

    # cargar comparativa de retornos existente para unir
    comp = json.loads((PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
                       / "comparativa_500eur_todas.json").read_text())

    resultado = {}
    print("Métricas de riesgo de la estrategia COMBO (capital 500 EUR / $560)")
    print(f"{'periodo':<10}{'ret%':>9}{'Sharpe':>8}{'Sortino':>9}{'MaxDD%':>8}{'Calmar':>7}{'anual%':>9}")
    for pname, (s, e) in PERIODOS.items():
        st, en = pd.Timestamp(s), pd.Timestamp(e)
        curve = simular_combo_curve(pred_map, df_close, s, e, sig_map)
        rets = np.diff(curve) / curve[:-1]
        # primer retorno = cambio desde el capital inicial
        rets = np.insert(rets, 0, curve[0] / INITIAL_USD - 1)
        m = performance_metrics(rets)
        ret_pct = (curve[-1] / INITIAL_USD - 1) * 100
        sharpe = round(m["sharpe"], 3)
        sortino = round(m["sortino"], 3)
        maxdd = round(m["max_drawdown"] * 100, 1)
        calmar = round(m["calmar"], 3)
        anual = round(m["annualized_return"] * 100, 1)
        resultado[pname] = {"ret_pct": round(ret_pct, 1), "sharpe": sharpe, "sortino": sortino,
                            "max_drawdown_pct": maxdd, "calmar": calmar, "annualized_pct": anual,
                            "n_dias": int(len(curve))}
        print(f"{pname:<10}{ret_pct:>8.1f}%{sharpe:>8.2f}{sortino:>9.2f}{maxdd:>8.1f}%{calmar:>7.2f}{anual:>8.1f}%")

    out = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes" / "metrics_combo.json"
    out.write_text(json.dumps(resultado, indent=2, ensure_ascii=False) + "\n")
    print(f"\nGuardado: {out}")


if __name__ == "__main__":
    main()