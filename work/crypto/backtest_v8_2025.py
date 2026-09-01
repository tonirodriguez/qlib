"""
backtest_v8_2025.py — Backtest SFM v8 2025-01-01 -> 2026-08-30 operando IGUAL que el paper.

Replica fielmente la logica de sfm_paper_trading.py:
- Long en HASTA MAX_POSITIONS monedas (default 2).
- Compra monedas con score > HIGH_CONF_THRESHOLD (confianza ALTA), hasta llenar cupos.
- Ponderacion equitativa del capital entre posiciones.
- Vende posiciones que dejan de tener COMPRA.
- Costes Binance: fee 0.1% taker + half-spread + slippage en cada cambio de posicion.

Metodologia causal: features y scaler con datos <= cada dia (sin lookahead).
Convierte 10000 EUR -> USD al inicio y USD -> EUR al final.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

import pywt  # noqa: E402
import qlib  # noqa: E402
from qlib.config import REG_US  # noqa: E402
from qlib.data import D  # noqa: E402

from research_utils import apply_clip_bounds, fit_clip_bounds, performance_metrics  # noqa: E402
from sklearn.preprocessing import MinMaxScaler  # noqa: E402

CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
START = "2025-01-01"
END = "2026-08-30"
MODEL_FILE = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "sfm_top3.pth"
MODEL_PARAMS = {"hidden_dim": 96, "freq_components": 20, "dropout_rate": 0.30, "lookback": 20}

INITIAL_CAPITAL_EUR = 10000.0
EURUSD_START = 1.0389   # EUR/USD dia habil previo a 1/1/2025
EURUSD_END = 1.1643     # EUR/USD dia habil previo a 30/08/2026
INITIAL_CAPITAL_USD = INITIAL_CAPITAL_EUR * EURUSD_START

# Parametros del paper trading
MAX_POSITIONS = 2
BUY_THRESHOLD = 0.015          # score > esto -> COMPRA
HIGH_CONF_THRESHOLD = 0.025    # score > esto -> confianza ALTA
TRANSACTION_COST = 0.0010      # fee Binance base taker
HALF_SPREAD = 0.0002
SLIPPAGE = 0.0003
COST = TRANSACTION_COST + HALF_SPREAD + SLIPPAGE  # coste total por operacion (one-way)


class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.W_i = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_f = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_o = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_z = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_omega = nn.Parameter(torch.randn(hidden_dim, hidden_dim))
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x, states):
        h_prev, c_prev = states
        combined = torch.cat([x, h_prev], dim=-1)
        i = torch.sigmoid(self.W_i(combined))
        f = torch.sigmoid(self.W_f(combined))
        o = torch.sigmoid(self.W_o(combined))
        z = torch.tanh(self.W_z(combined))
        c = f * c_prev + i * z
        omega = torch.softmax(self.W_omega, dim=-1)
        freq_adapt = (omega * c.unsqueeze(-1)).sum(dim=1)
        h = o * torch.tanh(c + freq_adapt)
        h = self.dropout(h)
        return h, c


class SFMModelRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, output_dim, dropout_rate=0.2):
        super().__init__()
        self.cell = SFMCellRefined(input_dim, hidden_dim, freq_components, dropout_rate)
        self.fc_out = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        h = torch.zeros(batch_size, self.cell.hidden_dim, device=x.device)
        c = torch.zeros(batch_size, self.cell.hidden_dim, device=x.device)
        for t in range(seq_len):
            h, c = self.cell(x[:, t, :], (h, c))
        return self.fc_out(h)


def wavelet_denoise_1d(signal, wavelet="db2", level=2, mode="soft"):
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    if sigma < 1e-10:
        sigma = np.std(signal) * 0.1
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))
    coeffs_thresh = list(coeffs)
    for i in range(1, len(coeffs_thresh)):
        coeffs_thresh[i] = pywt.threshold(coeffs_thresh[i], threshold, mode=mode)
    return pywt.waverec(coeffs_thresh, wavelet)[:len(signal)]


def denoise_matrix(matrix):
    denoised = np.zeros_like(matrix)
    for col in range(matrix.shape[1]):
        denoised[:, col] = wavelet_denoise_1d(matrix[:, col])
    return denoised


def build_features_matrix(df_close: pd.DataFrame) -> np.ndarray:
    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_close_safe = df_close.replace(0, np.nan).ffill().bfill()
    df_ratio = (df_mean_5 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)
    df_vol = df_pct.rolling(window=20).std().fillna(0)
    df_ma20 = df_close.rolling(window=20).mean().fillna(df_close)
    df_ma20_ratio = (df_ma20 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)
    df_range = df_pct.abs()
    matrix = np.hstack([df_close.values, df_pct.values, df_ratio.values,
                        df_vol.values, df_ma20_ratio.values, df_range.values])
    return np.nan_to_num(matrix, nan=0.0, posinf=1.0, neginf=-1.0)


def simulate_portfolio(pred_days, pred_list, df_close):
    """Simula la cartera igual que el paper. Retorna (curve, operaciones)."""
    cash = INITIAL_CAPITAL_USD
    positions = {}  # symbol(lower) -> shares
    curve, opers = [], []

    for r, day in enumerate(pred_days):
        scores = pred_list[r]
        close_row = df_close.loc[day] if day in df_close.index else None
        idx_map = {c.upper(): i for i, c in enumerate(CRYPTOS)}

        # 1. Vender posiciones que ya no tienen COMPRA (score <= BUY_THRESHOLD)
        for s_lower in list(positions.keys()):
            ci = idx_map[s_lower.upper()]
            if scores[ci] <= BUY_THRESHOLD:
                if close_row is not None and s_lower.upper() in close_row.index:
                    px = float(close_row[s_lower.upper()])
                    if px and px == px:
                        shares = positions[s_lower]
                        gross = shares * px
                        fee = gross * COST
                        net = gross - fee
                        cash += net
                        opers.append({"date": str(day.date()), "type": "SELL", "symbol": s_lower.upper(),
                                      "shares": shares, "price": px, "fee": round(fee, 2), "net": round(net, 2)})
                        del positions[s_lower]

        # 2. Compras: monedas con score > HIGH_CONF, hasta llenar cupos
        current = len(positions)
        available = MAX_POSITIONS - current
        if available > 0 and close_row is not None:
            candidates = []
            for c in CRYPTOS:
                if c not in positions and scores[CRYPTOS.index(c)] > HIGH_CONF_THRESHOLD:
                    candidates.append((c, scores[CRYPTOS.index(c)]))
            candidates.sort(key=lambda kv: -kv[1])
            for c, _sc in candidates[:available]:
                if close_row is not None and c.upper() in close_row.index:
                    px = float(close_row[c.upper()])
                    if px and px == px:
                        # capital equitativo entre posiciones (paper: cash/(slots+1)); sin exceder cash tras fee
                        capital_per = cash / (available + 1)
                        # invertir capital_per NETO de fee en shares
                        nav = max(capital_per - capital_per * COST, 0.0)
                        shares = nav / px
                        fee = capital_per * COST
                        cost = shares * px + fee  # == capital_per
                        if cost <= cash:
                            positions[c] = shares
                            cash -= cost
                            opers.append({"date": str(day.date()), "type": "BUY", "symbol": c.upper(),
                                          "shares": shares, "price": px, "fee": round(fee, 2), "cost": round(cost, 2)})

        # 3. Valorar
        val = cash
        if close_row is not None:
            for c_shar in positions:
                if close_row is not None and c_shar.upper() in close_row.index:
                    val += positions[c_shar] * float(close_row[c_shar.upper()])
        curve.append((day, val))

    return curve, opers


def load_closes():
    close_dict = {}
    for c in CRYPTOS:
        df = D.features([c], ["$close"], start_time="2024-01-01", end_time="2026-12-31")
        df = df.reset_index()
        s = df.pivot(index="datetime", columns="instrument", values="$close")[c]
        close_dict[c.upper()] = s
    df = pd.DataFrame(close_dict).sort_index()
    return df[df.index <= pd.Timestamp(END)]


def load_model():
    device = torch.device("cpu")
    model = SFMModelRefined(54, MODEL_PARAMS["hidden_dim"], MODEL_PARAMS["freq_components"],
                            len(CRYPTOS), MODEL_PARAMS["dropout_rate"])
    model.load_state_dict(torch.load(MODEL_FILE, map_location=device, weights_only=True))
    model.eval()
    return model


def main():
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)
    df_close = load_closes()
    print(f"Datos: {df_close.index[0].date()} -> {df_close.index[-1].date()} ({len(df_close)} filas)")
    model = load_model()
    lookback = MODEL_PARAMS["lookback"]

    pred_days, pred_list = [], []
    all_days = list(df_close.index)
    for i in range(lookback + 25, len(all_days)):
        day = all_days[i]
        if day < pd.Timestamp(START):
            continue
        if day > pd.Timestamp(END):
            break
        window = df_close.loc[:day]
        if len(window) < lookback + 5:
            continue
        matrix = build_features_matrix(window)
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scale = MinMaxScaler(feature_range=(-1, 1)); scaled = scale.fit_transform(matrix)
        x = torch.tensor(scaled[-lookback:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred = model(x).numpy()[0]
        pred_days.append(day); pred_list.append(pred)

    print(f"Dias evaluados: {len(pred_days)}")
    if not pred_days:
        return None

    curve, opers = simulate_portfolio(pred_days, pred_list, df_close)
    dates = [str(d.date()) for d, _ in curve]
    vals = np.array([v for _, v in curve])

    # retornos
    rets = np.diff(vals) / vals[:-1] if len(vals) > 1 else np.array([0.0])
    rets = np.insert(rets, 0, vals[0] / INITIAL_CAPITAL_USD - 1)
    metrics = performance_metrics(rets)

    final_usd = float(vals[-1]) if len(vals) else INITIAL_CAPITAL_USD
    final_eur = final_usd / EURUSD_END
    ret_pct_usd = (final_usd / INITIAL_CAPITAL_USD - 1) * 100
    ret_pct_eur = (final_eur / INITIAL_CAPITAL_EUR - 1) * 100

    result = {
        "start_date": dates[0], "end_date": dates[-1],
        "initial_capital_eur": INITIAL_CAPITAL_EUR, "eurusd_start": EURUSD_START,
        "eurusd_end": EURUSD_END, "initial_capital_usd": round(INITIAL_CAPITAL_USD, 2),
        "final_capital_usd": round(final_usd, 2), "final_capital_eur": round(final_eur, 2),
        "return_pct_usd": round(ret_pct_usd, 2), "return_pct_eur": round(ret_pct_eur, 2),
        "sharpe": round(metrics["sharpe"], 3), "sortino": round(metrics["sortino"], 3),
        "max_drawdown_pct": round(metrics["max_drawdown"] * 100, 2),
        "n_trades": len(opers), "costs": {"transaction_cost": TRANSACTION_COST,
                                          "half_spread": HALF_SPREAD, "slippage": SLIPPAGE},
        "curve_dates": dates, "equity_usd": [round(float(v), 2) for v in vals],
        "operations": opers,
    }
    out = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "backtest_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["start_date","end_date","final_capital_eur","return_pct_eur","return_pct_usd","sharpe","n_trades"]}, indent=2))
    return result


if __name__ == "__main__":
    main()