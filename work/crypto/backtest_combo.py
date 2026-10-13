"""backtest_combo.py — Combina el RÉGIMEN-SWITCH (macro LONG/CASH) con la v8 (selección).

Arquitectura en 2 niveles:
  - Nivel MACRO (régimen-switch v2): decide si estamos en régimen alcista (LONG, invertir en
    el mercado) o defensivo (CASH, USDT con yield). Parámetros fijados: vital_dd=0.30,
    exit_dd=0.30 (ATH), ma_win=75, under_ma_days=10.
  - Nivel SELECCIÓN (v8/modelo): cuando el régimen es LONG, COMPRA la cripto con mejor score
    del modelo SFM (> umbral), hasta MAX_POSITIONS posiciones, con costes reales.

Reutiliza: generación de predicciones del modelo de backtest_v8_regimen, y la señal de régimen
de regime_switch_v2. El régimen se calcula sobre BTC (proxy macro del mercado).

ADVERTENCIA: el modelo v8 fue entrenado con datos hasta ~2026 → sobre 2020-21/2024 su selección
es ESPEJO (no OOS limpio). La capa MACRO (régimen) SÍ es causal. El resultado combina ambos.

Uso:
    python backtest_combo.py --name bull2021 --start 2020-11-01 --end 2021-11-30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch  # noqa

import qlib  # noqa: E402
from qlib.config import REG_US  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from backtest_v8_regimen import (  # noqa: E402
    CRYPTOS, MODEL_PARAMS, MODEL_FILE, build_features_matrix, load_closes, load_model,
    SFMModelRefined, COST, MAX_POSITIONS, HIGH_CONF_THRESHOLD,
)
from regime_switch_v2 import (  # noqa: E402
    CASH_YIELD_APY, load_proxy, regime_signal_v2,
)

INITIAL_USD = 11000.0


def get_predictions(df_close, start, end, model, lookback):
    """Genera predicciones diarias (score por cripto) del modelo sobre el régimen [start,end]."""
    pred_days, pred_list = [], []
    all_days = list(df_close.index)
    for i in range(lookback + 25, len(all_days)):
        day = all_days[i]
        if day < pd.Timestamp(start, tz="UTC"):
            continue
        if day > pd.Timestamp(end, tz="UTC"):
            break
        window = df_close.loc[:day]
        if len(window) < lookback + 5:
            continue
        matrix = build_features_matrix(window)
        from research_utils import apply_clip_bounds, fit_clip_bounds  # noqa
        from sklearn.preprocessing import MinMaxScaler  # noqa
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scale = MinMaxScaler(feature_range=(-1, 1)); scaled = scale.fit_transform(matrix)
        x = torch.tensor(scaled[-lookback:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred = model(x).numpy()[0]
        pred_days.append(day); pred_list.append(pred)
    return pred_days, pred_list


def simulate_combo(regime_sig, pred_days, pred_list, df_close):
    """Régimen LONG -> operar v8; CASH -> yield USDT. Retorna (curve, n_buys, n_sells)."""
    daily_rate = (1.0 + CASH_YIELD_APY) ** (1.0 / 365.0) - 1.0
    cash = INITIAL_USD
    shares = {}          # symbol -> {"shares": x, "entry_day": r}
    curve, n_buys, n_sells = [], 0, 0
    idx_map = {c.upper(): i for i, c in enumerate(CRYPTOS)}
    regime_day = dict(regime_sig)  # fecha -> bool (LONG?)

    for r, day in enumerate(pred_days):
        scores = pred_list[r]
        close_row = df_close.loc[day] if day in df_close.index else None
        long_now = regime_day.get(day, True)

        # 1. yield del cash no invertido
        if daily_rate > 0 and cash > 0:
            cash += cash * daily_rate

        # 2. Si el régimen es CASH -> liquidar todo a cash (si habia)
        if not long_now:
            if close_row is not None:
                for s in list(shares.keys()):
                    if s in close_row.index:
                        px = float(close_row[s]); gross = shares[s]["shares"] * px
                        cash += gross - gross * COST
                        n_sells += 1
                        del shares[s]
            val = cash
            curve.append((day, val))
            continue

        # 3. Régimen LONG -> operar v8 (vender si deja de ser COMPRA, comprar top si slot)
        for s in list(shares.keys()):
            ci = idx_map[s]
            if scores[ci] < HIGH_CONF_THRESHOLD and close_row is not None and s in close_row.index:
                px = float(close_row[s]); gross = shares[s]["shares"] * px
                cash += gross - gross * COST
                n_sells += 1
                del shares[s]
        available = MAX_POSITIONS - len(shares)
        if available > 0 and close_row is not None:
            cands = []
            for c in CRYPTOS:
                cu = c.upper()
                if cu not in shares and scores[CRYPTOS.index(c)] > HIGH_CONF_THRESHOLD:
                    cands.append((cu, scores[CRYPTOS.index(c)]))
            cands.sort(key=lambda kv: -kv[1])
            for cu, _ in cands[:available]:
                if cu in close_row.index:
                    px = float(close_row[cu])
                    if px and px == px:
                        capital_per = cash / (available + 1)
                        nav = max(capital_per - capital_per * COST, 0.0)
                        shares_ = nav / px
                        cost = shares_ * px + capital_per * COST
                        if cost <= cash:
                            shares[cu] = {"shares": shares_, "entry_day": r}
                            cash -= cost
                            n_buys += 1
        val = cash
        if close_row is not None:
            for s in shares:
                if s in close_row.index:
                    val += shares[s]["shares"] * float(close_row[s])
        curve.append((day, val))
    return curve, n_buys, n_sells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--load-from", default="2020-01-01")
    args = ap.parse_args()

    # v8 model predictions
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)  # noqa
    df_close = load_closes()
    df_close = df_close[df_close.index <= pd.Timestamp("2026-10-31")]
    model = load_model()
    pred_days, pred_list = get_predictions(df_close, args.start, args.end, model, MODEL_PARAMS["lookback"])
    print(f"Predicciones v8: {len(pred_days)} días")

    # régimen-switch (macro) sobre BTC
    btc = load_proxy("btc")
    btc_win = btc[(btc.index >= pd.Timestamp(args.start, tz="UTC")) & (btc.index <= pd.Timestamp(args.end, tz="UTC"))]
    # la señal necesita historia previa para los promedios rodantes -> calcular sobre serie completa, luego recortar
    btc_full = load_proxy("btc")
    sig_full = regime_signal_v2(btc_full, vital_dd=0.30, exit_dd=0.30, ma_win=75, under_ma_days=10)
    s0 = pd.Timestamp(args.start, tz="UTC"); s1 = pd.Timestamp(args.end, tz="UTC")
    regime_sig = sig_full[(sig_full.index >= s0) & (sig_full.index <= s1)]
    print(f"Régimen LONG {int(regime_sig.sum())}/{len(regime_sig)} días ({int(regime_sig.sum())/max(len(regime_sig),1)*100:.0f}%)")

    # alinear predicciones con señal (por fecha)
    combo_sig = {}
    for d in pred_days:
        combo_sig[d] = bool(regime_sig.loc[d]) if d in regime_sig.index else True

    # reformular días con su señal
    sig_series = pd.Series({d: combo_sig[d] for d in pred_days})
    curve, n_buys, n_sells = simulate_combo(sig_series, pred_days, pred_list, df_close)
    vals = np.array([v for _, v in curve])
    rets = np.diff(vals) / vals[:-1]
    rets = np.insert(rets, 0, vals[0] / INITIAL_USD - 1)
    final = float(vals[-1]) if len(vals) else INITIAL_USD
    ret_pct = (final / INITIAL_USD - 1) * 100

    bh_btc = (btc_win.iloc[-1] / btc_win.iloc[0] - 1) * 100
    usdt = ((1 + CASH_YIELD_APY) ** (len(pred_days) / 365.0) - 1) * 100

    result = {
        "nombre": args.name, "start_date": str(pred_days[0].date()), "end_date": str(pred_days[-1].date()),
        "ret_combo_usd_pct": round(ret_pct, 2), "ret_buyhold_btc_pct": round(bh_btc, 2),
        "ret_usdt_pct": round(usdt, 2), "n_dias": len(pred_days),
        "dias_long": int(sig_series.sum()), "dias_cash": int((~sig_series).sum()),
        "n_buys": n_buys, "n_sells": n_sells,
        "param_macro": {"vital_dd": 0.30, "exit_dd": 0.30, "ma_win": 75, "under_ma_days": 10},
        "param_seleccion": {"high_conf": HIGH_CONF_THRESHOLD, "max_pos": MAX_POSITIONS, "cost": COST},
    }
    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"backtest_combo_{args.name}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()