"""backtest_comparativo_500eur.py — Compara TODAS las estrategias con 500€ en BTC, por período + final.

Estrategias evaluadas (mismas reglas, capital inicial 500€->USD):
  1. BTC buy & hold
  2. USDT puro (yield 4.5%)
  3. Régimen-switch v2 (gate macro, reinversión total CORREGIDA)
  4. v8 (modelo SFM, selección sola)
  5. COMBO (régimen-switch gate AND v8 confirmación)

Detalle: el régimen-switch y el combo usan las funciones corregidas (sin bug de escala).
La v8 (modelo) sobre periodos históricos es ESPEJO (entreno con futuro) -> se marca como tal.
Periodos: bull2021, giro2022, rally2024, base2025, y TODO 2020-2026.

Uso: python backtest_comparativo_500eur.py  (desde /opt/data/qlib con el venv qlib)
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

from regime_switch_v2 import (  # noqa: E402
    CASH_YIELD_APY, load_proxy, regime_signal_v2, simulate_switch,
)
from backtest_v8_regimen import (  # noqa: E402
    CRYPTOS, MODEL_PARAMS, MODEL_FILE, build_features_matrix,
    SFMCellRefined, SFMModelRefined, COST, MAX_POSITIONS, HIGH_CONF_THRESHOLD,
    INITIAL_CAPITAL_EUR, EURUSD_DEFAULT,
)
from research_utils import fit_clip_bounds, apply_clip_bounds  # noqa: E402
from sklearn.preprocessing import MinMaxScaler  # noqa
from qlib.data import D  # noqa: E402

INITIAL_USD = 500.0 * 1.12   # 500 EUR -> USD (EURUSD 1.12, fijo para comparar estrategias)
PERIODOS = {
    "Bull2021": ("2020-11-01", "2021-11-30"),
    "Giro2022": ("2021-06-01", "2022-12-31"),
    "Rally2024": ("2024-01-01", "2024-12-31"),
    "Base2025": ("2025-01-01", "2026-08-30"),
    "TODO 2020-26": ("2020-11-01", "2026-10-08"),
}
BUY = 0.025


def load_datos():
    """Carga closes de las 9 criptos desde Qlib (replica de backtest_v8_regimen.main)."""
    close_dict = {}
    for c in CRYPTOS:
        df = D.features([c], ["$close"], start_time="2019-01-01", end_time="2026-12-31")
        df = df.reset_index()
        s = df.pivot(index="datetime", columns="instrument", values="$close")[c]
        close_dict[c.upper()] = s
    df_close = pd.DataFrame(close_dict).sort_index()
    return df_close[df_close.index <= pd.Timestamp("2026-10-31")]


def load_model():
    device = torch.device("cpu")
    model = SFMModelRefined(54, MODEL_PARAMS["hidden_dim"], MODEL_PARAMS["freq_components"],
                            len(CRYPTOS), MODEL_PARAMS["dropout_rate"])
    model.load_state_dict(torch.load(MODEL_FILE, map_location=device, weights_only=True))
    model.eval()
    return model


def get_predictions_batch(df_close, model, lookback):
    """Predicciones del modelo sobre TODOS los días (para filtrar luego por período)."""
    pred_map = {}  # day -> pred
    all_days = list(df_close.index)
    for i in range(lookback + 25, len(all_days)):
        day = all_days[i]
        if day > pd.Timestamp("2026-10-31"):
            break
        window = df_close.loc[:day]
        if len(window) < lookback + 5:
            continue
        matrix = build_features_matrix(window)
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scale = MinMaxScaler(feature_range=(-1, 1)); scaled = scale.fit_transform(matrix)
        x = torch.tensor(scaled[-lookback:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred_map[day] = model(x).numpy()[0]
    return pred_map


def get_predictions(df_close, start, end, model, lookback):
    """Versión por-período (llama a load_datos cargado una vez; aquí filtrar por fechas)."""
    # Nota: en este script usamos get_predictions_batch y filtramos por fechas.
    raise NotImplementedError("usar get_predictions_batch")


def simular_v8(pred_map, df_close, start, end, regime_series=None):
    """Seleccion v8 pura (o con gate de régimen si regime_series provisto). Reinvierte capital real."""
    daily_rate = (1.0 + CASH_YIELD_APY) ** (1.0 / 365.0) - 1.0
    s0, s1 = pd.Timestamp(start), pd.Timestamp(end)  # df_close es tz-naive
    days = [d for d in df_close.index if s0 <= d <= s1 and d in pred_map]
    cash = INITIAL_USD
    shares = {}
    idx_map = {c.upper(): i for i, c in enumerate(CRYPTOS)}
    regime_day = {} if regime_series is None else {d: bool(v) for d, v in regime_series.items()}
    last_day = days[-1] if days else None
    for day in days:
        scores = pred_map[day]
        close_row = df_close.loc[day]
        long_now = regime_day.get(day, True) if regime_series is not None else True
        if daily_rate > 0 and cash > 0:
            cash += cash * daily_rate
        if not long_now:  # régimen CASH -> liquidar
            for s in list(shares.keys()):
                if s in close_row.index:
                    px = float(close_row[s]); g = shares[s]["sh"] * px
                    cash += g - g * COST
                    del shares[s]
            continue
        # vender las que pierden COMPRA
        for s in list(shares.keys()):
            ci = idx_map[s]
            if scores[ci] < BUY and s in close_row.index:
                px = float(close_row[s]); g = shares[s]["sh"] * px
                cash += g - g * COST
                del shares[s]
        # comprar las mejores con slot libre
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
    # valorar al final del período
    val = cash
    if last_day is not None and last_day in df_close.index:
        row = df_close.loc[last_day]
        for s in shares:
            if s in row.index:
                val += shares[s]["sh"] * float(row[s])
        # valorar shares restantes con el último precio de su serie si no está en row
    else:
        for s in shares:
            val += shares[s]["sh"] * float(df_close[s].dropna().iloc[-1])
    return val


def main():
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)
    df_close = load_datos()
    model = load_model()
    lookback = MODEL_PARAMS["lookback"]
    pred_map = get_predictions_batch(df_close, model, lookback)

    btc = load_proxy("btc")
    sig_full = regime_signal_v2(btc, vital_dd=0.30, exit_dd=0.30, ma_win=75, under_ma_days=10)

    print("Capital inicial: 500 EUR (~$560). Estrategia: BTC / USDT / Régimen-switch / v8 / COMBO")
    print(f"{'periodo':<14}{'BH_BTC':>9}{'USDT':>8}{'Régimen':>9}{'v8':>9}{'COMBO':>9}")
    all_final = {}
    for pname, (s, e) in PERIODOS.items():
        st, en = pd.Timestamp(s, tz="UTC"), pd.Timestamp(e, tz="UTC")
        st_n, en_n = pd.Timestamp(s), pd.Timestamp(e)   # naive para df_close
        # buys
        px = btc[(btc.index >= st) & (btc.index <= en)]
        bh = (px.iloc[-1] / px.iloc[0] - 1) * 100
        usdt = ((1 + CASH_YIELD_APY) ** (len(px) / 365.0) - 1) * 100
        # regime
        reg = sig_full[(sig_full.index >= pd.Timestamp(s, tz="UTC")) & (sig_full.index <= pd.Timestamp(e, tz="UTC"))]
        val_reg, nt, _ = simulate_switch(px, reg, initial_usd=INITIAL_USD)
        ret_reg = (val_reg / INITIAL_USD - 1) * 100
        # v8 y combo (usar pred_map ya cargado)
        val_v8 = simular_v8(pred_map, df_close, s, e)
        ret_v8 = (val_v8 / INITIAL_USD - 1) * 100
        days_v8 = [d for d in df_close.index if st_n <= d <= en_n and d in pred_map]
        reg_naive = reg.tz_localize(None) if reg.index.tz is not None else reg
        reg_series = pd.Series({d: bool(reg_naive.loc[d]) for d in days_v8 if d in reg_naive.index}, dtype=bool)
        val_combo = simular_v8(pred_map, df_close, s, e, regime_series=reg_series)
        ret_combo = (val_combo / INITIAL_USD - 1) * 100
        all_final[pname] = {"BH": round(bh, 1), "USDT": round(usdt, 1), "Régimen": round(ret_reg, 1),
                            "v8": round(ret_v8, 1), "COMBO": round(ret_combo, 1)}
        print(f"{pname:<14}{bh:>8.1f}%{usdt:>7.1f}%{ret_reg:>8.1f}%{ret_v8:>8.1f}%{ret_combo:>8.1f}%")

    print("\n=== Resultado FINAL (TODO 2020-26) en USD y EUR (500 EUR iniciales) ===")
    fin = all_final["TODO 2020-26"]
    for k, v in fin.items():
        usd = INITIAL_USD * (1 + v / 100)
        print(f"  {k:<10} ret {v:+.1f}%  ->  ${usd:,.0f}  =  €{usd/1.12:,.0f}")

    out = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes" / "comparativa_500eur_todas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_final, indent=2, ensure_ascii=False) + "\n")
    print(f"\nGuardado: {out}")


if __name__ == "__main__":
    main()